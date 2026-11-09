"""Helpers transverses du moteur conversationnel.

Regroupe ce qui sert aux webhooks (création EndUser / Conversation, persistance
des messages, type de réponse) et n'a rien à voir avec la logique d'un parcours.

Le moteur de parcours lui-même vit dans `workflow_executor.py` ; ces helpers
sont indépendants et stables peu importe le workflow exécuté.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Channel,
    Conversation,
    EndUser,
    Message,
    MessageDirection,
)


@dataclass
class BotReply:
    """Réponse du moteur conversationnel à délivrer sur le canal."""

    text: str
    ui: Optional[dict] = None
    """Hint UI structuré (rendu riche côté web / boutons WhatsApp).

    Forme :
      {"type": "form",   "fields": [{"name","label","type","options","required","placeholder"}]}
      {"type": "select", "name", "label", "options": [{"code","label"}], "allow_other": bool}
    Ignoré par les canaux qui ne savent pas afficher autre chose que du texte.
    """


async def get_or_create_end_user(
    db: AsyncSession,
    tenant_id: UUID,
    channel: Channel,
    external_id: str,
    name: Optional[str],
) -> EndUser:
    if channel == Channel.whatsapp:
        stmt = select(EndUser).where(
            EndUser.tenant_id == tenant_id, EndUser.phone == external_id,
        )
    else:
        stmt = select(EndUser).where(
            EndUser.tenant_id == tenant_id, EndUser.telegram_id == external_id,
        )
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
    db: AsyncSession,
    tenant_id: UUID,
    end_user: EndUser,
    channel: Channel,
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
