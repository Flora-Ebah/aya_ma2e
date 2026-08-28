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

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.conversation import dispatcher
from app.conversation import utils as conv_utils
from app.core.config import settings
from app.core.database import get_db
from app.core.storage import put_object
from app.models import Channel, MessageDirection, Tenant

router = APIRouter(prefix="/webhooks/web", tags=["webhooks"])
logger = logging.getLogger(__name__)


def _allowed_origins() -> set[str]:
    """Parse la liste des origines autorisées depuis les settings."""
    raw = settings.web_channel_allowed_origins or ""
    return {o.strip().rstrip("/") for o in raw.split(",") if o.strip()}


def _enforce_origin_control(request: Request) -> None:
    """F-04 (cohérence) — contrôle d'origine pour le canal web anonyme.

    Le pentester a recommandé d'appliquer le même contrôle d'origine à
    TOUS les canaux d'intake, pas seulement WhatsApp. Le canal web est
    ouvert au public (chat widget), donc on ne peut pas exiger une
    signature HMAC comme Meta. À la place, on vérifie l'en-tête
    `Origin` (posé automatiquement par le navigateur sur les POST) et
    le fallback `Referer` contre une allowlist configurée.

    En prod avec allowlist configurée : origine non listée → 403.
    En prod sans allowlist : refuse pour forcer l'ops à configurer.
    En dev sans allowlist : laisse passer avec un warning.
    """
    allowed = _allowed_origins()
    if not allowed:
        if settings.app_env == "production":
            logger.error(
                "WEB_CHANNEL_ALLOWED_ORIGINS absent en production — canal web refusé"
            )
            raise HTTPException(
                status_code=503, detail="web channel origin control not configured"
            )
        logger.warning(
            "WEB_CHANNEL_ALLOWED_ORIGINS absent — contrôle d'origine désactivé (mode dev)"
        )
        return

    origin = (request.headers.get("origin") or "").strip().rstrip("/")
    if not origin:
        # Fallback sur Referer (préfixe uniquement, on ne compare pas le path)
        referer = (request.headers.get("referer") or "").strip()
        if referer:
            # Extrait scheme://host de l'URL
            try:
                from urllib.parse import urlparse
                parsed = urlparse(referer)
                origin = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
            except Exception:
                origin = ""

    if origin not in allowed:
        logger.warning(
            "Web webhook: origine refusée '%s' (from %s)",
            origin, request.client.host if request.client else "?",
        )
        raise HTTPException(status_code=403, detail="origin not allowed")


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
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    # F-04 (cohérence) — contrôle d'origine appliqué à tous les canaux d'intake.
    _enforce_origin_control(request)
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
    request: Request,
    session_id: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    # F-04 (cohérence) — contrôle d'origine appliqué à tous les canaux d'intake.
    _enforce_origin_control(request)
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
