"""Dispatcher conversationnel — moteur dynamique uniquement.

Toute conversation est pilotée par le workflow actif en BD (édité depuis le
back-office `/assistante/parcours`). Aucune logique de parcours n'est codée
en dur : ajouter / modifier / réordonner les étapes se fait depuis l'UI,
sans redémarrage.

Si aucun workflow n'est actif en BD, on retourne un message d'erreur clair
plutôt qu'un comportement legacy silencieux — c'est une condition de
configuration à corriger côté admin.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.conversation import default_actions  # noqa: F401 (enregistre les actions)
from app.conversation import handoff_actions  # noqa: F401 (enregistre lookup/update/rag)
from app.conversation import llm_actions  # noqa: F401 (build_recap, send_otp, verify_otp)
from app.conversation import workflow_executor
from app.conversation.utils import BotReply
from app.models import Conversation, EndUser, Tenant

logger = logging.getLogger(__name__)


# Détection « question libre » quand on est au menu ou après completion :
# plus de 2 mots qui ne forment pas un numéro ni un mot-clé de reset ou
# d'intent de parcours → on route vers le RAG.
_INTENT_PARCOURS_RE = re.compile(
    r"\b(inscri|identif|m[’']?identif|cr[eé]er|ouvri|nouveau)|"
    r"\b(modifi|mettre[\s-]?[àa][\s-]?jour|actualis|chang)|"
    r"\b(consult|v[eé]rif|suivr|statut|avance)",
    re.IGNORECASE,
)
_NUMERIC_PICK_RE = re.compile(r"^\s*[0-9]{1,2}\s*$")

_GREETING_RE = re.compile(
    r"^\s*(hello|hi|hey|bonjour|bonsoir|salut|cc|coucou|yo|allo|allô|menu|accueil|start|aide|help|info|infos)\s*[!.?]*\s*$",
    re.IGNORECASE,
)


def _looks_like_free_question(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    if _NUMERIC_PICK_RE.match(t):
        return False
    if _is_reset_keyword(t):
        return False
    if _INTENT_PARCOURS_RE.search(t):
        return False
    # 3 mots ou plus, ou se termine par un ? → c'est une question libre
    words = re.findall(r"[a-zA-Zéèàêîôûç']{2,}", t)
    return t.endswith("?") or len(words) >= 3

# Mots-clés universels qui marchent à n'importe quelle étape du parcours.
# Évite les conversations bloquées (ex. attente d'une photo verso quand
# l'utilisateur ne peut pas la fournir tout de suite).
RESET_KEYWORDS = {
    "menu", "/menu",
    "annuler", "/annuler",
    "reset", "/reset",
    "stop", "/stop",
    "recommencer", "/recommencer",
    "abandonner", "/abandonner",
}


def _is_reset_keyword(text: str) -> bool:
    if not text:
        return False
    return text.strip().lower() in RESET_KEYWORDS


async def dispatch(
    db: AsyncSession,
    tenant: Tenant,
    conversation: Conversation,
    end_user: EndUser,
    text: str,
    has_media: bool = False,
    media_url: Optional[str] = None,
) -> BotReply:
    """Exécute un tour du workflow actif et retourne la réponse à envoyer."""
    # Payload spécial envoyé par les cartes du chat web :
    # "__wf__:<workflow_id>" → bascule direct sur CE workflow.
    # Résout le cross-routing quand plusieurs parcours actifs partagent des
    # codes de step (ex. deux parcours avec `consent_artci`).
    from uuid import UUID as _UUID
    forced_workflow_id = None
    if text and text.startswith("__wf__:"):
        try:
            forced_workflow_id = _UUID(text.split(":", 1)[1].strip())
        except Exception:
            forced_workflow_id = None

    workflow = None
    if forced_workflow_id:
        workflow = await workflow_executor.load_workflow(db, forced_workflow_id)
        if workflow is not None:
            # On repart du début de CE workflow, user_input="" pour afficher
            # son step d'accueil sans que le "__wf__:..." soit traité comme
            # une réponse à une question.
            conversation.state = "start"
            # Pin le workflow dans le contexte pour que les tours suivants
            # retrouvent le BON workflow (les codes de step peuvent être
            # partagés entre parcours → load_workflow_by_step_code n'est pas
            # fiable). Clé interne préfixée `_` pour ne pas polluer le recap.
            ctx_tmp = dict(conversation.context or {})
            ctx_tmp["_pinned_workflow_id"] = str(workflow.id)
            conversation.context = ctx_tmp
            text = ""

    # Si un workflow est pinned dans le contexte (sélection précédente), on le
    # réutilise sans ambiguïté.
    if workflow is None:
        pinned = (conversation.context or {}).get("_pinned_workflow_id")
        if pinned:
            try:
                workflow = await workflow_executor.load_workflow(db, _UUID(pinned))
            except Exception:
                workflow = None

    # ---- MENU UNIFIÉ (priorité absolue, avant toute résolution workflow) ----
    waiting_menu_choice = (
        (conversation.context or {}).get("_menu_pending") is True
    )
    at_start = (not conversation.state) or conversation.state in ("start", "done")

    async def _render_menu() -> BotReply:
        active_wfs = await workflow_executor.list_active_workflows(db)
        if not active_wfs:
            return BotReply(text="Posez votre question, je vais y répondre à partir des informations MA2E.")
        lines = [
            "👋 Bonjour, bienvenue sur MA2E.",
            "",
            "Que souhaitez-vous faire ?",
            "",
        ]
        for i, wf in enumerate(active_wfs, 1):
            label = workflow_executor._short_label(wf.name)
            lines.append(f"{i}. *{label}*")
        lines.append(f"{len(active_wfs) + 1}. *Poser une question libre*")
        lines.append("")
        lines.append("_Répondez par le numéro de votre choix._")
        ctx_tmp = dict(conversation.context or {})
        ctx_tmp["_menu_pending"] = True
        ctx_tmp["_menu_workflow_ids"] = [str(w.id) for w in active_wfs]
        ctx_tmp.pop("_pinned_workflow_id", None)
        ctx_tmp.pop("_update_mode", None)
        ctx_tmp.pop("_update_dossier_id", None)
        conversation.context = ctx_tmp
        conversation.state = "start"
        return BotReply(text="\n".join(lines))

    # 1) Reset keyword (STOP/MENU/ANNULER/RECOMMENCER) → TOUJOURS menu, même
    #    si on était au milieu d'un parcours. Shortcut absolu.
    if not forced_workflow_id and _is_reset_keyword(text):
        return await _render_menu()

    # 2) En attente d'un choix de menu : traite la saisie
    if waiting_menu_choice:
        raw = (text or "").strip()
        if raw.isdigit():
            choice = int(raw)
            wf_ids = (conversation.context or {}).get("_menu_workflow_ids", [])
            if 1 <= choice <= len(wf_ids):
                # Choix d'un parcours : on sort du menu
                ctx_tmp = dict(conversation.context or {})
                ctx_tmp.pop("_menu_pending", None)
                ctx_tmp.pop("_menu_workflow_ids", None)
                chosen_id = wf_ids[choice - 1]
                try:
                    workflow = await workflow_executor.load_workflow(db, _UUID(chosen_id))
                    if workflow is not None:
                        ctx_tmp["_pinned_workflow_id"] = str(workflow.id)
                        conversation.state = "start"
                        text = ""
                except Exception:
                    workflow = None
                conversation.context = ctx_tmp
            elif choice == len(wf_ids) + 1:
                # « Poser une question libre » : on RESTE dans la boucle menu
                # (menu_pending conservé) pour que les tours suivants, tant
                # qu'ils ne sont pas un digit valide ou un reset keyword,
                # continuent de router vers le RAG — sinon « Ok » après la
                # première réponse relancerait l'inscription.
                ctx_tmp = dict(conversation.context or {})
                ctx_tmp["_menu_pending"] = True
                conversation.context = ctx_tmp
                conversation.state = "start"
                return BotReply(
                    text="Posez votre question, je vais y répondre en me basant sur les informations MA2E.",
                )
            else:
                # Numéro hors liste : reprompte le menu
                return await _render_menu()
        else:
            # Pas un numéro : si greeting → reprompte menu, sinon RAG
            if _GREETING_RE.match(raw):
                return await _render_menu()
            # Question libre → RAG. On garde `_menu_pending` pour que les
            # messages de suivi (« Ok », « Merci », reformulation…) restent
            # en mode question libre au lieu de retomber dans un parcours.
            try:
                from app.services import rag
                answer = await rag.answer_question(
                    db, tenant_id=tenant.id, tenant_name=tenant.name,
                    question=raw, history=None,
                )
                return BotReply(text=answer.answer)
            except Exception as e:
                logger.warning("RAG fallback échoué : %s", e)
                return await _render_menu()

    # 3) Greeting / message vide sur une conversation fraîche → menu
    if not forced_workflow_id and workflow is None and at_start and (
        _GREETING_RE.match(text or "") or not (text or "").strip()
    ):
        return await _render_menu()

    # Si la conversation est déjà engagée dans un parcours (state = code d'un
    # step existant), reprendre CE workflow — pas nécessairement le "principal".
    # Sinon (nouveau, done, start) → charger le workflow actif primaire.
    if workflow is None and conversation.state and conversation.state not in ("start", "done"):
        workflow = await workflow_executor.load_workflow_by_step_code(
            db, conversation.state,
        )
    if workflow is None:
        workflow = await workflow_executor.load_active_workflow(db)
    if workflow is None:
        # Pas de parcours actif : on peut encore répondre aux questions libres
        # via le RAG (base de connaissances). "J'ai une question" fait partie
        # de ce cas.
        if _looks_like_free_question(text) or text.strip().lower().startswith("j'ai une question"):
            try:
                from app.services import rag
                answer = await rag.answer_question(
                    db,
                    tenant_id=tenant.id,
                    tenant_name=tenant.name,
                    question=text,
                    history=None,
                )
                conversation.state = "start"
                return BotReply(text=answer.answer)
            except Exception as e:
                logger.warning("RAG fallback (sans workflow) échoué : %s", e)
        logger.error("Aucun workflow actif en BD pour le tenant %s", tenant.id)
        return BotReply(
            text=(
                "⚠️ Le service est temporairement indisponible "
                "(aucun parcours actif configuré). Merci de réessayer plus tard."
            )
        )

    # 🆘 Escape hatch global : MENU / ANNULER / RESET / STOP redémarrent le
    # parcours depuis le début, quel que soit l'état courant. Indispensable
    # quand l'utilisateur est coincé sur une question qu'il ne peut pas
    # satisfaire (ex. demande de photo alors qu'il n'a pas l'image sous la main).
    #
    # Un parcours TERMINÉ (`state == "done"`) est aussi un reset implicite :
    # l'utilisateur recommence une interaction après avoir fini un dossier.
    # Sinon le texte serait interprété comme réponse au welcome, qui attend
    # un numéro de menu, et le dispatcher boucle en reprompt.
    done_reset = conversation.state == "done"
    if _is_reset_keyword(text) or done_reset:
        logger.info(
            "Reset %s — état précédent : %s (texte=%r)",
            "mot-clé" if _is_reset_keyword(text) else "après completion",
            conversation.state, text[:60],
        )
        conversation.state = "start"
        conversation.context = {}
        current_state = None
    else:
        # Si l'état courant ne fait pas partie des steps du workflow actif
        # (transition depuis un ancien parcours, état "start", reset…),
        # on repart du début.
        current_state = conversation.state
        step_codes = {s.code for s in workflow.steps}
        if current_state not in step_codes:
            if current_state and current_state not in ("start", "done"):
                logger.info(
                    "État '%s' inconnu du workflow %s → reset au start_step_code",
                    current_state, workflow.name,
                )
            current_state = None  # l'executor démarrera à workflow.start_step_code

    # 💬 Fallback RAG : au menu (current_state is None) et texte libre non
    # routable (ni numéro, ni intent parcours, ni reset) → bascule sur la
    # base de connaissances au lieu de reprompt le menu en boucle.
    if current_state is None and _looks_like_free_question(text):
        try:
            from app.services import rag
            answer = await rag.answer_question(
                db,
                tenant_id=tenant.id,
                tenant_name=tenant.name,
                question=text,
                history=None,
            )
            # On reste à l'état "start" pour permettre d'enchaîner avec un
            # choix de parcours derrière.
            conversation.state = "start"
            return BotReply(text=answer.answer)
        except Exception as e:
            logger.warning("RAG fallback échoué, retour au menu : %s", e)

    context = dict(conversation.context or {})
    if media_url:
        context["last_media_url"] = media_url
        context["last_has_media"] = has_media
    # Injecte les identifiants accessibles aux actions backend (envoi
    # notifications, création dossier, OTP, etc.)
    context["_end_user_id"] = str(end_user.id)
    context["_end_user_phone"] = end_user.phone
    context["_end_user_name"] = end_user.name
    context["_channel"] = conversation.channel.value
    context["_conversation_id"] = str(conversation.id)

    # Sur un reset : ne passe PAS le mot-clé comme user_input (sinon le moteur
    # le traiterait comme une réponse au welcome et boucle à nouveau).
    effective_input = None if _is_reset_keyword(text) else text

    result = await workflow_executor.execute(
        db,
        workflow=workflow,
        tenant_id=tenant.id,
        current_step_code=current_state,
        user_input=effective_input,
        context=context,
    )

    # Basculement inter-parcours : le menu principal a routé vers un autre
    # workflow (ex. "2" → Consultation). On charge ce workflow et on lance
    # son start_step_code pour afficher le premier message.
    if result.switch_to_step:
        target_workflow = await workflow_executor.load_workflow_by_step_code(
            db, result.switch_to_step,
        )
        if target_workflow is not None:
            result = await workflow_executor.execute(
                db,
                workflow=target_workflow,
                tenant_id=tenant.id,
                current_step_code=None,   # démarre au start du nouveau workflow
                user_input=None,
                context=result.context,
            )
            workflow = target_workflow

    # Persiste le nouvel état
    if result.is_terminal:
        conversation.state = "done"
    elif result.next_step_code:
        conversation.state = result.next_step_code

    # Nettoie les clés internes du contexte (préfixées par `_`) avant persistance.
    # On garde `_pinned_workflow_id` pour que les tours suivants retrouvent le
    # bon workflow quand plusieurs parcours partagent des step codes.
    _PRESERVE = {"_pinned_workflow_id", "_update_mode", "_update_dossier_id",
                 "_menu_pending", "_menu_workflow_ids",
                 "_wa_form_step", "_wa_form_idx"}
    cleaned = {k: v for k, v in result.context.items() if not k.startswith("_") or k in _PRESERVE}
    # Ajoute aussi le pin depuis le contexte source (si pas encore dans result.context)
    src_pin = (conversation.context or {}).get("_pinned_workflow_id")
    if src_pin and "_pinned_workflow_id" not in cleaned:
        cleaned["_pinned_workflow_id"] = src_pin
    # Si le parcours est terminé, on libère le pin pour que la prochaine
    # interaction revienne au menu / au workflow par défaut.
    if result.is_terminal:
        cleaned.pop("_pinned_workflow_id", None)
    conversation.context = cleaned

    if result.error:
        logger.warning("Erreur d'exécution workflow : %s", result.error)
        return BotReply(
            text=(
                "Une erreur est survenue dans le parcours. "
                "Merci de réessayer ou contactez le support."
            )
        )

    if not result.messages:
        return BotReply(text="…", ui=result.ui)

    full_text = "\n\n".join(m.strip() for m in result.messages if m and m.strip())
    return BotReply(text=full_text or "…", ui=result.ui)
