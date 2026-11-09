"""Service d'envoi de notifications aux sociétaires.

Détecte automatiquement le canal (WhatsApp / Web) selon le end_user et le tenant,
envoie le message, et journalise dans la conversation.
"""
from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Channel,
    Conversation,
    EndUser,
    Message,
    MessageDirection,
    Tenant,
    TenantChannel,
)

log = logging.getLogger(__name__)


async def notify_end_user(
    db: AsyncSession,
    *,
    tenant: Tenant,
    end_user: EndUser,
    text: str,
    also_send_email: bool = False,
    email_subject: Optional[str] = None,
) -> dict:
    """Envoie un message au sociétaire sur son canal d'origine.

    Stratégie :
    - Cherche la conversation la plus récente du end_user pour ce tenant
    - Détermine le canal (whatsapp / web)
    - Envoie via le bon canal
    - Si `also_send_email=True` et l'email du sociétaire est connu (extra.email
      ou récupéré depuis le dossier), envoie aussi par email (US-23 AC2).
    - Journalise le message en DB
    """
    # Récupère la dernière conversation du sociétaire
    conv_stmt = (
        select(Conversation)
        .where(
            Conversation.tenant_id == tenant.id,
            Conversation.end_user_id == end_user.id,
        )
        .order_by(Conversation.last_activity_at.desc())
        .limit(1)
    )
    conversation = (await db.execute(conv_stmt)).scalar_one_or_none()
    if not conversation:
        log.warning("Pas de conversation pour end_user=%s tenant=%s", end_user.id, tenant.id)
        return {"sent": False, "reason": "no_conversation"}

    channel = conversation.channel
    result = {"sent": False, "channel": channel.value}

    if channel == Channel.whatsapp:
        ok = await _send_whatsapp(db, tenant, end_user, text)
        result["sent"] = ok
    elif channel == Channel.web:
        # Pour le web : on enregistre juste le message en DB, le frontend pollera
        ok = True
        result["sent"] = ok
    else:
        log.warning("Canal non géré pour notification : %s", channel)
        return result

    if result["sent"]:
        db.add(
            Message(
                tenant_id=tenant.id,
                conversation_id=conversation.id,
                direction=MessageDirection.outbound,
                content=text,
                extra={"source": "notification", "channel": channel.value},
            )
        )
        await db.flush()

    # === Doublage email (US-23 AC2) — best-effort, ne bloque pas le résultat ===
    if also_send_email:
        email = _resolve_end_user_email(end_user)
        if email:
            try:
                from app.services.email_service import send_email
                subject = email_subject or "[MA2E] Notification de votre dossier"
                html = _text_to_html(text)
                er = await send_email(email, subject, html, text_body=text)
                result["email_sent"] = er.sent
                if not er.sent:
                    result["email_error"] = er.error
            except Exception as e:  # noqa: BLE001
                log.warning("Email doublé échoué pour %s : %s", email, e)
                result["email_sent"] = False
                result["email_error"] = str(e)[:200]
        else:
            result["email_sent"] = False
            result["email_error"] = "Pas d'email connu pour ce sociétaire"

    return result


def _resolve_end_user_email(end_user: EndUser) -> Optional[str]:
    """Retourne l'email du sociétaire s'il est connu (extra.email ou champ dédié)."""
    if end_user.extra and isinstance(end_user.extra, dict):
        return end_user.extra.get("email")
    return None


def _text_to_html(text: str) -> str:
    """Conversion minimale texte → HTML pour l'email."""
    safe = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br>")
    )
    return (
        "<div style=\"font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; "
        "background: #F6FAF7; padding: 20px; color: #1a1a1a;\">"
        "<div style=\"max-width: 480px; margin: 0 auto; background: #fff; border-radius: 6px; "
        "padding: 24px; border: 1px solid #e5e7eb; font-size: 14px; line-height: 1.6;\">"
        f"{safe}"
        "</div>"
        "<p style=\"max-width: 480px; margin: 12px auto 0; font-size: 11px; color: #9ca3af; text-align: center;\">"
        "MA2E — Mutuelle des Agents de l'Eau et de l'Électricité"
        "</p>"
        "</div>"
    )


async def _send_whatsapp(
    db: AsyncSession, tenant: Tenant, end_user: EndUser, text: str
) -> bool:
    """Envoie un message WhatsApp via Meta Cloud API."""
    if not end_user.phone:
        log.warning("end_user sans phone, impossible d'envoyer WhatsApp")
        return False

    # Récupère le canal WhatsApp du tenant (le plus récent si plusieurs) pour
    # avoir token + phone_id. `.first()` évite MultipleResultsFound quand une
    # rotation d'external_id a créé un doublon en BD.
    channel_stmt = (
        select(TenantChannel)
        .where(
            TenantChannel.tenant_id == tenant.id,
            TenantChannel.channel == Channel.whatsapp,
            TenantChannel.is_active == True,  # noqa: E712
        )
        .order_by(TenantChannel.created_at.desc())
        .limit(1)
    )
    channel_record = (await db.execute(channel_stmt)).scalar_one_or_none()
    if not channel_record:
        log.warning("Tenant %s n'a pas de canal WhatsApp actif", tenant.slug)
        return False

    creds = channel_record.credentials or {}
    access_token = creds.get("access_token")
    phone_number_id = creds.get("phone_number_id")
    if not access_token or not phone_number_id:
        log.warning("Credentials WhatsApp incomplets pour %s", tenant.slug)
        return False

    # Normalise le numéro (sans +)
    to = end_user.phone.lstrip("+").replace(" ", "")

    url = f"https://graph.facebook.com/v21.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    body = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text[:4096]},
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=body, headers=headers)
            if resp.status_code >= 400:
                log.error("WhatsApp notif failed: %s %s", resp.status_code, resp.text[:300])
                return False
            return True
    except Exception as e:
        log.exception("WhatsApp notif exception: %s", e)
        return False


# ----------------------------------------------------------------------
# Templates de messages MA2E (chargés depuis message_template_service)
#
# Chaque fonction rend le template enregistré pour le tenant. En cas
# d'erreur (template manquant, BD down…), un fallback hardcodé prend
# le relais pour garantir la livraison du message.
# ----------------------------------------------------------------------
def _first_name(full_name: Optional[str]) -> str:
    if not full_name:
        return ""
    return full_name.strip().split(" ")[0]


async def msg_dossier_valide(
    db: AsyncSession,
    tenant_id: UUID,
    dossier_number: str,
    name: Optional[str] = None,
    numero_societaire: Optional[str] = None,
) -> str:
    from app.services import message_template_service
    try:
        _, content = await message_template_service.render(
            db,
            tenant_id=tenant_id,
            code="validation.dossier_valide",
            variables={
                "prenom": _first_name(name),
                "numero_dossier": dossier_number,
                "numero_societaire": numero_societaire or dossier_number,
            },
        )
        return content
    except Exception as e:  # noqa: BLE001
        log.warning("Template validation.dossier_valide indisponible (%s), fallback", e)
        prefix = f"Bonjour {name}, " if name else "Bonjour, "
        membership = (
            f"\nVotre numéro de sociétaire est : *{numero_societaire}*\n"
            if numero_societaire else ""
        )
        return (
            f"✅ {prefix}votre dossier MA2E *{dossier_number}* vient d'être *validé* !\n\n"
            f"Vous êtes officiellement enregistré comme sociétaire MA2E.{membership}\n"
            f"Merci de votre confiance.\n— Équipe MA2E"
        )


async def msg_dossier_rejete(
    db: AsyncSession,
    tenant_id: UUID,
    dossier_number: str,
    motive: str,
    name: Optional[str] = None,
) -> str:
    from app.services import message_template_service
    try:
        _, content = await message_template_service.render(
            db,
            tenant_id=tenant_id,
            code="validation.dossier_refuse",
            variables={
                "prenom": _first_name(name),
                "numero_dossier": dossier_number,
                "motif": motive,
            },
        )
        return content
    except Exception as e:  # noqa: BLE001
        log.warning("Template validation.dossier_refuse indisponible (%s), fallback", e)
        prefix = f"Bonjour {name}, " if name else "Bonjour, "
        return (
            f"❌ {prefix}votre dossier MA2E *{dossier_number}* n'a pas pu être validé.\n\n"
            f"*Motif :* {motive}\n\n"
            f"Vous pouvez reprendre la conversation pour soumettre un nouveau dossier.\n"
            f"— Équipe MA2E"
        )


async def msg_complement_requis(
    db: AsyncSession,
    tenant_id: UUID,
    dossier_number: str,
    request_text: str,
    name: Optional[str] = None,
) -> str:
    from app.services import message_template_service
    try:
        _, content = await message_template_service.render(
            db,
            tenant_id=tenant_id,
            code="validation.complement_requested",
            variables={
                "prenom": _first_name(name),
                "numero_dossier": dossier_number,
                "elements_requis": request_text,
            },
        )
        return content
    except Exception as e:  # noqa: BLE001
        log.warning("Template validation.complement_requested indisponible (%s), fallback", e)
        prefix = f"Bonjour {name}, " if name else "Bonjour, "
        return (
            f"⚠️ {prefix}un complément est requis pour votre dossier MA2E *{dossier_number}*.\n\n"
            f"*Demande :* {request_text}\n\n"
            f"Répondez directement à ce message pour compléter votre dossier.\n"
            f"— Équipe MA2E"
        )
