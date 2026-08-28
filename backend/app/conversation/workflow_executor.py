"""Moteur d'exécution des workflows conversationnels dynamiques.

Lit le workflow actif depuis la BD et avance pas à pas. L'état conversationnel
est porté par `Conversation.state` (= code de l'étape courante) et
`Conversation.context` (= dict du contexte métier accumulé).

Cycle d'exécution :
1. Pour un step `message` : envoie le template puis enchaîne immédiatement
   sur `next_step_code` (boucle interne, sans retour à l'utilisateur).
2. Pour un step `question` : envoie le template, retourne au caller pour
   attendre la réponse utilisateur. À la prochaine entrée, valide + transition.
3. Pour un step `action` : appelle la fonction registered, transitionne selon
   `branch_key` ou `next_step_code`. Enchaîne immédiatement.
4. Pour un step `decision` : évalue la règle, transitionne. Enchaîne.

Le caller (webhook ou simulateur) appelle `advance(user_input)` à chaque
message reçu. La méthode retourne :
- le texte à envoyer
- l'état suivant à persister
- des indications de fin de parcours
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.conversation.workflow_actions import ActionResult, get_action
from app.models.workflow import Workflow, WorkflowStep, WorkflowStepType
from app.services import workflow_template_service
from app.services.message_template_service import render as render_template

logger = logging.getLogger(__name__)

# Garde-fou : évite les boucles infinies si un workflow mal câblé pointe sur
# lui-même via une chaîne d'actions/messages sans question.
MAX_INTERNAL_STEPS = 25


@dataclass
class ExecuteResult:
    """Résultat d'une étape d'exécution renvoyée au caller."""

    messages: list[str] = field(default_factory=list)
    """Tous les textes à envoyer à l'utilisateur (concaténation des steps
    `message` enchaînés)."""

    next_step_code: Optional[str] = None
    """Le code de l'étape qui attend la prochaine entrée utilisateur.
    None = fin du parcours."""

    is_terminal: bool = False
    """True si le parcours est terminé (plus aucune étape suivante)."""

    switch_to_step: Optional[str] = None
    """Si non-None : le dispatcher doit charger le workflow contenant ce step
    et relancer execute() dessus (transition inter-parcours depuis le menu)."""

    context: dict = field(default_factory=dict)
    """Le contexte mis à jour, à persister dans `Conversation.context`."""

    error: Optional[str] = None
    """Message d'erreur lisible (workflow inconnu, step manquante…)."""


async def load_active_workflow(db: AsyncSession) -> Optional[Workflow]:
    """Retourne le workflow actif de plus petite position.

    ORDER BY position garantit un choix stable quand plusieurs workflows
    sont marqués actifs (sinon Postgres renvoie n'importe lequel).
    """
    result = await db.execute(
        select(Workflow)
        .options(selectinload(Workflow.steps))
        .where(Workflow.active.is_(True))
        .order_by(Workflow.position.asc(), Workflow.created_at.asc())
    )
    return result.scalars().first()


async def load_workflow(db: AsyncSession, workflow_id: UUID) -> Optional[Workflow]:
    result = await db.execute(
        select(Workflow)
        .options(selectinload(Workflow.steps))
        .where(Workflow.id == workflow_id)
    )
    return result.scalars().first()


async def load_workflow_by_step_code(db: AsyncSession, step_code: str) -> Optional[Workflow]:
    """Trouve le workflow qui contient un step avec ce code.

    Utile pour :
    - reprendre une conversation dans le bon workflow via son state
    - basculer d'un workflow à un autre depuis un menu inter-parcours
    """
    step = (
        await db.execute(
            select(WorkflowStep).where(WorkflowStep.code == step_code).limit(1)
        )
    ).scalar_one_or_none()
    if step is None:
        return None
    return await load_workflow(db, step.workflow_id)


def _build_step_index(workflow: Workflow) -> dict[str, WorkflowStep]:
    return {step.code: step for step in workflow.steps}


def _validate_question_input(step: WorkflowStep, user_input: str) -> Optional[str]:
    """Retourne `None` si valide, sinon un message d'erreur lisible."""
    rules = step.validation_rules or {}
    text = (user_input or "").strip()

    min_len = rules.get("min_len")
    if min_len is not None and len(text) < int(min_len):
        return f"Au moins {min_len} caractère(s) attendu(s)."

    max_len = rules.get("max_len")
    if max_len is not None and len(text) > int(max_len):
        return f"Au plus {max_len} caractère(s) autorisé(s)."

    regex = rules.get("regex")
    if regex:
        try:
            if not re.match(regex, text):
                return rules.get("error_message", "Format invalide.")
        except re.error as e:
            logger.warning("Workflow step %s : regex invalide '%s' (%s)", step.code, regex, e)

    return None


# Détection courte du type de parcours d'après son nom — pour afficher dans
# le menu welcome avec un libellé court et un emoji.
_PARCOURS_KINDS = [
    (re.compile(r"inscription", re.I), "✨", "M'inscrire"),
    (re.compile(r"consultation", re.I), "🔍", "Consulter mon dossier"),
    (re.compile(r"mise[- ]à[- ]jour|modification", re.I), "✏️", "Modifier mes informations"),
    (re.compile(r"chat|faq|question", re.I), "💬", "Poser une question libre"),
]

_DIGIT_EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]


def _short_label(name: str) -> str:
    """Retourne un libellé court selon le nom du workflow."""
    for pattern, _emoji, short in _PARCOURS_KINDS:
        if pattern.search(name):
            return short
    return name


def _parcours_emoji(name: str) -> str:
    for pattern, emoji, _short in _PARCOURS_KINDS:
        if pattern.search(name):
            return emoji
    return "▶️"


async def _build_parcours_list(db: AsyncSession) -> str:
    """Génère dynamiquement le menu des parcours à partir des workflows ACTIFS.

    Ordre = position. Format :
        1️⃣ ✨ *M'inscrire* (nouveau sociétaire)
        2️⃣ 🔍 *Consulter* mon dossier
        ...
    Un workflow désactivé disparaît du menu (cohérent avec _resolve_dynamic_router).
    """
    result = await db.execute(
        select(Workflow)
        .where(Workflow.active.is_(True))
        .order_by(Workflow.position.asc(), Workflow.created_at.asc())
    )
    workflows = list(result.scalars().all())

    lines = []
    for idx, wf in enumerate(workflows, start=1):
        digit = _DIGIT_EMOJIS[idx - 1] if idx <= 9 else f"{idx}."
        short = _short_label(wf.name)
        emoji = _parcours_emoji(wf.name)
        lines.append(f"{digit} {emoji} *{short}*")
    return "\n".join(lines)


async def _build_employeurs_list(db: AsyncSession, tenant_id: UUID) -> str:
    """Liste numérotée des sociétés actives, format :
        1️⃣ CIE
        2️⃣ SODECI
        ...
    Permet de garder le template `workflow.ask_employeur` synchro avec la BD.
    """
    from app.models import Employeur
    from sqlalchemy import select as _select
    result = await db.execute(
        _select(Employeur)
        .where(Employeur.tenant_id == tenant_id, Employeur.is_active.is_(True))
        .order_by(Employeur.name)
    )
    lines = []
    for idx, emp in enumerate(result.scalars().all(), start=1):
        digit = _DIGIT_EMOJIS[idx - 1] if idx <= 9 else f"{idx}."
        lines.append(f"{digit} {emp.name}")
    return "\n".join(lines)


async def _build_boites_postales_list(db: AsyncSession, tenant_id: UUID) -> str:
    """Construit la liste numérotée des boîtes postales par société, depuis
    la table Employeur. Affichée dans le template `workflow.ask_boite_postale`
    via la variable `{boites_postales_list}`.

    Format :
        1️⃣ CIE · 01 BP 6923 Abidjan 01
        2️⃣ SODECI · 01 BP 1843 Abidjan 01
        …
    Ne retient que les employeurs actifs ayant une boîte postale renseignée.
    """
    from app.models import Employeur
    from sqlalchemy import select as _select
    result = await db.execute(
        _select(Employeur)
        .where(
            Employeur.tenant_id == tenant_id,
            Employeur.is_active.is_(True),
        )
        .order_by(Employeur.name)
    )
    lines = []
    for idx, emp in enumerate(result.scalars().all(), start=1):
        if not emp.boite_postale:
            continue
        digit = _DIGIT_EMOJIS[idx - 1] if idx <= 9 else f"{idx}."
        lines.append(f"{digit} {emp.name} · {emp.boite_postale}")
    return "\n".join(lines)


async def _system_variables(db: AsyncSession, tenant_id: UUID) -> dict[str, str]:
    """Réutilise le helper du message_template_service pour injecter
    assistant_name, support_*, artci_url, dpo_email + un menu `parcours_list`
    dynamique généré à partir des workflows en BD + `boites_postales_list`."""
    try:
        from app.services.message_template_service import _system_variables as fn
        base = await fn(db, tenant_id)
    except Exception as e:
        logger.debug("system_variables indisponibles : %s", e)
        base = {}

    try:
        base["parcours_list"] = await _build_parcours_list(db)
    except Exception as e:
        logger.warning("Construction parcours_list échouée : %s", e)
        base.setdefault("parcours_list", "")

    try:
        base["boites_postales_list"] = await _build_boites_postales_list(db, tenant_id)
    except Exception as e:
        logger.warning("Construction boites_postales_list échouée : %s", e)
        base.setdefault("boites_postales_list", "")

    try:
        base["employeurs_list"] = await _build_employeurs_list(db, tenant_id)
    except Exception as e:
        logger.warning("Construction employeurs_list échouée : %s", e)
        base.setdefault("employeurs_list", "")

    return base


# Footer ajouté automatiquement à chaque QUESTION du workflow pour rappeler à
# l'utilisateur qu'il peut sortir d'une boucle (ex. attente d'une photo qu'il
# n'a pas sous la main). Vu en bas de chaque prompt sauf sur les start-steps
# qui sont déjà des menus.
ESCAPE_HINT = "\n\n💡 _Tapez *MENU*, *STOP*, *ANNULER* ou *RECOMMENCER* à tout moment pour reprendre depuis le début._"

# Steps de démarrage des différents workflows — ils SONT déjà des menus, pas
# besoin d'ajouter un rappel "tapez MENU".
START_STEP_CODES = {
    "welcome",
    "consult_welcome",
    "update_welcome",
    "chat_welcome",
}


def _should_show_escape_hint(step: WorkflowStep, context: dict) -> bool:
    """True si on doit ajouter le rappel des mots-clés à la fin du message."""
    if step.type != WorkflowStepType.question:
        return False  # pas pour les actions / messages terminaux
    if step.code in START_STEP_CODES:
        return False  # le step de démarrage EST déjà un menu
    if context.get("_simulate"):
        # Mode simulateur : on ajoute quand même pour que l'admin voie
        # l'aspect final tel que le sociétaire le verra.
        return True
    return True


# F-09 — Un nom de variable interne (`{ocr_extracted_name}`, `{support_phone}`,
# etc.) ne doit JAMAIS fuiter vers l'utilisateur. Le regex matche uniquement
# les identifiants Python valides pour ne pas fusiller les accolades légitimes
# (JSON échantillon, code, snippets techniques).
_LEAKED_TOKEN_RE = re.compile(r"\{[a-zA-Z_][a-zA-Z0-9_]{0,63}\}")


def _scrub_leaked_tokens(text: str) -> str:
    """Remplace tout token `{xxx}` résiduel par un tiret discret.

    Défense en profondeur : même si `format_map` a échoué (accolade
    orpheline, JSON dans le template, brace non fermée) et laissé
    passer un identifiant en clair, on l'efface avant renvoi.
    """
    return _LEAKED_TOKEN_RE.sub("—", text)


async def _render_or_fallback(
    db: AsyncSession,
    tenant_id: UUID,
    step: WorkflowStep,
    context: dict,
) -> str:
    """Rend le template du step. Fallback safe sur le label si absent.

    Ajoute automatiquement le rappel des mots-clés universels (MENU / STOP /
    ANNULER / RECOMMENCER) en bas de chaque question — sauf sur les steps de
    démarrage qui sont déjà des menus.

    F-09 — tous les chemins de retour passent par `_scrub_leaked_tokens` :
    aucun `{xxx}` ne peut atteindre l'utilisateur, même quand `format_map`
    lève une exception ou quand le template contient des accolades JSON.
    """
    template_code = step.template_code or workflow_template_service.derive_code(step.code)
    sys_vars = await _system_variables(db, tenant_id)
    variables = {**sys_vars, **{k: str(v) for k, v in context.items() if v is not None}}

    # 1) Essai sur le service workflow (BD directe, sans registry)
    raw = await workflow_template_service.get_content(db, tenant_id, template_code)
    if raw is not None and raw.strip():
        # Substitution simple {var} dans le contenu
        try:
            body = raw.format_map(_SafeDict(variables))
        except Exception:
            body = raw
        body = _scrub_leaked_tokens(body)
        if _should_show_escape_hint(step, context):
            body = body + ESCAPE_HINT
        return body

    # 2) Fallback sur le registry standard (pour les codes système)
    if step.template_code:
        try:
            _, content = await render_template(
                db, tenant_id=tenant_id, code=step.template_code, variables=variables,
            )
            if content:
                content = _scrub_leaked_tokens(content)
                if _should_show_escape_hint(step, context):
                    content = content + ESCAPE_HINT
                return content
        except Exception as e:
            logger.debug(
                "Template registry '%s' absent pour step %s (%s)",
                step.template_code, step.code, e,
            )

    # 3) Fallback ultime : libellé entre crochets
    fallback = f"[{_scrub_leaked_tokens(step.label or '')}]"
    if _should_show_escape_hint(step, context):
        fallback += ESCAPE_HINT
    return fallback


class _SafeDict(dict):
    """dict qui renvoie un placeholder discret au lieu de KeyError.

    F-09 — les gabarits internes (ex. `{ocr_extracted_name}` sans OCR
    disponible) ne doivent JAMAIS être affichés en clair à l'utilisateur ;
    le pentest a signalé ça comme fuite de gabarit interne. On renvoie
    donc un tiret pour signaler l'absence sans exposer le nom technique
    de la variable.
    """

    def __missing__(self, key):  # type: ignore[override]
        return "—"


async def _run_action(
    db: AsyncSession,
    step: WorkflowStep,
    context: dict,
    last_input: Optional[str] = None,
) -> ActionResult:
    name = step.action_name or step.code
    handler = get_action(name)
    if handler is None:
        logger.error("Action workflow inconnue : %s (step %s)", name, step.code)
        return ActionResult(
            branch_key=None,
            message=f"[Action backend non implémentée : {name}]",
        )
    try:
        return await handler(db, context, last_input)
    except Exception as e:
        logger.exception("Action %s a échoué : %s", name, e)
        return ActionResult(branch_key="error", message=f"Erreur action {name} : {e}")


def _resolve_next_code(step: WorkflowStep, branch_key: Optional[str]) -> Optional[str]:
    """Choisit l'étape suivante selon branch_key (priorité) puis next_step_code."""
    if branch_key and step.branches and branch_key in step.branches:
        return step.branches[branch_key]
    return step.next_step_code


def _kind_from_name(name: str) -> str:
    """Détecte le « kind » d'un workflow à partir de son nom (pour mapper
    vers le handoff correspondant, ex. workflow consultation → handoff_consultation)."""
    n = (name or "").lower()
    if "consultation" in n:
        return "consultation"
    if "mise" in n or "modification" in n or "update" in n:
        return "modification"
    if "chat" in n or "faq" in n or "question" in n:
        return "chat"
    if "inscription" in n or "enrôl" in n or "enrol" in n:
        return "inscription"
    return ""


async def _resolve_dynamic_router(
    db: AsyncSession,
    *,
    current_workflow_id: UUID,
    user_input: Optional[str],
    steps_index: dict[str, WorkflowStep],
) -> Optional[str]:
    """Pour les steps marqués `meta.dynamic_router = "by_workflow_position"` :
    résout le step suivant en fonction de la position du workflow choisi.

    - L'utilisateur tape un chiffre (1, 2, 3…)
    - On récupère la liste des workflows ordonnés par created_at
    - Le N-ième workflow détermine la destination :
      * Si c'est le workflow courant → next_step_code ou branche `self`
      * Sinon → cherche un step `handoff_<kind>` dans le workflow courant

    Retourne le code de step à utiliser, ou None si pas de match.
    """
    if not user_input:
        return None
    try:
        idx = int(user_input.strip())
    except ValueError:
        return None
    if idx < 1:
        return None

    # Ne considère QUE les workflows actifs : un handoff vers un workflow
    # désactivé mène à un cul-de-sac. Le compte doit rester cohérent avec
    # ce que l'utilisateur voit dans le menu.
    result = await db.execute(
        select(Workflow)
        .where(Workflow.active.is_(True))
        .order_by(Workflow.position.asc(), Workflow.created_at.asc())
    )
    workflows = list(result.scalars().all())
    if idx > len(workflows):
        return None

    target = workflows[idx - 1]
    # Cas 1 : la cible EST le workflow courant → continuer dans ce workflow
    if target.id == current_workflow_id:
        return "__self__"

    # Cas 2 : workflow différent → on veut TRANSITER vers le workflow cible.
    # On retourne son start_step_code sous forme `__switch__:code` que le
    # dispatcher détectera et utilisera pour changer de workflow.
    if target.start_step_code:
        return f"__switch__:{target.start_step_code}"
    return None


# ----------------------------------------------------------------------
# ENTRÉE PRINCIPALE
# ----------------------------------------------------------------------
async def execute(
    db: AsyncSession,
    *,
    workflow: Workflow,
    tenant_id: UUID,
    current_step_code: Optional[str],
    user_input: Optional[str],
    context: dict,
) -> ExecuteResult:
    """Avance le workflow d'un tour.

    Si `current_step_code` est None : démarre au `workflow.start_step_code`.
    Sinon : consomme `user_input` comme réponse à la question courante,
    valide, puis enchaîne les transitions automatiques (message/action/
    decision) jusqu'à la prochaine question.

    Le caller doit persister `result.next_step_code` et `result.context`.
    """
    steps_by_code = _build_step_index(workflow)
    ctx = dict(context or {})
    # Injecte tenant_id dans le contexte pour que les actions puissent
    # appeler les services tenant-scoped (settings, email, OTP, etc.)
    ctx["_tenant_id"] = str(tenant_id)
    out_messages: list[str] = []

    # ---- Phase 1 : si on est sur une question, consommer la réponse
    if current_step_code:
        current = steps_by_code.get(current_step_code)
        if current is None:
            return ExecuteResult(
                error=f"Étape '{current_step_code}' inexistante dans le workflow.",
                context=ctx,
            )

        if current.type == WorkflowStepType.question:
            error = _validate_question_input(current, user_input or "")
            if error:
                # Reste sur la même question, mais ajoute le message d'erreur
                # devant le re-prompt du template
                reprompt = await _render_or_fallback(db, tenant_id, current, ctx)
                return ExecuteResult(
                    messages=[f"⚠️ {error}\n\n{reprompt}"],
                    next_step_code=current.code,
                    context=ctx,
                )
            # Stocke la réponse dans le contexte sous une clé déduite du code
            ctx[current.code] = (user_input or "").strip()
            ctx[f"{current.code}_input"] = (user_input or "").strip()

            # Résolveur dynamique : si le step est marqué `meta.dynamic_router =
            # "by_workflow_position"`, on résout vers le bon handoff selon le
            # numéro tapé par l'utilisateur (mappé à la liste réelle des
            # workflows en BD).
            next_code = None
            if (current.meta or {}).get("dynamic_router") == "by_workflow_position":
                resolved = await _resolve_dynamic_router(
                    db,
                    current_workflow_id=workflow.id,
                    user_input=user_input,
                    steps_index=steps_by_code,
                )
                if resolved == "__self__":
                    # L'utilisateur a tapé le numéro du workflow courant — on
                    # suit le chemin nominal (branche "self" si définie, sinon
                    # next_step_code).
                    next_code = current.branches.get("self") or current.next_step_code
                elif resolved and resolved.startswith("__switch__:"):
                    # Basculement inter-parcours : le dispatcher va charger le
                    # workflow contenant ce step et relancer execute() dessus.
                    return ExecuteResult(
                        messages=out_messages,
                        next_step_code=None,
                        is_terminal=False,
                        context=ctx,
                        switch_to_step=resolved.split(":", 1)[1],
                    )
                elif resolved:
                    next_code = resolved

            # Fallback : routage selon l'input utilisateur
            if next_code is None:
                normalised = (user_input or "").strip().lower()
                branch = None
                branches = current.branches or {}
                # Priorité 1 : "on_refused" pour "2"/"non" (cas certification ARTCI)
                if normalised in {"non", "no", "refus", "refuser", "2"} and "on_refused" in branches:
                    branch = "on_refused"
                # Priorité 2 : "on_correction" pour "2"/"corriger" (cas validation OCR)
                elif normalised in {"corriger", "correction", "2"} and "on_correction" in branches:
                    branch = "on_correction"
                # Priorité 3 : l'input matche directement une clé de branche
                # (ex. menu numérique : "1" → branches["1"], "2" → branches["2"]…)
                elif normalised in branches:
                    branch = normalised
                next_code = _resolve_next_code(current, branch)
        else:
            # current n'est pas une question — on enchaîne depuis lui (cas exotique)
            next_code = current.code
    else:
        # Démarrage du parcours
        next_code = workflow.start_step_code
        if not next_code:
            return ExecuteResult(
                error="Workflow sans étape de démarrage configurée.", context=ctx,
            )

    # ---- Phase 2 : enchaîne les transitions automatiques jusqu'à une question
    steps_run = 0
    while next_code is not None and steps_run < MAX_INTERNAL_STEPS:
        steps_run += 1
        step = steps_by_code.get(next_code)
        if step is None:
            return ExecuteResult(
                error=f"Étape '{next_code}' référencée mais inexistante.",
                messages=out_messages,
                next_step_code=None,
                is_terminal=True,
                context=ctx,
            )

        if step.type == WorkflowStepType.message:
            text = await _render_or_fallback(db, tenant_id, step, ctx)
            out_messages.append(text)
            # Basculement inter-workflow : si `meta.switch_to_step = "code"`,
            # le dispatcher change de workflow et démarre sur ce code.
            switch_target = (step.meta or {}).get("switch_to_step")
            if switch_target:
                return ExecuteResult(
                    messages=out_messages,
                    next_step_code=None,
                    is_terminal=False,
                    context=ctx,
                    switch_to_step=switch_target,
                )
            next_code = step.next_step_code
            if next_code is None:
                # Message terminal — fin du parcours
                return ExecuteResult(
                    messages=out_messages,
                    next_step_code=None,
                    is_terminal=True,
                    context=ctx,
                )
            continue

        if step.type == WorkflowStepType.question:
            text = await _render_or_fallback(db, tenant_id, step, ctx)
            out_messages.append(text)
            return ExecuteResult(
                messages=out_messages,
                next_step_code=step.code,
                context=ctx,
            )

        if step.type == WorkflowStepType.action:
            last_in = ctx.get(f"{current_step_code}_input") if current_step_code else None
            result = await _run_action(db, step, ctx, last_input=last_in)
            if result.extra_context:
                ctx.update(result.extra_context)
            if result.message:
                out_messages.append(result.message)
            next_code = _resolve_next_code(step, result.branch_key)
            if next_code is None:
                return ExecuteResult(
                    messages=out_messages,
                    next_step_code=None,
                    is_terminal=True,
                    context=ctx,
                )
            continue

        if step.type == WorkflowStepType.decision:
            # Pour la Phase 3 actuelle on traite decision comme un alias d'action
            # qui ne fait rien et suit next_step_code. À étendre avec un évaluateur
            # de conditions (jsonlogic, etc.) en Phase 3.5.
            next_code = _resolve_next_code(step, None)
            continue

        # Type inconnu : fin défensive
        return ExecuteResult(
            error=f"Type d'étape inconnu : {step.type}",
            messages=out_messages,
            next_step_code=None,
            is_terminal=True,
            context=ctx,
        )

    # Garde-fou anti-boucle
    return ExecuteResult(
        error="Boucle d'exécution interrompue (trop d'étapes automatiques enchaînées).",
        messages=out_messages,
        next_step_code=next_code,
        context=ctx,
    )
