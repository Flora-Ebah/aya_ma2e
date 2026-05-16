import logging
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.conversation import state_machine
from app.core.database import get_db
from app.core.storage import put_object
from app.core.tenancy import get_tenant_channel, resolve_tenant_by_channel
from app.models import Channel, MessageDirection

router = APIRouter(prefix="/webhooks/telegram", tags=["webhooks"])
logger = logging.getLogger(__name__)


@router.post("/{bot_token_suffix}")
async def telegram_webhook(
    bot_token_suffix: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    payload = await request.json()
    msg = payload.get("message") or payload.get("edited_message")
    if not msg:
        return {"ok": True}

    channel_record = await get_tenant_channel(db, "telegram", bot_token_suffix)
    if not channel_record:
        logger.warning("telegram webhook: unknown bot suffix %s", bot_token_suffix)
        return {"ok": True}

    tenant = await resolve_tenant_by_channel(db, "telegram", bot_token_suffix)
    if not tenant:
        return {"ok": True}

    chat_id = str(msg["chat"]["id"])
    from_user = msg.get("from", {})
    user_name = from_user.get("first_name") or from_user.get("username")

    end_user = await state_machine.get_or_create_end_user(
        db, tenant.id, Channel.telegram, chat_id, user_name
    )
    conversation = await state_machine.get_or_create_conversation(
        db, tenant.id, end_user, Channel.telegram
    )

    text = msg.get("text") or msg.get("caption") or ""
    media_url: Optional[str] = None
    has_media = False
    bot_token = channel_record.credentials.get("bot_token")

    if "photo" in msg and bot_token:
        photos = msg["photo"]
        largest = max(photos, key=lambda p: p.get("file_size", 0))
        media_url = await _download_and_store(bot_token, largest["file_id"], tenant.slug)
        has_media = True
    elif "document" in msg and bot_token:
        doc = msg["document"]
        media_url = await _download_and_store(bot_token, doc["file_id"], tenant.slug, doc.get("file_name"))
        has_media = True

    await state_machine.record_message(
        db, tenant.id, conversation, MessageDirection.inbound,
        content=text, media_url=media_url,
        extra={"telegram_message_id": msg.get("message_id")},
    )

    reply = await state_machine.handle_message(
        db=db, tenant=tenant, conversation=conversation, end_user=end_user,
        text=text, has_media=has_media, media_url=media_url,
    )

    if reply.text and bot_token:
        await _send_telegram_message(bot_token, chat_id, reply.text)
        await state_machine.record_message(
            db, tenant.id, conversation, MessageDirection.outbound,
            content=reply.text,
        )

    await db.commit()
    return {"ok": True}


async def _send_telegram_message(bot_token: str, chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    async with httpx.AsyncClient(timeout=15.0) as client:
        await client.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})


async def _download_and_store(bot_token: str, file_id: str, tenant_slug: str, file_name: Optional[str] = None) -> Optional[str]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        info_resp = await client.get(f"https://api.telegram.org/bot{bot_token}/getFile", params={"file_id": file_id})
        info = info_resp.json()
        if not info.get("ok"):
            return None
        file_path = info["result"]["file_path"]
        file_resp = await client.get(f"https://api.telegram.org/file/bot{bot_token}/{file_path}")
        data = file_resp.content
        key = f"telegram/{file_id}/{file_name or file_path.split('/')[-1]}"
        return put_object(tenant_slug, key, data)
