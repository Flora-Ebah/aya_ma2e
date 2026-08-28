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

from app.conversation import dispatcher
from app.conversation import utils as conv_utils
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

    end_user = await conv_utils.get_or_create_end_user(
        db, tenant.id, Channel.web, payload.session_id, payload.name
    )
    conversation = await conv_utils.get_or_create_conversation(
        db, tenant.id, end_user, Channel.web
    )

    logger.info(
        "WEB-IN session=%s end_user=%s conversation=%s state_before=%s message=%r",
        payload.session_id, end_user.id, conversation.id, conversation.state, payload.message,
    )

    await conv_utils.record_message(
        db, tenant.id, conversation, MessageDirection.inbound,
        content=payload.message, media_url=payload.media_url,
    )

    reply = await dispatcher.dispatch(
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

    await conv_utils.record_message(
        db, tenant.id, conversation, MessageDirection.outbound, content=reply.text,
    )
    await db.commit()

    logger.info("WEB-COMMIT done state=%s", conversation.state)

    return WebChatResponse(
        reply=reply.text,
        session_id=payload.session_id,
        state=conversation.state,
    )


# F-01 — canal anonyme : le pentest a démontré qu'un attaquant peut
# forger une pièce d'identité malveillante et la pusher via cet endpoint.
# On ferme la surface d'attaque par :
#   - allowlist MIME stricte (image bitmap uniquement, pas de PDF ni SVG)
#   - allowlist extension côté filename (défense en profondeur)
#   - taille max 5 MB (une photo CNI compressée fait 200-800 KB)
#   - rate-limit strict par IP (défini dans app/core/rate_limit.py)
_ALLOWED_UPLOAD_MIME: frozenset[str] = frozenset({
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/heic",
    "image/heif",
    "image/webp",
})
_ALLOWED_UPLOAD_EXT: frozenset[str] = frozenset({
    ".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp",
})
_MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB
_MAX_FILENAME_LEN = 128


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
    if len(file.filename) > _MAX_FILENAME_LEN:
        raise HTTPException(status_code=400, detail="filename too long")

    # F-01 — allowlist MIME (déclarée par le client + extension file)
    mime = (file.content_type or "").lower()
    if mime and mime not in _ALLOWED_UPLOAD_MIME:
        logger.warning(
            "upload rejected: unsupported mime=%r tenant=%s session=%s",
            mime, tenant.slug, session_id,
        )
        raise HTTPException(status_code=415, detail="unsupported media type")

    ext = ""
    if "." in file.filename:
        ext = "." + file.filename.rsplit(".", 1)[1].lower()
    if ext and ext not in _ALLOWED_UPLOAD_EXT:
        raise HTTPException(status_code=415, detail="unsupported file extension")

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="empty file")

    # F-01 — plafond de taille strict
    if len(contents) > _MAX_UPLOAD_BYTES:
        logger.warning(
            "upload rejected: too large %d bytes (max %d) tenant=%s session=%s",
            len(contents), _MAX_UPLOAD_BYTES, tenant.slug, session_id,
        )
        raise HTTPException(status_code=413, detail="file too large (5 MB max)")

    key = f"web/{session_id}/{uuid_lib.uuid4()}{ext}"
    storage_url = put_object(
        tenant.slug, key, contents, content_type=mime or "application/octet-stream"
    )

    return {
        "media_url": storage_url,
        "filename": file.filename,
        "size_bytes": len(contents),
        "content_type": mime or None,
    }
