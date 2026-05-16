"""Machine à états du parcours d'identification MA2E.

PRD §8 — 14 étapes principales avec 3 portes de consentement critiques (GATES).
Chaque transition est journalisée (PRD §10.3).
"""
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Channel,
    ConsentDecision,
    ConsentGate,
    Conversation,
    Dossier,
    DossierStatus,
    Employeur,
    EndUser,
    Message,
    MessageDirection,
    PieceFace,
    PieceIdentite,
    PieceType,
    Tenant,
    TexteConsentement,
)
import logging

from app.core import storage
from app.services import consent_service, dossiers as dossier_service, ocr_mindee
from app.services.rag import answer_question, fetch_history
from app.conversation.intent_router import detect_intent

logger = logging.getLogger(__name__)


class OCRError(Exception):
    pass


def _detect_filename_by_magic(data: bytes, fallback: str = "image.jpg") -> str:
    """Détecte le type d'image via les magic bytes et retourne un filename correct.

    Évite que les fichiers WhatsApp `.bin` soient rejetés par Mindee.
    """
    if not data or len(data) < 12:
        return fallback
    if data[:3] == b"\xff\xd8\xff":
        return "image.jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image.png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image.webp"
    if data[:4] in (b"II*\x00", b"MM\x00*"):
        return "image.tiff"
    if data[:4] == b"%PDF":
        return "document.pdf"
    if data[:8] in (b"ftypheic", b"ftypheix") or data[4:12] == b"ftypheic":
        return "image.heic"
    return fallback


async def _run_ocr_recto(media_url: str, piece_type: PieceType) -> dict:
    """OCR recto réel via Mindee. Lève OCRError en cas d'échec."""
    if not ocr_mindee.is_configured():
        raise OCRError("Mindee API key non configurée")
    if not media_url or not media_url.startswith("minio://"):
        raise OCRError("media_url invalide")
    file_bytes, original_filename = storage.get_object_bytes_from_url(media_url)
    filename = _detect_filename_by_magic(file_bytes, fallback=original_filename or "image.jpg")
    logger.info("OCR recto : %d bytes, filename=%s", len(file_bytes), filename)
    try:
        return await ocr_mindee.ocr_recto(file_bytes, filename, piece_type)
    except Exception as e:
        logger.error("OCR recto Mindee a échoué : %s", e)
        raise OCRError(str(e)) from e


async def _run_ocr_verso(media_url: str, piece_type: PieceType, recto_data: Optional[dict]) -> dict:
    """OCR verso réel via Mindee. Lève OCRError en cas d'échec."""
    if not ocr_mindee.is_configured():
        raise OCRError("Mindee API key non configurée")
    if not media_url or not media_url.startswith("minio://"):
        raise OCRError("media_url invalide")
    file_bytes, original_filename = storage.get_object_bytes_from_url(media_url)
    filename = _detect_filename_by_magic(file_bytes, fallback=original_filename or "image.jpg")
    logger.info("OCR verso : %d bytes, filename=%s", len(file_bytes), filename)
    try:
        return await ocr_mindee.ocr_verso(file_bytes, filename, piece_type, recto_data=recto_data)
    except Exception as e:
        logger.error("OCR verso Mindee a échoué : %s", e)
        raise OCRError(str(e)) from e

# ----------------------------------------------------------------------
# États du parcours (PRD §8.2)
# ----------------------------------------------------------------------
S_ACCUEIL = "accueil_langue"
S_MAIN_MENU = "menu_principal"
S_CONSENT_ARTCI = "consentement_artci"                # GATE 1
S_REFUS_FINAL = "refus_final"
S_MATRICULE = "saisie_matricule"
# Update flow
S_UPDATE_MATRICULE = "update_matricule"
S_UPDATE_FIELD_SELECT = "update_field_select"
S_UPDATE_VALUE = "update_value"
# Status flow
S_STATUS_MATRICULE = "status_matricule"
# Q&A libre (AYA)
S_QA_MODE = "qa_mode"
S_EMPLOYEUR = "confirmation_employeur"
S_FONCTION = "saisie_fonction"
S_ANCIENNETE = "saisie_anciennete"
S_FAMILLE = "saisie_famille"
S_CHOIX_PIECE = "choix_piece"
S_CAPTURE_RECTO = "capture_recto"
S_OCR_RECTO = "ocr_recto_en_cours"
S_CAPTURE_VERSO = "capture_verso"
S_OCR_VERSO = "ocr_verso_en_cours"
S_VALIDATION_OCR = "validation_donnees_ocr"           # GATE 2
S_CORRECTION = "correction_donnees"
S_RECAPITULATIF = "recapitulatif"                     # GATE 3
S_TRANSMIS = "transmis"
S_DONE = "done"

GREETINGS = {"bonjour", "salut", "hello", "hi", "bjr", "hey", "bonsoir", "/start", "menu", "/menu", "coucou", "allo", "yo"}
GREETING_PREFIXES = ("bonjour", "salut", "hello", "bonsoir", "bjr", "coucou", "allo", "hey")
GLOBAL_HELP = {"aide", "/aide", "help"}
GLOBAL_DROITS = {"droits", "/droits"}
GLOBAL_CANCEL = {"annuler", "/annuler", "stop", "cancel"}


@dataclass
class BotReply:
    text: str


# ======================================================================
#  ENTRY POINT
# ======================================================================
async def handle_message(
    db: AsyncSession,
    tenant: Tenant,
    conversation: Conversation,
    end_user: EndUser,
    text: str,
    has_media: bool = False,
    media_url: Optional[str] = None,
) -> BotReply:
    """Entrée principale : dispatch + traduction selon la langue choisie."""
    reply = await _dispatch_message(db, tenant, conversation, end_user, text, has_media, media_url)
    lang = (conversation.context or {}).get("lang", "fr")
    if lang == "en" and reply.text:
        try:
            translated = await _translate_to_english(reply.text)
            if translated:
                reply = BotReply(text=translated)
        except Exception as e:
            logger.warning("Translation to English failed: %s", e)
    return reply


async def _translate_to_english(text: str) -> str:
    """Traduit un message du français vers l'anglais en préservant le format."""
    from app.conversation import llm as _llm

    system = (
        "You are a professional French→English translator for a digital identification "
        "platform serving Côte d'Ivoire. Translate the user's French message to natural, "
        "professional English. Preserve EXACTLY: markdown formatting (*bold*, _italic_), "
        "all emojis, all numbers and option keys (e.g. '1)', '2)'), all line breaks, all "
        "technical references (ARTCI, MA2E, MRZ, ICAO, etc.) and brand names. Reply with "
        "ONLY the translation — no preamble, no explanation, no quotes."
    )
    out = await _llm.chat_complete(system_prompt=system, user_message=text)
    return (out or "").strip()


async def _dispatch_message(
    db: AsyncSession,
    tenant: Tenant,
    conversation: Conversation,
    end_user: EndUser,
    text: str,
    has_media: bool = False,
    media_url: Optional[str] = None,
) -> BotReply:
    """Dispatch interne selon l'état courant (texte canonique FR)."""
    raw = (text or "").strip()
    lower = raw.lower()

    if lower in GLOBAL_CANCEL:
        return await _cmd_cancel(db, tenant, conversation)
    if lower in GLOBAL_DROITS:
        return _cmd_droits(tenant)
    if lower in GLOBAL_HELP:
        return _cmd_help(conversation.state)

    # Bascule rapide de langue
    if lower in {"english", "anglais", "en"}:
        conversation.context["lang"] = "en"
        return BotReply(text="✅ Language set to English. How can I help you today?")
    if lower in {"français", "francais", "french", "fr"}:
        conversation.context["lang"] = "fr"
        return BotReply(text="✅ Langue définie sur le français. Que puis-je faire pour vous ?")

    # Raccourcis directs (tuiles du chat web) — bypass welcome + langue + menu
    if lower in {"/identification", "/identify", "/start_id"}:
        if not conversation.context.get("lang"):
            conversation.context["lang"] = "fr"
        conversation.state = S_CONSENT_ARTCI
        return await _show_consent_artci(db, tenant)
    if lower in {"/update", "/mise-a-jour", "/start_update"}:
        if not conversation.context.get("lang"):
            conversation.context["lang"] = "fr"
        conversation.state = S_UPDATE_MATRICULE
        return BotReply(
            text=(
                "*Mise à jour de votre dossier*\n\n"
                "Pour retrouver votre dossier, saisissez votre *matricule employeur* "
                "(6 à 10 caractères alphanumériques)."
            )
        )
    if lower in {"/status", "/statut", "/start_status"}:
        if not conversation.context.get("lang"):
            conversation.context["lang"] = "fr"
        conversation.state = S_STATUS_MATRICULE
        return BotReply(
            text=(
                "*Vérification du statut*\n\n"
                "Saisissez votre *matricule employeur* pour consulter l'état de votre dossier."
            )
        )

    # === Intent router LLM-only (AYA) ===
    # On lance le LLM pour TOUS les messages non triviaux (≥ 3 chars).
    # Placé AVANT le check "state==start" pour qu'une vraie question dès le 1er
    # message déclenche le RAG au lieu d'afficher l'accueil langue.
    skip_intent = (
        len(raw) < 3
        or raw.startswith("/")
        or raw.isdigit()  # choix de menu pur
    )
    if not skip_intent:
        try:
            intent = await detect_intent(raw, tenant_name=tenant.name)
        except Exception as e:
            logger.warning("intent detect failed: %s", e)
            intent = None

        if intent and intent.confidence >= 0.8:
            if intent.name == "greeting":
                conversation.context = {}
                conversation.state = "start"
                return await _step_accueil(conversation)
            if intent.name == "identification":
                conversation.context = {}
                conversation.state = S_CONSENT_ARTCI
                return await _show_consent_artci(db, tenant)
            if intent.name == "update":
                conversation.context = {}
                conversation.state = S_UPDATE_MATRICULE
                return BotReply(
                    text=(
                        "*Mise à jour de votre dossier*\n\n"
                        "Pour retrouver votre dossier, saisissez votre *matricule employeur* "
                        "(6 à 10 caractères alphanumériques)."
                    )
                )
            if intent.name == "status":
                conversation.context = {}
                conversation.state = S_STATUS_MATRICULE
                return BotReply(
                    text=(
                        "*Vérification du statut*\n\n"
                        "Saisissez votre *matricule employeur*."
                    )
                )
            if intent.name == "menu":
                conversation.context = {}
                conversation.state = S_MAIN_MENU
                return _show_main_menu()
            if intent.name == "cancel":
                return await _cmd_cancel(db, tenant, conversation)
            if intent.name == "droits":
                return _cmd_droits(tenant)
            if intent.name == "question":
                try:
                    hist = await fetch_history(db, conversation.id)
                    rag = await answer_question(
                        db,
                        tenant_id=tenant.id,
                        tenant_name=tenant.name,
                        question=raw,
                        history=hist,
                    )
                    suffix = ""
                    if rag.sources and rag.confidence >= 0.45:
                        urls = list(dict.fromkeys(s.source for s in rag.sources[:2]))
                        suffix = "\n\n_Source : " + " · ".join(urls) + "_"
                    return BotReply(text=rag.answer + suffix)
                except Exception as e:
                    logger.warning("rag failed: %s", e)
                    return BotReply(
                        text=(
                            "Je n'arrive pas à répondre pour le moment. "
                            "Tapez *menu* pour revenir aux options principales."
                        )
                    )

    # Fallback : si on est à l'état "start" ou "done" et qu'aucun intent n'a triggé,
    # on affiche l'accueil normal (choix langue).
    if conversation.state in {"start", S_DONE, S_REFUS_FINAL}:
        return await _step_accueil(conversation)

    handlers = {
        S_ACCUEIL: _step_accueil_choice,
        S_MAIN_MENU: _step_main_menu_choice,
        S_CONSENT_ARTCI: _step_consent_artci,
        S_MATRICULE: _step_matricule,
        S_EMPLOYEUR: _step_employeur,
        S_FONCTION: _step_fonction,
        S_ANCIENNETE: _step_anciennete,
        S_FAMILLE: _step_famille,
        S_CHOIX_PIECE: _step_choix_piece,
        S_CAPTURE_RECTO: _step_capture_recto,
        S_CAPTURE_VERSO: _step_capture_verso,
        S_VALIDATION_OCR: _step_validation_ocr,
        S_CORRECTION: _step_correction,
        S_RECAPITULATIF: _step_recapitulatif,
        S_TRANSMIS: _step_already_transmitted,
        S_UPDATE_MATRICULE: _step_update_matricule,
        S_UPDATE_FIELD_SELECT: _step_update_field_select,
        S_UPDATE_VALUE: _step_update_value,
        S_STATUS_MATRICULE: _step_status_matricule,
        S_QA_MODE: _step_qa_mode,
    }
    handler = handlers.get(conversation.state)
    if not handler:
        return await _step_accueil(conversation)

    return await handler(
        db=db, tenant=tenant, conversation=conversation, end_user=end_user,
        raw=raw, lower=lower, has_media=has_media, media_url=media_url,
    )


# ======================================================================
#  COMMANDES GLOBALES
# ======================================================================
async def _cmd_cancel(db: AsyncSession, tenant: Tenant, conversation: Conversation) -> BotReply:
    conversation.state = "start"
    conversation.context = {}
    await db.flush()
    return BotReply(
        text=(
            "❌ *Parcours annulé.*\n\n"
            f"Vos données saisies dans cette session ont été effacées.\n"
            "Tapez *bonjour* pour redémarrer un nouveau parcours."
        )
    )


def _cmd_droits(tenant: Tenant) -> BotReply:
    return BotReply(
        text=(
            "🔐 *Exercice de vos droits — Loi 2013-450 (Côte d'Ivoire)*\n\n"
            "Conformément à la loi sur la protection des données, vous disposez "
            "des droits suivants sur vos données personnelles :\n\n"
            "1️⃣  *Droit d'accès* — obtenir une copie de vos données\n"
            "2️⃣  *Droit de rectification* — corriger une donnée inexacte\n"
            "3️⃣  *Droit d'effacement* — demander la suppression\n"
            "4️⃣  *Droit d'opposition* — refuser un traitement\n"
            "5️⃣  *Droit de portabilité* — récupérer vos données\n"
            "6️⃣  *Droit de limitation*\n\n"
            "Pour exercer un droit, répondez par le numéro correspondant. "
            f"Votre DPO {tenant.name} traitera votre demande sous 30 jours.\n\n"
            "Recours possible auprès de l'ARTCI : www.artci.ci"
        )
    )


def _cmd_help(state: str) -> BotReply:
    contextual = {
        S_MATRICULE: "Votre matricule figure sur votre fiche de paie (6 à 10 caractères).",
        S_CAPTURE_RECTO: "Photographiez le recto de votre pièce, bien à plat, sans reflet.",
        S_CAPTURE_VERSO: "Photographiez le verso : la zone MRZ (lignes en bas) doit être nette.",
    }.get(state, "Suivez les instructions pas à pas. Tapez *menu* pour revoir l'option courante.")
    return BotReply(
        text=(
            "ℹ️ *Aide*\n\n"
            f"{contextual}\n\n"
            "Commandes utiles :\n"
            "• *AIDE* — afficher l'aide\n"
            "• *DROITS* — exercer vos droits ARTCI\n"
            "• *ANNULER* — abandonner le parcours en cours"
        )
    )


# ======================================================================
#  ÉTAPE 1 — Accueil & langue
# ======================================================================
async def _step_accueil(conversation: Conversation) -> BotReply:
    """Welcome chaleureux d'AYA. Saute l'étape langue (par défaut FR)
    et affiche directement le menu principal pour fluidifier l'expérience.
    """
    conversation.context = {"lang": "fr"}
    conversation.state = S_MAIN_MENU
    return BotReply(
        text=(
            "👋 *Bonjour, je suis AYA, votre assistante MA2E.*\n"
            "_Mutuelle des Agents de l'Eau et de l'Électricité_\n\n"
            "Très contente de vous accueillir 🌿\n\n"
            "Je peux vous aider à :\n"
            "• Vous identifier comme sociétaire\n"
            "• Mettre à jour vos informations\n"
            "• Suivre l'état de votre dossier\n"
            "• Répondre à toutes vos questions sur MA2E\n\n"
            "*Que souhaitez-vous faire ?*\n\n"
            "*1)* M'identifier (nouvel enrôlement)\n"
            "*2)* Mettre à jour mon dossier\n"
            "*3)* Vérifier le statut de mon dossier\n"
            "*4)* Poser une question sur MA2E 💬\n\n"
            "_For English, just type «english»._"
        )
    )


async def _step_accueil_choice(db, tenant, conversation, end_user, raw, lower, **_) -> BotReply:
    if raw not in {"1", "2"}:
        return BotReply(text="Merci de répondre par *1)* (Français) ou *2)* (English).")

    conversation.context["lang"] = "fr" if raw == "1" else "en"
    conversation.state = S_MAIN_MENU
    return _show_main_menu()


def _show_main_menu() -> BotReply:
    return BotReply(
        text=(
            "*Que souhaitez-vous faire ?*\n\n"
            "*1)* M'identifier (nouvel enrôlement)\n"
            "*2)* Mettre à jour mon dossier\n"
            "*3)* Vérifier le statut de mon dossier\n"
            "*4)* Poser une question sur MA2E 💬"
        )
    )


async def _step_main_menu_choice(db, tenant, conversation, end_user, raw, lower, **_) -> BotReply:
    if raw == "1":
        conversation.state = S_CONSENT_ARTCI
        return await _show_consent_artci(db, tenant)
    if raw == "2":
        conversation.state = S_UPDATE_MATRICULE
        return BotReply(
            text=(
                "*Mise à jour de votre dossier*\n\n"
                "Pour retrouver votre dossier, saisissez votre *matricule employeur* "
                "(6 à 10 caractères alphanumériques)."
            )
        )
    if raw == "3":
        conversation.state = S_STATUS_MATRICULE
        return BotReply(
            text=(
                "*Vérification du statut*\n\n"
                "Saisissez votre *matricule employeur* pour consulter l'état de votre dossier."
            )
        )
    if raw == "4":
        conversation.state = S_QA_MODE
        return BotReply(
            text=(
                "💬 *Posez-moi vos questions sur MA2E*\n\n"
                "Je peux vous renseigner sur :\n"
                "• Les produits d'épargne et de crédit\n"
                "• Les conditions d'adhésion\n"
                "• Les coordonnées et le fonctionnement\n"
                "• Vos droits et la conformité ARTCI\n\n"
                "_Tapez *menu* pour revenir aux options principales._"
            )
        )
    return BotReply(text="Choix invalide. Répondez *1)*, *2)*, *3)* ou *4)*.")


async def _step_update_matricule(db, tenant, conversation, end_user, raw, lower, **_) -> BotReply:
    from sqlalchemy import desc as _desc
    matricule = raw.upper().replace(" ", "")
    if not (6 <= len(matricule) <= 10) or not matricule.isalnum():
        return BotReply(text="⚠️ Matricule invalide. Format : 6 à 10 caractères alphanumériques.")

    stmt = (
        select(Dossier)
        .where(Dossier.tenant_id == tenant.id, Dossier.matricule == matricule)
        .order_by(_desc(Dossier.created_at))
        .limit(1)
    )
    dossier = (await db.execute(stmt)).scalar_one_or_none()
    if not dossier:
        conversation.state = S_MAIN_MENU
        return BotReply(
            text=(
                "❌ Aucun dossier trouvé avec ce matricule.\n\n"
                "Vérifiez votre matricule ou faites un nouvel enrôlement.\n\n"
                "Tapez *menu* pour revenir au menu principal."
            )
        )

    target_user = (
        await db.execute(select(EndUser).where(EndUser.id == dossier.end_user_id))
    ).scalar_one_or_none()
    target_name = target_user.name if (target_user and target_user.name) else "—"

    conversation.context["update_dossier_id"] = str(dossier.id)
    conversation.context["update_matricule"] = matricule
    conversation.state = S_UPDATE_FIELD_SELECT

    return BotReply(
        text=(
            f"✅ *Dossier trouvé* : `{dossier.dossier_number}`\n"
            f"Sociétaire : {target_name}\n"
            f"Employeur : {dossier.employeur_code or '—'}\n\n"
            "*Que souhaitez-vous mettre à jour ?*\n\n"
            "*1)* Téléphone WhatsApp\n"
            "*2)* Situation familiale\n"
            "*3)* Adresse\n"
            "*4)* Fonction professionnelle\n"
            "*5)* Annuler"
        )
    )


_UPDATE_FIELDS = {
    "1": ("phone", "Téléphone WhatsApp", "Saisissez votre nouveau numéro WhatsApp avec l'indicatif (ex: +225 07 00 00 00 00)."),
    "2": ("situation_familiale", "Situation familiale", "Précisez votre nouvelle situation : célibataire, marié(e), veuf(ve), divorcé(e)."),
    "3": ("address", "Adresse", "Saisissez votre nouvelle adresse complète."),
    "4": ("fonction", "Fonction", "Saisissez votre nouvelle fonction professionnelle."),
}


async def _step_update_field_select(db, tenant, conversation, end_user, raw, lower, **_) -> BotReply:
    if raw == "5":
        conversation.state = S_MAIN_MENU
        return _show_main_menu()
    if raw not in _UPDATE_FIELDS:
        return BotReply(text="Choix invalide. Répondez *1)*, *2)*, *3)*, *4)* ou *5)*.")

    field, label, prompt = _UPDATE_FIELDS[raw]
    conversation.context["update_field"] = field
    conversation.context["update_field_label"] = label
    conversation.state = S_UPDATE_VALUE
    return BotReply(text=f"*Mise à jour : {label}*\n\n{prompt}")


async def _step_update_value(db, tenant, conversation, end_user, raw, lower, **_) -> BotReply:
    from uuid import UUID as _UUID
    from app.models import AuditAction, DonneesPro
    from app.services import audit_service

    new_value = raw.strip()
    if len(new_value) < 2:
        return BotReply(text="⚠️ Valeur trop courte. Réessayez.")

    dossier_id = conversation.context.get("update_dossier_id")
    field = conversation.context.get("update_field")
    label = conversation.context.get("update_field_label", "champ")

    if not dossier_id or not field:
        conversation.state = S_MAIN_MENU
        return _show_main_menu()

    dossier = (
        await db.execute(select(Dossier).where(Dossier.id == _UUID(dossier_id)))
    ).scalar_one_or_none()
    if not dossier:
        conversation.state = S_MAIN_MENU
        return BotReply(text="❌ Dossier introuvable. Tapez *menu*.")

    target_user = (
        await db.execute(select(EndUser).where(EndUser.id == dossier.end_user_id))
    ).scalar_one_or_none()

    old_value: Optional[str] = None

    if field == "phone" and target_user:
        old_value = target_user.phone
        target_user.phone = new_value
    elif field == "address" and target_user:
        extra = dict(target_user.extra or {})
        old_value = extra.get("address")
        extra["address"] = new_value
        target_user.extra = extra
    elif field in {"situation_familiale", "fonction"}:
        dp = (
            await db.execute(select(DonneesPro).where(DonneesPro.dossier_id == dossier.id))
        ).scalar_one_or_none()
        if not dp:
            dp = DonneesPro(tenant_id=tenant.id, dossier_id=dossier.id)
            db.add(dp)
            await db.flush()
        old_value = getattr(dp, field, None)
        setattr(dp, field, new_value)
    else:
        return BotReply(text="⚠️ Champ non reconnu. Tapez *menu*.")

    await db.flush()

    await audit_service.log(
        db=db,
        tenant_id=tenant.id,
        action=AuditAction.dossier_complement_requested,
        resource_type="dossier",
        resource_id=str(dossier.id),
        actor_type="end_user",
        actor_id=str(end_user.id),
        details={
            "operation": "self_update",
            "field": field,
            "old_value": str(old_value) if old_value is not None else None,
            "new_value": new_value,
            "matricule": dossier.matricule,
        },
    )

    conversation.state = S_DONE
    conversation.context = {"lang": conversation.context.get("lang", "fr")}

    return BotReply(
        text=(
            f"✅ *{label}* mis à jour avec succès.\n\n"
            f"Nouvelle valeur : *{new_value}*\n"
            f"Dossier : `{dossier.dossier_number}`\n\n"
            "Vos données sont enregistrées et tracées dans le journal d'audit MA2E.\n\n"
            "Tapez *bonjour* pour revenir au menu."
        )
    )


async def _step_status_matricule(db, tenant, conversation, end_user, raw, lower, **_) -> BotReply:
    from sqlalchemy import desc as _desc
    matricule = raw.upper().replace(" ", "")
    if not (6 <= len(matricule) <= 10) or not matricule.isalnum():
        return BotReply(text="⚠️ Matricule invalide. Format : 6 à 10 caractères alphanumériques.")

    stmt = (
        select(Dossier)
        .where(Dossier.tenant_id == tenant.id, Dossier.matricule == matricule)
        .order_by(_desc(Dossier.created_at))
        .limit(1)
    )
    dossier = (await db.execute(stmt)).scalar_one_or_none()
    if not dossier:
        conversation.state = S_MAIN_MENU
        return BotReply(
            text=(
                "❌ Aucun dossier trouvé avec ce matricule.\n\n"
                "Vérifiez votre saisie ou créez un nouveau dossier.\n\n"
                "Tapez *menu* pour revenir au menu."
            )
        )

    target_user = (
        await db.execute(select(EndUser).where(EndUser.id == dossier.end_user_id))
    ).scalar_one_or_none()
    target_name = target_user.name if (target_user and target_user.name) else "—"

    status_labels = {
        "en_cours": "🔄 En cours de saisie",
        "soumis": "📤 Soumis — en attente de validation",
        "en_validation": "👀 En cours de validation",
        "valide": "✅ Validé",
        "rejete": "❌ Rejeté",
        "complement_requis": "⚠️ Complément requis",
    }
    status_label = status_labels.get(dossier.status.value, dossier.status.value)

    lines = [
        f"*Statut du dossier* `{dossier.dossier_number}`",
        "",
        f"👤 Sociétaire : {target_name}",
        f"🆔 Matricule  : {matricule}",
        f"🏢 Employeur  : {dossier.employeur_code or '—'}",
        f"📌 Statut     : {status_label}",
    ]
    if dossier.submitted_at:
        lines.append(f"📤 Soumis le  : {dossier.submitted_at.strftime('%d/%m/%Y à %Hh%M')}")
    if dossier.validated_at:
        lines.append(f"✓  Décidé le  : {dossier.validated_at.strftime('%d/%m/%Y à %Hh%M')}")
    if dossier.rejection_motive:
        lines.append("")
        lines.append(f"❌ *Motif de rejet :* {dossier.rejection_motive}")
    if dossier.additional_request:
        lines.append("")
        lines.append(f"⚠️ *Complément demandé :* {dossier.additional_request}")

    lines.append("")
    lines.append("Tapez *bonjour* pour revenir au menu.")

    conversation.state = S_DONE
    return BotReply(text="\n".join(lines))


# ======================================================================
#  MODE Q&A LIBRE (AYA)
# ======================================================================
async def _step_qa_mode(db, tenant, conversation, end_user, raw, lower, **_) -> BotReply:
    """Toute saisie ici est traitée comme une question → RAG avec historique.

    Note : les intentions claires (menu, identification, update, status, cancel)
    sont déjà attrapées en amont par le router LLM dans _dispatch_message.
    Si on arrive ici, c'est qu'il s'agit d'une question ou d'un input ambigu.
    """
    try:
        hist = await fetch_history(db, conversation.id)
        rag = await answer_question(
            db,
            tenant_id=tenant.id,
            tenant_name=tenant.name,
            question=raw,
            history=hist,
        )
        body = rag.answer
        if rag.sources and rag.confidence >= 0.45:
            urls = list(dict.fromkeys(s.source for s in rag.sources[:2]))
            body += "\n\n_Source : " + " · ".join(urls) + "_"
        body += "\n\n_Une autre question ? Tapez *menu* pour les options._"
        return BotReply(text=body)
    except Exception as e:
        logger.warning("rag in qa mode failed: %s", e)
        return BotReply(
            text=(
                "Désolé, je n'arrive pas à répondre pour le moment. "
                "Tapez *menu* pour revenir aux options principales."
            )
        )


# ======================================================================
#  GATE 1 — Consentement ARTCI
# ======================================================================
async def _show_consent_artci(db: AsyncSession, tenant: Tenant) -> BotReply:
    texte = await consent_service.get_current_text(db, tenant.id, ConsentGate.artci)
    body = texte.body if texte else "Texte de consentement indisponible."
    return BotReply(
        text=(
            f"🛑 *PORTE 1 / 3 — Consentement ARTCI*\n\n"
            f"{body}\n\n"
            "*1)* ✅ J'accepte\n"
            "*2)* ❌ Je refuse\n"
            "*3)* 📄 Voir la politique complète"
        )
    )


async def _step_consent_artci(db, tenant, conversation, end_user, raw, lower, **_) -> BotReply:
    if raw == "3":
        return BotReply(
            text=(
                f"📄 *Politique de protection des données — {tenant.name}*\n\n"
                "Document complet : https://ma2e.ci/confidentialite\n\n"
                "Répondez *1* pour accepter ou *2* pour refuser."
            )
        )
    if raw == "2":
        await consent_service.record_consent(
            db, tenant.id, end_user.id, None,
            ConsentGate.artci, ConsentDecision.refuse,
            channel=conversation.channel.value,
            ip_or_phone=end_user.phone or end_user.telegram_id,
        )
        conversation.state = S_REFUS_FINAL
        return BotReply(
            text=(
                "Nous respectons votre choix. ❌\n\n"
                "Sans votre consentement, l'enrôlement digital n'est pas possible.\n"
                "Vous pouvez vous présenter à l'agence MA2E la plus proche pour un "
                "enrôlement papier classique.\n\n"
                "📍 Siège MA2E : Plateau, Abidjan\n"
                "📞 +225 27 20 XX XX XX\n\n"
                "Tapez *bonjour* pour redémarrer."
            )
        )
    if raw != "1":
        return BotReply(text="Merci de répondre par *1*, *2* ou *3*.")

    dossier = await dossier_service.get_or_create_dossier(db, tenant, end_user, conversation)
    await consent_service.record_consent(
        db, tenant.id, end_user.id, dossier.id,
        ConsentGate.artci, ConsentDecision.accepte,
        channel=conversation.channel.value,
        ip_or_phone=end_user.phone or end_user.telegram_id,
    )
    conversation.context["dossier_id"] = str(dossier.id)
    conversation.state = S_MATRICULE
    return BotReply(
        text=(
            "✅ Consentement enregistré et signé cryptographiquement.\n"
            f"📋 Dossier ouvert : *{dossier.dossier_number}*\n\n"
            "*Étape 1/8 — Matricule employeur*\n"
            "Veuillez saisir votre matricule (6 à 10 caractères) :"
        )
    )


# ======================================================================
#  Étapes 3-5 — Données pro
# ======================================================================
async def _step_matricule(db, tenant, conversation, end_user, raw, lower, **_) -> BotReply:
    matricule = raw.upper().replace(" ", "")
    if not (6 <= len(matricule) <= 10) or not matricule.isalnum():
        attempts = conversation.context.get("matricule_attempts", 0) + 1
        conversation.context["matricule_attempts"] = attempts
        if attempts >= 3:
            return BotReply(
                text=(
                    "❌ Matricule non reconnu après 3 tentatives.\n"
                    "Un gestionnaire MA2E va vous contacter sous 24h.\n\n"
                    "Tapez *bonjour* pour redémarrer."
                )
            )
        return BotReply(
            text=(
                f"⚠️ Matricule invalide ({attempts}/3).\n"
                "Format attendu : 6 à 10 caractères alphanumériques."
            )
        )

    dossier = await _current_dossier(db, conversation)
    dossier.matricule = matricule

    employeurs = await _list_employeurs(db, tenant.id)
    conversation.context["matricule"] = matricule
    conversation.state = S_EMPLOYEUR
    options = "\n".join([f"*{i+1})* {e.name}" for i, e in enumerate(employeurs)])
    return BotReply(
        text=(
            f"✅ Matricule : *{matricule}*\n\n"
            "*Étape 2/8 — Employeur*\n"
            "Sélectionnez votre société employeur :\n\n"
            f"{options}"
        )
    )


async def _step_employeur(db, tenant, conversation, end_user, raw, lower, **_) -> BotReply:
    try:
        idx = int(raw) - 1
    except ValueError:
        return BotReply(text="Tapez le numéro correspondant à votre employeur.")

    employeurs = await _list_employeurs(db, tenant.id)
    if not (0 <= idx < len(employeurs)):
        return BotReply(text="Choix hors liste. Réessayez.")

    employeur = employeurs[idx]
    dossier = await _current_dossier(db, conversation)
    dossier.employeur_code = employeur.code

    conversation.context["employeur_code"] = employeur.code
    conversation.context["employeur_name"] = employeur.name
    conversation.state = S_FONCTION
    return BotReply(
        text=(
            f"✅ Employeur : *{employeur.name}*\n\n"
            "*Étape 3/8 — Fonction*\n"
            "Quelle est votre fonction actuelle ?"
        )
    )


async def _step_fonction(db, tenant, conversation, end_user, raw, lower, **_) -> BotReply:
    if len(raw) < 2:
        return BotReply(text="Merci de préciser votre fonction (au moins 2 caractères).")
    conversation.context["fonction"] = raw
    conversation.state = S_ANCIENNETE
    return BotReply(
        text=(
            f"✅ Fonction : *{raw}*\n\n"
            "*Étape 4/8 — Ancienneté*\n"
            "Combien d'années d'ancienneté chez votre employeur ? (chiffre)"
        )
    )


async def _step_anciennete(db, tenant, conversation, end_user, raw, lower, **_) -> BotReply:
    try:
        annees = int(raw)
        if not (0 <= annees <= 60):
            raise ValueError
    except ValueError:
        return BotReply(text="Merci de saisir un nombre d'années entre 0 et 60.")

    conversation.context["anciennete"] = annees
    conversation.state = S_FAMILLE
    return BotReply(
        text=(
            f"✅ Ancienneté : *{annees} ans*\n\n"
            "*Étape 5/8 — Situation familiale*\n\n"
            "*1)* Célibataire\n"
            "*2)* Marié(e)\n"
            "*3)* Veuf/Veuve\n"
            "*4)* Divorcé(e)"
        )
    )


async def _step_famille(db, tenant, conversation, end_user, raw, lower, **_) -> BotReply:
    mapping = {"1": "celibataire", "2": "marie", "3": "veuf", "4": "divorce"}
    if raw not in mapping:
        return BotReply(text="Choix invalide. Répondez 1, 2, 3 ou 4.")
    conversation.context["situation"] = mapping[raw]
    conversation.state = S_CHOIX_PIECE
    return BotReply(
        text=(
            "✅ Situation enregistrée.\n\n"
            "*Étape 6/8 — Type de pièce d'identité*\n"
            "Quel type de pièce allez-vous présenter ?\n\n"
            "*1)* CNI UEMOA (Côte d'Ivoire)\n"
            "*2)* Carte Consulaire\n"
            "*3)* Carte de Résident"
        )
    )


# ======================================================================
#  Étapes 6-10 — Pièce d'identité + OCR
# ======================================================================
async def _step_choix_piece(db, tenant, conversation, end_user, raw, lower, **_) -> BotReply:
    mapping = {"1": PieceType.cni_uemoa, "2": PieceType.carte_consulaire, "3": PieceType.carte_resident}
    if raw not in mapping:
        return BotReply(text="Choix invalide. Répondez 1, 2 ou 3.")
    piece_type = mapping[raw]
    conversation.context["piece_type"] = piece_type.value
    conversation.state = S_CAPTURE_RECTO
    return BotReply(
        text=(
            "✅ Type enregistré.\n\n"
            "*Étape 7/8 — Photo recto*\n\n"
            "📸 Envoyez maintenant une photo *claire* du *recto* de votre pièce :\n"
            "✓ Bien éclairée, sans reflet\n"
            "✓ Pièce à plat, cadrage net\n"
            "✓ Format JPEG ou PNG"
        )
    )


async def _step_capture_recto(db, tenant, conversation, end_user, raw, lower, has_media, media_url, **_) -> BotReply:
    if not has_media or not media_url:
        return BotReply(text="📷 Veuillez *envoyer une photo* du recto (pas de texte).")

    dossier = await _current_dossier(db, conversation)
    piece_type = PieceType(conversation.context["piece_type"])
    piece = await dossier_service.attach_piece(
        db, tenant.id, dossier, piece_type, PieceFace.recto, media_url
    )
    conversation.context["recto_piece_id"] = str(piece.id)
    conversation.state = S_OCR_RECTO

    try:
        ocr_result = await _run_ocr_recto(media_url, piece_type)
    except OCRError as e:
        conversation.state = S_CAPTURE_RECTO
        return BotReply(
            text=(
                "❌ *Impossible d'analyser cette photo.*\n\n"
                "Veuillez réessayer en respectant ces consignes :\n"
                "✓ Bonne lumière, sans reflet\n"
                "✓ Pièce à plat, cadrage complet\n"
                "✓ Texte net et lisible\n\n"
                "📸 Renvoyez une nouvelle photo du *recto*."
            )
        )

    if not ocr_result.get("fields", {}).get("nom") and not ocr_result.get("fields", {}).get("numero_piece"):
        conversation.state = S_CAPTURE_RECTO
        return BotReply(
            text=(
                "⚠️ *Données illisibles sur cette photo.*\n\n"
                "Aucune information lisible n'a pu être extraite. Réessayez avec :\n"
                "✓ Meilleure lumière\n"
                "✓ Pièce d'identité bien à plat\n"
                "✓ Texte parfaitement net\n\n"
                "📸 Renvoyez une nouvelle photo du *recto*."
            )
        )

    await dossier_service.store_ocr_result(db, piece, ocr_result)
    conversation.context["ocr_recto"] = ocr_result

    extracted_fields = ocr_result.get("fields", {}) or {}
    nom = extracted_fields.get("nom")
    prenoms = extracted_fields.get("prenoms")
    full_name = " ".join([p for p in [prenoms, nom] if p]).strip()
    if full_name:
        end_user.name = full_name
        await db.flush()

    conversation.state = S_CAPTURE_VERSO
    f = ocr_result["fields"]
    return BotReply(
        text=(
            f"✅ Recto analysé ({int(ocr_result['confidence'] * 100)}% de confiance)\n\n"
            f"Données extraites :\n"
            f"• Nom : {f.get('nom', '—')}\n"
            f"• Prénoms : {f.get('prenoms', '—')}\n"
            f"• N° pièce : {f.get('numero_piece', '—')}\n"
            f"• Né(e) le : {f.get('date_naissance', '—')}\n\n"
            "*Étape 8/8 — Photo verso*\n"
            "📸 Envoyez maintenant le *verso* (la zone MRZ doit être nette)."
        )
    )


async def _step_capture_verso(db, tenant, conversation, end_user, raw, lower, has_media, media_url, **_) -> BotReply:
    if not has_media or not media_url:
        return BotReply(text="📷 Veuillez *envoyer une photo* du verso.")

    dossier = await _current_dossier(db, conversation)
    piece_type = PieceType(conversation.context["piece_type"])
    piece = await dossier_service.attach_piece(
        db, tenant.id, dossier, piece_type, PieceFace.verso, media_url
    )
    conversation.state = S_OCR_VERSO

    recto = conversation.context.get("ocr_recto")
    try:
        ocr_result = await _run_ocr_verso(media_url, piece_type, recto_data=recto)
    except OCRError as e:
        conversation.state = S_CAPTURE_VERSO
        return BotReply(
            text=(
                "❌ *Impossible d'analyser le verso.*\n\n"
                "La zone MRZ (lignes de codes en bas) doit être bien nette.\n"
                "📸 Renvoyez une nouvelle photo du *verso*."
            )
        )

    await dossier_service.store_ocr_result(db, piece, ocr_result)
    conversation.context["ocr_verso"] = ocr_result
    conversation.state = S_VALIDATION_OCR

    return await _show_ocr_validation(conversation)


# ======================================================================
#  GATE 2 — Validation OCR
# ======================================================================
async def _show_ocr_validation(conversation: Conversation) -> BotReply:
    recto = conversation.context.get("ocr_recto", {}).get("fields", {})
    return BotReply(
        text=(
            "🛑 *PORTE 2 / 3 — Validation des données extraites*\n\n"
            "Voici les informations lues sur votre pièce d'identité :\n\n"
            f"👤 *Nom*        : {recto.get('nom', '—')}\n"
            f"👤 *Prénoms*    : {recto.get('prenoms', '—')}\n"
            f"🆔 *N° pièce*   : {recto.get('numero_piece', '—')}\n"
            f"📅 *Né(e) le*   : {recto.get('date_naissance', '—')}\n"
            f"🏙️ *Lieu*       : {recto.get('lieu_naissance', '—')}\n"
            f"🌍 *Nationalité*: {recto.get('nationalite', '—')}\n\n"
            "Ces informations sont-elles correctes ?\n\n"
            "*1)* ✅ Oui, tout est correct\n"
            "*2)* ✏️ Non, je veux corriger"
        )
    )


async def _step_validation_ocr(db, tenant, conversation, end_user, raw, lower, **_) -> BotReply:
    if raw == "2":
        conversation.state = S_CORRECTION
        return BotReply(
            text=(
                "✏️ *Correction*\n\n"
                "Veuillez indiquer en un seul message le ou les champs à corriger.\n"
                "Exemple : « Nom : KOUASSI ; Date : 1985-04-12 »"
            )
        )
    if raw != "1":
        return BotReply(text="Répondez *1* (correct) ou *2* (corriger).")

    dossier = await _current_dossier(db, conversation)
    await consent_service.record_consent(
        db, tenant.id, end_user.id, dossier.id,
        ConsentGate.ocr_validation, ConsentDecision.accepte,
        channel=conversation.channel.value,
        ip_or_phone=end_user.phone or end_user.telegram_id,
    )
    conversation.state = S_RECAPITULATIF
    return await _show_recap(db, conversation)


async def _step_correction(db, tenant, conversation, end_user, raw, lower, **_) -> BotReply:
    corrections = conversation.context.get("corrections", [])
    corrections.append(raw)
    conversation.context["corrections"] = corrections

    dossier = await _current_dossier(db, conversation)
    if dossier.pieces:
        for piece in dossier.pieces:
            if piece.face == PieceFace.recto:
                piece.user_corrections = {"raw_text": raw}
                break
    await db.flush()

    conversation.state = S_RECAPITULATIF
    return await _show_recap(db, conversation)


# ======================================================================
#  GATE 3 — Récapitulatif et certification finale
# ======================================================================
async def _show_recap(db: AsyncSession, conversation: Conversation) -> BotReply:
    ctx = conversation.context
    recto = ctx.get("ocr_recto", {}).get("fields", {})
    dossier = await _current_dossier(db, conversation)

    return BotReply(
        text=(
            "🛑 *PORTE 3 / 3 — Récapitulatif et certification*\n\n"
            f"📋 *Dossier*       : {dossier.dossier_number}\n\n"
            "*— Identité —*\n"
            f"Nom complet     : {recto.get('prenoms', '')} {recto.get('nom', '')}\n"
            f"N° pièce        : {recto.get('numero_piece', '—')}\n"
            f"Né(e) le        : {recto.get('date_naissance', '—')}\n\n"
            "*— Profession —*\n"
            f"Matricule       : {ctx.get('matricule', '—')}\n"
            f"Employeur       : {ctx.get('employeur_name', '—')}\n"
            f"Fonction        : {ctx.get('fonction', '—')}\n"
            f"Ancienneté      : {ctx.get('anciennete', '—')} ans\n"
            f"Situation       : {ctx.get('situation', '—')}\n\n"
            "*Je certifie sur l'honneur l'exactitude de ces informations.*\n\n"
            "*1)* ✅ Je certifie et soumets mon dossier\n"
            "*2)* ❌ Annuler"
        )
    )


async def _step_recapitulatif(db, tenant, conversation, end_user, raw, lower, **_) -> BotReply:
    if raw == "2":
        return await _cmd_cancel(db, tenant, conversation)
    if raw != "1":
        return BotReply(text="Répondez *1* pour certifier ou *2* pour annuler.")

    dossier = await _current_dossier(db, conversation)

    await consent_service.record_consent(
        db, tenant.id, end_user.id, dossier.id,
        ConsentGate.certification_finale, ConsentDecision.accepte,
        channel=conversation.channel.value,
        ip_or_phone=end_user.phone or end_user.telegram_id,
    )

    ctx = conversation.context
    await dossier_service.upsert_donnees_pro(
        db, tenant.id, dossier,
        fonction=ctx.get("fonction"),
        anciennete_annees=ctx.get("anciennete"),
        situation_familiale=ctx.get("situation"),
    )
    await dossier_service.submit_dossier(db, dossier)

    conversation.state = S_TRANSMIS
    return BotReply(
        text=(
            "🎉 *Votre dossier est transmis !*\n\n"
            f"📋 Numéro : *{dossier.dossier_number}*\n"
            "📅 Délai de traitement : *24 à 72 heures*\n\n"
            "Vous recevrez une notification dès la décision de validation.\n\n"
            "_Tapez *DROITS* à tout moment pour exercer vos droits ARTCI._\n"
            "_Tapez *bonjour* pour démarrer un nouveau parcours._"
        )
    )


async def _step_already_transmitted(db, tenant, conversation, end_user, raw, lower, **_) -> BotReply:
    return BotReply(
        text=(
            "⏳ Votre dossier est déjà transmis et en cours de traitement.\n"
            "Tapez *bonjour* pour démarrer un nouveau parcours."
        )
    )


# ======================================================================
#  HELPERS
# ======================================================================
async def get_or_create_end_user(
    db: AsyncSession, tenant_id: UUID, channel: Channel, external_id: str, name: Optional[str]
) -> EndUser:
    if channel == Channel.whatsapp:
        stmt = select(EndUser).where(EndUser.tenant_id == tenant_id, EndUser.phone == external_id)
    else:
        stmt = select(EndUser).where(EndUser.tenant_id == tenant_id, EndUser.telegram_id == external_id)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if user:
        return user

    user = EndUser(
        tenant_id=tenant_id,
        phone=external_id if channel == Channel.whatsapp else None,
        telegram_id=external_id if channel in (Channel.telegram, Channel.web) else None,
        name=name,
    )
    db.add(user)
    await db.flush()
    return user


async def get_or_create_conversation(
    db: AsyncSession, tenant_id: UUID, end_user: EndUser, channel: Channel
) -> Conversation:
    stmt = (
        select(Conversation)
        .where(
            Conversation.tenant_id == tenant_id,
            Conversation.end_user_id == end_user.id,
            Conversation.channel == channel,
        )
        .order_by(Conversation.last_activity_at.desc())
    )
    conv = (await db.execute(stmt)).scalars().first()
    if conv:
        return conv

    conv = Conversation(
        tenant_id=tenant_id, end_user_id=end_user.id, channel=channel,
        state="start", context={},
    )
    db.add(conv)
    await db.flush()
    return conv


async def record_message(
    db: AsyncSession,
    tenant_id: UUID,
    conversation: Conversation,
    direction: MessageDirection,
    content: Optional[str],
    media_url: Optional[str] = None,
    extra: Optional[dict] = None,
) -> Message:
    msg = Message(
        tenant_id=tenant_id,
        conversation_id=conversation.id,
        direction=direction,
        content=content,
        media_url=media_url,
        extra=extra or {},
    )
    db.add(msg)
    await db.flush()
    return msg


async def _current_dossier(db: AsyncSession, conversation: Conversation) -> Dossier:
    dossier_id = conversation.context.get("dossier_id")
    if dossier_id:
        from uuid import UUID as _UUID
        d = (await db.execute(select(Dossier).where(Dossier.id == _UUID(dossier_id)))).scalar_one_or_none()
        if d:
            return d
    stmt = (
        select(Dossier)
        .where(Dossier.conversation_id == conversation.id)
        .order_by(Dossier.created_at.desc())
        .limit(1)
    )
    d = (await db.execute(stmt)).scalar_one_or_none()
    if not d:
        raise RuntimeError("dossier not found")
    return d


async def _list_employeurs(db: AsyncSession, tenant_id: UUID) -> list[Employeur]:
    stmt = (
        select(Employeur)
        .where(Employeur.tenant_id == tenant_id, Employeur.is_active.is_(True))
        .order_by(Employeur.name)
    )
    return list((await db.execute(stmt)).scalars().all())
