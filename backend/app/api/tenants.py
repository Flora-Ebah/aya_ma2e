from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.tenancy import AuthContext, get_auth_context
from app.models import Tenant, TenantChannel, UserRole
from app.schemas.tenant import ChannelCreate, TenantCreate, TenantOut

router = APIRouter(prefix="/api/tenants", tags=["tenants"])


@router.get("", response_model=list[TenantOut])
async def list_tenants(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    if ctx.is_super_admin:
        result = await db.execute(select(Tenant).order_by(Tenant.created_at.desc()))
        return result.scalars().all()
    if not ctx.tenant_id:
        return []
    result = await db.execute(select(Tenant).where(Tenant.id == ctx.tenant_id))
    return result.scalars().all()


@router.post("", response_model=TenantOut, status_code=201)
async def create_tenant(
    payload: TenantCreate,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    if not ctx.is_super_admin:
        raise HTTPException(status_code=403, detail="only super_admin can create tenants")

    existing = (await db.execute(select(Tenant).where(Tenant.slug == payload.slug))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="slug already used")

    tenant = Tenant(
        slug=payload.slug,
        name=payload.name,
        description=payload.description,
        branding=payload.branding,
        menu_config=payload.menu_config,
        llm_config=payload.llm_config,
    )
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return tenant


@router.post("/{tenant_id}/channels", status_code=201)
async def attach_channel(
    tenant_id: UUID,
    payload: ChannelCreate,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    if not ctx.is_super_admin:
        raise HTTPException(status_code=403, detail="only super_admin can attach channels")

    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="tenant not found")

    channel = TenantChannel(
        tenant_id=tenant.id,
        channel=payload.channel,
        external_id=payload.external_id,
        display_name=payload.display_name,
        credentials=payload.credentials,
    )
    db.add(channel)
    await db.commit()
    return {"ok": True, "channel_id": str(channel.id)}
