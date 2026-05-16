"""Web chat endpoint — canal secondaire à WhatsApp.

POST /webhooks/web/{tenant_slug}
Body: {"session_id": "...", "message": "...", "name"?: "...", "media_url"?: "..."}
Response: {"reply": "...", "session_id": "...", "state": "..."}

POST /webhooks/web/upload/{tenant_slug}
Multipart: file + session_id
Response: {"media_url": "...", "filename": "..."}
"""
import logging
import uuid as uuid_lib

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.conversation import state_machine
from app.core.database import get_db
from app.core.storage import put_object
from app.models import Channel, MessageDirection, Tenant

router = APIRouter(prefix="/webhooks/web", tags=["webhooks"])
logger = logging.getLogger(__name__)


class WebChatRequest(BaseModel):
    session_id: str
    message: str = ""
    name: str | None = None
    media_url: str | None = None


class WebChatResponse(BaseModel):
    reply: str
    session_id: str
    state: str


@router.post("/{tenant_slug}", response_model=WebChatResponse)
async def web_chat(
    tenant_slug: str,
    payload: WebChatRequest,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Tenant).where(Tenant.slug == tenant_slug, Tenant.is_active.is_(True))
    tenant = (await db.execute(stmt)).scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="tenant not found")

    end_user = await state_machine.get_or_create_end_user(
        db, tenant.id, Channel.web, payload.session_id, payload.name
    )
    conversation = await state_machine.get_or_create_conversation(
        db, tenant.id, end_user, Channel.web
    )

    logger.info(
        "WEB-IN session=%s end_user=%s conversation=%s state_before=%s message=%r",
        payload.session_id, end_user.id, conversation.id, conversation.state, payload.message,
    )

    await state_machine.record_message(
        db, tenant.id, conversation, MessageDirection.inbound,
        content=payload.message, media_url=payload.media_url,
    )

    reply = await state_machine.handle_message(
        db=db,
        tenant=tenant,
        conversation=conversation,
        end_user=end_user,
        text=payload.message or "",
        has_media=bool(payload.media_url),
        media_url=payload.media_url,
    )

    logger.info(
        "WEB-OUT conversation=%s state_after=%s reply=%r",
        conversation.id, conversation.state, reply.text[:60],
    )

    await state_machine.record_message(
        db, tenant.id, conversation, MessageDirection.outbound, content=reply.text,
    )
    await db.commit()

    logger.info("WEB-COMMIT done state=%s", conversation.state)

    return WebChatResponse(
        reply=reply.text,
        session_id=payload.session_id,
        state=conversation.state,
    )


@router.post("/upload/{tenant_slug}")
async def upload_media(
    tenant_slug: str,
    session_id: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Tenant).where(Tenant.slug == tenant_slug, Tenant.is_active.is_(True))
    tenant = (await db.execute(stmt)).scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="tenant not found")

    if not file.filename:
        raise HTTPException(status_code=400, detail="no file provided")
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="empty file")

    ext = ""
    if "." in file.filename:
        ext = "." + file.filename.rsplit(".", 1)[1].lower()
    key = f"web/{session_id}/{uuid_lib.uuid4()}{ext}"
    storage_url = put_object(
        tenant.slug, key, contents, content_type=file.content_type or "application/octet-stream"
    )

    return {
        "media_url": storage_url,
        "filename": file.filename,
        "size_bytes": len(contents),
        "content_type": file.content_type,
    }
