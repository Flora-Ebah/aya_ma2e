import logging
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.conversation import state_machine
from app.core.config import settings
from app.core.database import get_db
from app.core.storage import put_object
from app.core.tenancy import get_tenant_channel, resolve_tenant_by_channel
from app.models import Channel, MessageDirection

router = APIRouter(prefix="/webhooks/whatsapp", tags=["webhooks"])
logger = logging.getLogger(__name__)


@router.get("")
async def whatsapp_verify(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
):
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(hub_challenge)
    raise HTTPException(status_code=403, detail="invalid verify token")


@router.post("")
async def whatsapp_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.json()
    try:
        entry = payload["entry"][0]
        change = entry["changes"][0]
        value = change["value"]
        phone_number_id = value["metadata"]["phone_number_id"]
    except (KeyError, IndexError):
        return {"ok": True}

    messages = value.get("messages")
    if not messages:
        return {"ok": True}

    msg = messages[0]
    from_phone = msg["from"]

    channel_record = await get_tenant_channel(db, "whatsapp", phone_number_id)
    if not channel_record:
        logger.warning("whatsapp: unknown phone_number_id %s", phone_number_id)
        return {"ok": True}

    tenant = await resolve_tenant_by_channel(db, "whatsapp", phone_number_id)
    if not tenant:
        return {"ok": True}

    contacts = value.get("contacts", [])
    name = contacts[0]["profile"]["name"] if contacts else None

    end_user = await state_machine.get_or_create_end_user(
        db, tenant.id, Channel.whatsapp, from_phone, name
    )
    conversation = await state_machine.get_or_create_conversation(
        db, tenant.id, end_user, Channel.whatsapp
    )

    text = ""
    media_url: Optional[str] = None
    has_media = False
    access_token = channel_record.credentials.get("access_token")

    msg_type = msg.get("type")
    if msg_type == "text":
        text = msg["text"]["body"]
    elif msg_type == "interactive":
        interactive = msg["interactive"]
        if interactive.get("type") == "button_reply":
            text = interactive["button_reply"]["id"]
        elif interactive.get("type") == "list_reply":
            text = interactive["list_reply"]["id"]
    elif msg_type in {"image", "document", "audio", "video"} and access_token:
        media = msg[msg_type]
        media_id = media["id"]
        media_url = await _download_whatsapp_media(access_token, media_id, tenant.slug, media.get("filename"))
        has_media = True
        text = msg.get("caption", "")

    await state_machine.record_message(
        db, tenant.id, conversation, MessageDirection.inbound,
        content=text, media_url=media_url,
        extra={"whatsapp_message_id": msg.get("id")},
    )

    reply = await state_machine.handle_message(
        db=db, tenant=tenant, conversation=conversation, end_user=end_user,
        text=text, has_media=has_media, media_url=media_url,
    )

    if reply.text and access_token:
        await _send_whatsapp_message(access_token, phone_number_id, from_phone, reply.text)
        await state_machine.record_message(
            db, tenant.id, conversation, MessageDirection.outbound,
            content=reply.text,
        )

    await db.commit()
    return {"ok": True}


async def _send_whatsapp_message(access_token: str, phone_number_id: str, to: str, text: str) -> None:
    url = f"https://graph.facebook.com/v21.0/{phone_number_id}/messages"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    body = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text[:4096]},
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(url, json=body, headers=headers)
        if resp.status_code >= 400:
            logger.error("whatsapp send failed: %s %s", resp.status_code, resp.text)


async def _download_whatsapp_media(access_token: str, media_id: str, tenant_slug: str, file_name: Optional[str]) -> Optional[str]:
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        meta_resp = await client.get(f"https://graph.facebook.com/v21.0/{media_id}")
        if meta_resp.status_code >= 400:
            return None
        media_url = meta_resp.json().get("url")
        if not media_url:
            return None
        file_resp = await client.get(media_url)
        data = file_resp.content
        ext = (file_name or "").split(".")[-1] if file_name and "." in file_name else "bin"
        key = f"whatsapp/{media_id}.{ext}"
        return put_object(tenant_slug, key, data)
