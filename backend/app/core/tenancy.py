"""Résolution du tenant MA2E.

Historiquement le projet était multi-tenant (MA2E / CIE / SODECI / SMB).
Décision 2026-06-15 : la plateforme ne sert que MA2E. On garde la colonne
`tenant_id` en BD (zéro migration) mais l'UX et les API ne l'exposent plus.
Tout passe par le tenant slug `ma2e` résolu une fois et caché.
"""
from typing import Optional
from uuid import UUID

from fastapi import Cookie, Depends, Header, HTTPException, status

from app.core.config import settings as app_settings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.models import Tenant, TenantChannel, User, UserRole

# ----------------------------------------------------------------------
# Résolution du tenant unique (MA2E)
# ----------------------------------------------------------------------
DEFAULT_TENANT_SLUG = "ma2e"

# Cache process-local pour ne pas refaire la requête à chaque appel.
# Sûr en mono-process ; en multi-worker chaque worker l'initialise au 1er appel.
_default_tenant_id: Optional[UUID] = None


async def get_default_tenant_id(db: AsyncSession) -> UUID:
    """Retourne l'UUID du tenant MA2E (créé par le seeder).

    Lève 500 si la ligne n'existe pas — c'est un bug d'installation, pas
    une condition normale.
    """
    global _default_tenant_id
    if _default_tenant_id is not None:
        return _default_tenant_id
    row = (
        await db.execute(select(Tenant.id).where(Tenant.slug == DEFAULT_TENANT_SLUG))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Tenant '{DEFAULT_TENANT_SLUG}' introuvable en base. "
                "Lancez `python seeds/seed.py` pour initialiser la plateforme."
            ),
        )
    _default_tenant_id = row
    return row


async def resolve_tenant_by_channel(
    db: AsyncSession,
    channel: str,
    external_id: str,
) -> Optional[Tenant]:
    """Conservé pour compat avec les webhooks. En pratique retourne toujours MA2E."""
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
    def __init__(self, user_id: UUID, tenant_id: UUID, role: UserRole):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.role = role

    @property
    def is_super_admin(self) -> bool:
        return self.role == UserRole.super_admin


async def get_auth_context(
    authorization: Optional[str] = Header(None),
    ma2e_token: Optional[str] = Cookie(default=None, alias="ma2e_token"),
    db: AsyncSession = Depends(get_db),
) -> AuthContext:
    # F-07 — le passage du jeton via query string (?token=) est proscrit :
    # les jetons y transitent en clair dans les logs serveur, l'historique
    # navigateur et les Referer. Seuls le cookie httpOnly et l'en-tête
    # Authorization: Bearer sont acceptés.
    #
    # Ordre de priorité (du plus sûr au plus permissif) :
    #   1) Cookie httpOnly — mode nominal (Phase 2)
    #   2) Header Authorization: Bearer — compat clients existants
    # Les téléchargements <a href> reposent désormais sur `credentials: "include"`
    # qui envoie automatiquement le cookie httpOnly.
    token: Optional[str] = None
    if ma2e_token:
        token = ma2e_token
    elif authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
    try:
        payload = decode_token(token)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")

    user_id = UUID(payload["sub"])
    role = UserRole(payload["role"])

    result = await db.execute(select(User).where(User.id == user_id, User.is_active.is_(True)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user not found")

    # Le tenant_id du JWT peut être absent (anciens tokens, super_admin historique).
    # On résout systématiquement vers le tenant MA2E unique.
    tenant_id: UUID
    if payload.get("tenant_id"):
        tenant_id = UUID(payload["tenant_id"])
    elif user.tenant_id:
        tenant_id = user.tenant_id
    else:
        tenant_id = await get_default_tenant_id(db)

    return AuthContext(user_id=user_id, tenant_id=tenant_id, role=role)


def tenant_filter(ctx: AuthContext, target_tenant_id: Optional[UUID] = None) -> UUID:
    """Toujours le tenant MA2E. Le paramètre `target_tenant_id` est ignoré
    (conservé pour compat avec les anciens appels)."""
    return ctx.tenant_id
