"""API REST des utilisateurs back-office.

Endpoints :
    GET    /api/users
        → liste des users (filtrée selon le rôle de l'appelant)

    GET    /api/users/{id}
        → détail d'un user

    POST   /api/users
        → création (admin uniquement, password initial fixé)

    PATCH  /api/users/{id}
        → mise à jour (name, role, is_active)

    POST   /api/users/{id}/reset-password
        → reset du mot de passe par un admin

    POST   /api/users/me/change-password
        → self-service change password (utilisateur connecté)

Règles d'accès :
- super_admin : voit/édite tous les users
- tenant_admin : voit/édite uniquement les users de son tenant
- agent : ne peut accéder qu'à `me/change-password`
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.tenancy import AuthContext, get_auth_context
from app.models import User, UserRole
from app.schemas.auth import MfaDisableRequest, MfaEnableRequest
from app.schemas.user import (
    PasswordChangeIn,
    PasswordResetIn,
    UserCreateIn,
    UserOut,
    UserUpdateIn,
)
from app.services import mfa_service, user_service

router = APIRouter(prefix="/api/users", tags=["users"])


# ====================================================================== #
# Helpers
# ====================================================================== #
def _require_admin(ctx: AuthContext) -> None:
    if ctx.role not in (UserRole.super_admin, UserRole.tenant_admin):
        raise HTTPException(
            status_code=403,
            detail="Seuls les administrateurs peuvent gérer les utilisateurs.",
        )


async def _load_target_user(
    db: AsyncSession, user_id: UUID, ctx: AuthContext
) -> User:
    """Charge un user et vérifie que le caller a le droit de l'opérer."""
    user = await user_service.get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    # super_admin peut tout
    if ctx.is_super_admin:
        return user

    # tenant_admin : seulement son tenant
    if ctx.role == UserRole.tenant_admin and user.tenant_id == ctx.tenant_id:
        return user

    raise HTTPException(status_code=403, detail="Accès refusé sur cet utilisateur.")


# ====================================================================== #
# Endpoints
# ====================================================================== #
@router.get("", response_model=list[UserOut])
async def list_users(
    include_inactive: bool = Query(default=True),
    tenant_id: Optional[UUID] = Query(default=None, description="Super-admin uniquement"),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    _require_admin(ctx)
    # super_admin peut filtrer par tenant, sinon son tenant uniquement
    effective_tenant = tenant_id if ctx.is_super_admin else ctx.tenant_id
    users = await user_service.list_users(
        db, tenant_id=effective_tenant, include_inactive=include_inactive,
    )
    return [UserOut.model_validate(u) for u in users]


@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    _require_admin(ctx)
    user = await _load_target_user(db, user_id, ctx)
    return UserOut.model_validate(user)


@router.post("", response_model=UserOut, status_code=201)
async def create_user(
    payload: UserCreateIn,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    _require_admin(ctx)

    # Détermine le tenant cible
    if ctx.is_super_admin:
        target_tenant = payload.tenant_id
    else:
        target_tenant = ctx.tenant_id

    # tenant_admin ne peut pas créer de super_admin
    if not ctx.is_super_admin and payload.role == UserRole.super_admin:
        raise HTTPException(
            status_code=403,
            detail="Seul un super-admin peut créer un autre super-admin.",
        )

    try:
        user = await user_service.create_user(
            db,
            email=payload.email,
            name=payload.name,
            role=payload.role,
            password=payload.password,
            auth_method=payload.auth_method,
            tenant_id=target_tenant,
            actor_id=ctx.user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    await db.commit()
    await db.refresh(user)
    return UserOut.model_validate(user)


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: UUID,
    payload: UserUpdateIn,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    _require_admin(ctx)
    user = await _load_target_user(db, user_id, ctx)

    # tenant_admin ne peut pas promouvoir au rang super_admin
    if (
        payload.role == UserRole.super_admin
        and not ctx.is_super_admin
    ):
        raise HTTPException(
            status_code=403,
            detail="Seul un super-admin peut promouvoir un utilisateur au rang super-admin.",
        )

    # Auto-modification : un user ne peut pas se rétrograder/désactiver lui-même
    if user.id == ctx.user_id and (
        payload.is_active is False or payload.role not in (None, user.role)
    ):
        raise HTTPException(
            status_code=400,
            detail="Vous ne pouvez pas modifier votre propre rôle ou vous désactiver.",
        )

    updated = await user_service.update_user(
        db, user,
        name=payload.name, role=payload.role, is_active=payload.is_active,
        actor_id=ctx.user_id,
    )
    await db.commit()
    await db.refresh(updated)
    return UserOut.model_validate(updated)


@router.post("/{user_id}/reset-password", status_code=204)
async def reset_password(
    user_id: UUID,
    payload: PasswordResetIn,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    _require_admin(ctx)
    user = await _load_target_user(db, user_id, ctx)
    await user_service.reset_password(
        db, user, new_password=payload.new_password, actor_id=ctx.user_id,
    )
    await db.commit()


@router.post("/me/change-password", status_code=204)
async def change_my_password(
    payload: PasswordChangeIn,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Self-service : tout user connecté peut changer son propre mot de passe."""
    user = await user_service.get_user(db, ctx.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    try:
        await user_service.change_own_password(
            db, user,
            current_password=payload.current_password,
            new_password=payload.new_password,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.commit()


# ====================================================================== #
# MFA TOTP (self-service)
# ====================================================================== #
@router.get("/me/mfa/status")
async def mfa_status(ctx: AuthContext = Depends(get_auth_context), db: AsyncSession = Depends(get_db)):
    user = await user_service.get_user(db, ctx.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    return {
        "enabled": user.mfa_enabled,
        "enrolled_at": user.mfa_enrolled_at.isoformat() if user.mfa_enrolled_at else None,
    }


@router.post("/me/mfa/setup")
async def mfa_setup(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Génère un nouveau secret + QR code. À appeler avant d'activer MFA."""
    user = await user_service.get_user(db, ctx.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    try:
        setup = await mfa_service.generate_setup(db, user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.commit()
    return setup


@router.post("/me/mfa/enable", status_code=204)
async def mfa_enable(
    payload: MfaEnableRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Active MFA après vérification du premier code TOTP."""
    user = await user_service.get_user(db, ctx.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    try:
        await mfa_service.enable_mfa(db, user, payload.code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.commit()


@router.post("/me/mfa/disable", status_code=204)
async def mfa_disable(
    payload: MfaDisableRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Désactive MFA. L'utilisateur doit fournir un code TOTP valide."""
    user = await user_service.get_user(db, ctx.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    try:
        await mfa_service.disable_mfa(db, user, payload.code, actor_id=ctx.user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.commit()


@router.post("/{user_id}/mfa/disable", status_code=204)
async def admin_mfa_disable(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Désactivation forcée par un admin (ex. user a perdu son authenticator).
    Aucun code requis — l'admin engage sa responsabilité (audité)."""
    _require_admin(ctx)
    target = await _load_target_user(db, user_id, ctx)
    if not target.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA déjà désactivé.")
    try:
        await mfa_service.disable_mfa(db, target, code="", actor_id=ctx.user_id, forced=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.commit()
