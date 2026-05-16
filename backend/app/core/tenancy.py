from typing import Optional
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.models import Tenant, TenantChannel, User, UserRole


async def resolve_tenant_by_channel(
    db: AsyncSession,
    channel: str,
    external_id: str,
) -> Optional[Tenant]:
    stmt = (
        select(Tenant)
        .join(TenantChannel, TenantChannel.tenant_id == Tenant.id)
        .where(
            TenantChannel.channel == channel,
            TenantChannel.external_id == external_id,
            TenantChannel.is_active.is_(True),
            Tenant.is_active.is_(True),
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_tenant_channel(
    db: AsyncSession,
    channel: str,
    external_id: str,
) -> Optional[TenantChannel]:
    stmt = select(TenantChannel).where(
        TenantChannel.channel == channel,
        TenantChannel.external_id == external_id,
        TenantChannel.is_active.is_(True),
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


class AuthContext:
    def __init__(self, user_id: UUID, tenant_id: Optional[UUID], role: UserRole):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.role = role

    @property
    def is_super_admin(self) -> bool:
        return self.role == UserRole.super_admin


async def get_auth_context(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> AuthContext:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_token(token)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")

    user_id = UUID(payload["sub"])
    tenant_id = UUID(payload["tenant_id"]) if payload.get("tenant_id") else None
    role = UserRole(payload["role"])

    result = await db.execute(select(User).where(User.id == user_id, User.is_active.is_(True)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user not found")

    return AuthContext(user_id=user_id, tenant_id=tenant_id, role=role)


def tenant_filter(ctx: AuthContext, target_tenant_id: Optional[UUID] = None) -> UUID:
    if ctx.is_super_admin:
        if target_tenant_id is None:
            raise HTTPException(status_code=400, detail="super_admin must specify tenant_id")
        return target_tenant_id
    if ctx.tenant_id is None:
        raise HTTPException(status_code=403, detail="user has no tenant")
    if target_tenant_id is not None and target_tenant_id != ctx.tenant_id:
        raise HTTPException(status_code=403, detail="cross-tenant access forbidden")
    return ctx.tenant_id
