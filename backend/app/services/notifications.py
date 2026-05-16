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
) -> dict:
    """Envoie un message au sociétaire sur son canal d'origine.

    Stratégie :
    - Cherche la conversation la plus récente du end_user pour ce tenant
    - Détermine le canal (whatsapp / web)
    - Envoie via le bon canal
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

    return result


async def _send_whatsapp(
    db: AsyncSession, tenant: Tenant, end_user: EndUser, text: str
) -> bool:
    """Envoie un message WhatsApp via Meta Cloud API."""
    if not end_user.phone:
        log.warning("end_user sans phone, impossible d'envoyer WhatsApp")
        return False

    # Récupère le canal WhatsApp du tenant pour avoir token + phone_id
    channel_stmt = select(TenantChannel).where(
        TenantChannel.tenant_id == tenant.id,
        TenantChannel.channel == Channel.whatsapp,
        TenantChannel.is_active == True,  # noqa: E712
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
# Templates de messages MA2E
# ----------------------------------------------------------------------
def msg_dossier_valide(dossier_number: str, name: Optional[str] = None) -> str:
    prefix = f"Bonjour {name}, " if name else "Bonjour, "
    return (
        f"✅ {prefix}votre dossier MA2E *{dossier_number}* vient d'être *validé* !\n\n"
        f"Vous êtes officiellement enregistré comme sociétaire MA2E.\n\n"
        f"Merci de votre confiance.\n— Équipe MA2E"
    )


def msg_dossier_rejete(dossier_number: str, motive: str, name: Optional[str] = None) -> str:
    prefix = f"Bonjour {name}, " if name else "Bonjour, "
    return (
        f"❌ {prefix}votre dossier MA2E *{dossier_number}* n'a pas pu être validé.\n\n"
        f"*Motif :* {motive}\n\n"
        f"Vous pouvez reprendre la conversation pour soumettre un nouveau dossier.\n"
        f"— Équipe MA2E"
    )


def msg_complement_requis(dossier_number: str, request_text: str, name: Optional[str] = None) -> str:
    prefix = f"Bonjour {name}, " if name else "Bonjour, "
    return (
        f"⚠️ {prefix}un complément est requis pour votre dossier MA2E *{dossier_number}*.\n\n"
        f"*Demande :* {request_text}\n\n"
        f"Répondez directement à ce message pour compléter votre dossier.\n"
        f"— Équipe MA2E"
    )
