"""API OTP email pour les sociétaires (US-22).

Endpoints publics (pas d'auth — c'est utilisé pendant l'onboarding du sociétaire) :

    POST   /api/otp/request   { email, tenant_slug }
    POST   /api/otp/verify    { email, tenant_slug, code }

Rate-limiting et tentatives max sont gérés en interne par otp_service.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import Tenant
from app.services import otp_service

router = APIRouter(prefix="/api/otp", tags=["otp"])


class OtpRequest(BaseModel):
    email: EmailStr
    tenant_slug: str = Field(min_length=1, max_length=64)


class OtpVerifyRequest(BaseModel):
    email: EmailStr
    tenant_slug: str = Field(min_length=1, max_length=64)
    code: str = Field(min_length=6, max_length=6)


async def _resolve_tenant(db: AsyncSession, slug: str) -> Tenant:
    tenant = (
        await db.execute(select(Tenant).where(Tenant.slug == slug))
    ).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant inconnu")
    return tenant


@router.post("/request")
async def request_otp(
    payload: OtpRequest,
    db: AsyncSession = Depends(get_db),
):
    tenant = await _resolve_tenant(db, payload.tenant_slug)
    result = await otp_service.request_otp(
        db, tenant_id=tenant.id, email=payload.email,
    )
    if not result["issued"] and result["rate_limited"]:
        raise HTTPException(status_code=429, detail=result["reason"])
    return result


@router.post("/verify")
async def verify_otp(
    payload: OtpVerifyRequest,
    db: AsyncSession = Depends(get_db),
):
    tenant = await _resolve_tenant(db, payload.tenant_slug)
    result = await otp_service.verify_otp(
        db, tenant_id=tenant.id, email=payload.email, code=payload.code,
    )
    if not result["ok"]:
        # 400 pour code incorrect, 410 pour code expiré
        status_code = 410 if "expiré" in (result["reason"] or "") else 400
        raise HTTPException(status_code=status_code, detail=result)
    return result
