"""API REST des intégrations externes (référentiel agents, webhook compta, services).

Endpoints :
    GET    /api/integrations/services
        → liste des intégrations avec leur statut (activé, configuré)

    POST   /api/integrations/services/{key}/toggle
        → bascule l'activation d'un service

    GET    /api/integrations/referential/verify
        → vérifie un matricule dans le référentiel configuré (test admin)

    POST   /api/integrations/webhooks/test
        → envoie un événement de test à l'URL webhook configurée

    GET    /api/integrations/webhooks/deliveries
        → historique des envois (status, retry, payload, erreur)

    POST   /api/integrations/webhooks/deliveries/{id}/retry
        → re-tente un envoi en échec
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings as app_settings
from app.core.database import get_db
from app.core.tenancy import AuthContext, get_auth_context
from app.models import UserRole, WebhookDelivery
from app.services import referential_service, settings_service, webhook_service

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


def _require_admin(ctx: AuthContext) -> None:
    if ctx.role not in (UserRole.super_admin, UserRole.tenant_admin):
        raise HTTPException(
            status_code=403,
            detail="Seuls les administrateurs peuvent gérer les intégrations.",
        )


def _resolve_tenant(ctx: AuthContext) -> UUID:
    if not ctx.tenant_id:
        raise HTTPException(status_code=400, detail="Aucun tenant lié à la session.")
    return ctx.tenant_id


# ====================================================================== #
# Services & toggles
# ====================================================================== #
class ServiceStatus(BaseModel):
    key: str
    label: str
    description: str
    category: str  # "ai", "communication", "compliance"
    enabled: bool
    configured: bool
    config_hint: str  # message si non configuré (ex. "MINDEE_API_KEY manquante")


# Définition de chaque intégration exposée à l'UI.
# Chaque entrée dit : quel setting porte son flag, quel critère de
# configuration (lambda → bool), et quel hint montrer si pas configuré.
_INTEGRATIONS: list[dict] = [
    {
        "key": "mindee_ocr",  # clé conservée pour compat — désormais Azure AI Vision
        "setting_key": "mindee_ocr_enabled",
        "label": "OCR Azure AI Vision",
        "description": (
            "Extraction automatique des champs (nom, prénoms, n° pièce, MRZ) "
            "depuis le recto/verso de la CNI via Azure AI Vision (Read API) "
            "puis structuration JSON via Azure OpenAI (gpt-5.4-mini)."
        ),
        "category": "ai",
        "is_configured": lambda: bool(
            app_settings.azure_ai_vision_endpoint
            and app_settings.azure_ai_vision_api_key
            and app_settings.azure_openai_endpoint
            and app_settings.azure_openai_api_key
        ),
        "config_hint": "Variables AZURE_AI_VISION_* + AZURE_OPENAI_* requises.",
    },
    {
        "key": "email_otp",
        "setting_key": "email_otp_enabled",
        "label": "Vérification email par OTP",
        "description": (
            "Envoie un code à 6 chiffres par email au sociétaire pour confirmer "
            "son adresse avant la création du dossier. Code valable 10 min, 3 essais max."
        ),
        "category": "compliance",
        "is_configured": lambda: bool(app_settings.smtp_host and app_settings.smtp_host != "localhost"),
        "config_hint": "Variables SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASSWORD requises.",
    },
    {
        "key": "notifications_end",
        "setting_key": "notifications_end_enabled",
        "label": "Notification fin de parcours",
        "description": (
            "Envoie un récap au sociétaire (WhatsApp + email) avec son numéro "
            "de dossier dès la validation."
        ),
        "category": "communication",
        "is_configured": lambda: True,  # toujours utilisable, fallback log
        "config_hint": "",
    },
]


@router.get("/services", response_model=list[ServiceStatus])
async def list_services(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Retourne le statut de chaque intégration (activée + configurée)."""
    tenant_id = _resolve_tenant(ctx)
    out: list[ServiceStatus] = []
    for spec in _INTEGRATIONS:
        try:
            enabled = bool(
                await settings_service.get_value(db, tenant_id, "services", spec["setting_key"])
            )
        except Exception:
            enabled = True  # défaut si setting absent du registry
        configured = bool(spec["is_configured"]())
        out.append(ServiceStatus(
            key=spec["key"],
            label=spec["label"],
            description=spec["description"],
            category=spec["category"],
            enabled=enabled,
            configured=configured,
            config_hint=spec["config_hint"] if not configured else "",
        ))
    return out


class ToggleRequest(BaseModel):
    enabled: bool


@router.post("/services/{key}/toggle", response_model=ServiceStatus)
async def toggle_service(
    key: str,
    payload: ToggleRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Active ou désactive un service. Réservé aux administrateurs."""
    _require_admin(ctx)
    tenant_id = _resolve_tenant(ctx)
    spec = next((s for s in _INTEGRATIONS if s["key"] == key), None)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"Service inconnu : {key}")

    await settings_service.set_value(
        db, tenant_id, "services", spec["setting_key"], bool(payload.enabled),
        updated_by=ctx.user_id,
        change_reason=f"Toggle UI via /parametres/integrations",
    )
    await db.commit()

    configured = bool(spec["is_configured"]())
    return ServiceStatus(
        key=spec["key"],
        label=spec["label"],
        description=spec["description"],
        category=spec["category"],
        enabled=bool(payload.enabled),
        configured=configured,
        config_hint=spec["config_hint"] if not configured else "",
    )


# ====================================================================== #
# Référentiel
# ====================================================================== #
@router.get("/referential/verify")
async def referential_verify(
    employeur: str = Query(..., min_length=1, max_length=64),
    matricule: str = Query(..., min_length=1, max_length=64),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Test admin : vérifie un couple (employeur, matricule) dans le référentiel."""
    _require_admin(ctx)
    tenant_id = _resolve_tenant(ctx)
    return await referential_service.verify_matricule(
        db, tenant_id, employeur, matricule,
    )


# ====================================================================== #
# Webhooks
# ====================================================================== #
@router.post("/webhooks/test")
async def webhook_test(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Envoie un événement de test à l'URL webhook configurée.
    Permet de valider la configuration sans attendre une vraie validation."""
    _require_admin(ctx)
    tenant_id = _resolve_tenant(ctx)

    delivery = await webhook_service.send_event(
        db,
        tenant_id=tenant_id,
        event_type="test_event",
        resource_type="test",
        resource_id="ping",
        payload={
            "event": "test",
            "message": "Ceci est un événement de test depuis MA2E. Si vous le recevez, votre configuration est OK.",
            "issued_by": str(ctx.user_id),
        },
    )
    await db.commit()

    if delivery is None:
        return {
            "sent": False,
            "reason": "Aucune URL configurée ou événement de test non inclus dans la politique.",
        }
    await db.refresh(delivery)
    return {
        "sent": True,
        "delivery_id": str(delivery.id),
        "status": delivery.status.value,
        "response_status": delivery.response_status,
        "error_message": delivery.error_message,
    }


@router.get("/webhooks/deliveries")
async def webhook_deliveries(
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    _require_admin(ctx)
    tenant_id = _resolve_tenant(ctx)

    stmt = (
        select(WebhookDelivery)
        .where(WebhookDelivery.tenant_id == tenant_id)
        .order_by(WebhookDelivery.created_at.desc())
        .limit(limit)
    )
    rows = list((await db.execute(stmt)).scalars().all())
    return [_serialize(d) for d in rows]


@router.post("/webhooks/deliveries/{delivery_id}/retry")
async def webhook_retry(
    delivery_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    _require_admin(ctx)
    tenant_id = _resolve_tenant(ctx)

    delivery = (
        await db.execute(
            select(WebhookDelivery).where(
                WebhookDelivery.id == delivery_id,
                WebhookDelivery.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if delivery is None:
        raise HTTPException(status_code=404, detail="Delivery introuvable")

    try:
        await webhook_service.retry_delivery(db, delivery)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.commit()
    await db.refresh(delivery)
    return _serialize(delivery)


# ====================================================================== #
# Helpers
# ====================================================================== #
def _serialize(d: WebhookDelivery) -> dict:
    return {
        "id": str(d.id),
        "event_type": d.event_type,
        "resource_type": d.resource_type,
        "resource_id": d.resource_id,
        "target_url": d.target_url,
        "status": d.status.value,
        "response_status": d.response_status,
        "response_body": (d.response_body or "")[:500],
        "error_message": d.error_message,
        "attempts": d.attempts,
        "created_at": d.created_at.isoformat() if d.created_at else None,
        "last_attempt_at": d.last_attempt_at.isoformat() if d.last_attempt_at else None,
    }
