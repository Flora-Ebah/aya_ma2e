"""API REST des rôles métier (US-03 + US-04 multi-rôles).

Endpoints :
    GET    /api/roles                 → liste les rôles métier du tenant
    POST   /api/roles                 → crée un rôle métier
    GET    /api/roles/permissions     → schéma des modules et actions disponibles
    GET    /api/roles/{id}            → détail
    PATCH  /api/roles/{id}            → modifie
    DELETE /api/roles/{id}            → supprime (refus si affecté)
    POST   /api/roles/seed-defaults   → installe les 4 rôles MA2E par défaut

    GET    /api/users/{user_id}/roles → liste les rôles métier d'un user
    POST   /api/users/{user_id}/roles/{role_id} → attribue un rôle métier
    DELETE /api/users/{user_id}/roles/{role_id} → révoque

    GET    /api/me/permissions        → permissions effectives de l'utilisateur courant
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.tenancy import AuthContext, get_auth_context
from app.models import ACTIONS, AuditAction, MODULES, UserRole
from app.services import audit_service, rbac_service

router = APIRouter(tags=["roles"])


# ====================================================================== #
# Schémas Pydantic
# ====================================================================== #
class RoleOut(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    description: Optional[str] = None
    permissions: dict
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class RoleCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    description: Optional[str] = Field(default=None, max_length=512)
    permissions: dict = Field(
        default_factory=dict,
        description="Matrice {module: {action: bool}}. Modules : "
                    f"{list(MODULES)}. Actions : {list(ACTIONS)}.",
    )


class RoleUpdateIn(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=64)
    description: Optional[str] = Field(default=None, max_length=512)
    permissions: Optional[dict] = None
    is_active: Optional[bool] = None


def _require_admin(ctx: AuthContext) -> None:
    if ctx.role not in (UserRole.super_admin, UserRole.tenant_admin):
        raise HTTPException(status_code=403, detail="Accès admin requis.")


def _resolve_tenant(ctx: AuthContext) -> UUID:
    if not ctx.tenant_id:
        raise HTTPException(status_code=400, detail="Aucun tenant lié à la session.")
    return ctx.tenant_id


# ====================================================================== #
# Rôles métier (CRUD)
# ====================================================================== #
@router.get("/api/roles/permissions")
async def permissions_schema(ctx: AuthContext = Depends(get_auth_context)):
    """Retourne la liste des modules et actions disponibles pour le frontend."""
    return {"modules": list(MODULES), "actions": list(ACTIONS)}


@router.get("/api/roles", response_model=list[RoleOut])
async def list_roles(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    _require_admin(ctx)
    tenant_id = _resolve_tenant(ctx)
    return await rbac_service.list_roles(db, tenant_id)


@router.post("/api/roles", response_model=RoleOut, status_code=201)
async def create_role(
    payload: RoleCreateIn,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    _require_admin(ctx)
    tenant_id = _resolve_tenant(ctx)
    try:
        role = await rbac_service.create_role(
            db,
            tenant_id=tenant_id,
            name=payload.name,
            description=payload.description,
            permissions=payload.permissions,
            created_by=ctx.user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    await audit_service.log(
        db, tenant_id=tenant_id, action=AuditAction.user_updated,
        resource_type="custom_role", resource_id=str(role.id),
        actor_type="user", actor_id=str(ctx.user_id),
        details={"action": "role_created", "name": role.name},
    )
    await db.commit()
    await db.refresh(role)
    return role


@router.get("/api/roles/{role_id}", response_model=RoleOut)
async def get_role(
    role_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    _require_admin(ctx)
    tenant_id = _resolve_tenant(ctx)
    role = await rbac_service.get_role(db, role_id)
    if role is None or role.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Rôle introuvable")
    return role


@router.patch("/api/roles/{role_id}", response_model=RoleOut)
async def update_role(
    role_id: UUID,
    payload: RoleUpdateIn,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    _require_admin(ctx)
    tenant_id = _resolve_tenant(ctx)
    role = await rbac_service.get_role(db, role_id)
    if role is None or role.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Rôle introuvable")
    try:
        updated = await rbac_service.update_role(
            db, role,
            name=payload.name, description=payload.description,
            permissions=payload.permissions, is_active=payload.is_active,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    await audit_service.log(
        db, tenant_id=tenant_id, action=AuditAction.user_updated,
        resource_type="custom_role", resource_id=str(role.id),
        actor_type="user", actor_id=str(ctx.user_id),
        details={"action": "role_updated", "name": updated.name},
    )
    await db.commit()
    await db.refresh(updated)
    return updated


@router.delete("/api/roles/{role_id}", status_code=204)
async def delete_role(
    role_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    _require_admin(ctx)
    tenant_id = _resolve_tenant(ctx)
    role = await rbac_service.get_role(db, role_id)
    if role is None or role.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Rôle introuvable")
    try:
        await rbac_service.delete_role(db, role)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    await audit_service.log(
        db, tenant_id=tenant_id, action=AuditAction.user_updated,
        resource_type="custom_role", resource_id=str(role_id),
        actor_type="user", actor_id=str(ctx.user_id),
        details={"action": "role_deleted", "name": role.name},
    )
    await db.commit()


@router.post("/api/roles/seed-defaults")
async def seed_default_roles(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Installe les 4 rôles métier MA2E par défaut (Agent Validateur, Superviseur, Lecteur, IT)."""
    _require_admin(ctx)
    tenant_id = _resolve_tenant(ctx)
    created = await rbac_service.seed_default_roles(db, tenant_id, created_by=ctx.user_id)
    await db.commit()
    return {"created": created}


# ====================================================================== #
# Attribution multi-rôles (US-04)
# ====================================================================== #
@router.get("/api/users/{user_id}/roles", response_model=list[RoleOut])
async def list_user_roles(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    _require_admin(ctx)
    return await rbac_service.list_user_roles(db, user_id)


@router.post("/api/users/{user_id}/roles/{role_id}", status_code=204)
async def assign_role(
    user_id: UUID,
    role_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    _require_admin(ctx)
    tenant_id = _resolve_tenant(ctx)
    role = await rbac_service.get_role(db, role_id)
    if role is None or role.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Rôle introuvable")
    await rbac_service.assign_role(db, user_id=user_id, role_id=role_id, granted_by=ctx.user_id)
    await audit_service.log(
        db, tenant_id=tenant_id, action=AuditAction.user_updated,
        resource_type="user", resource_id=str(user_id),
        actor_type="user", actor_id=str(ctx.user_id),
        details={"action": "role_assigned", "role_id": str(role_id), "role_name": role.name},
    )
    await db.commit()


@router.delete("/api/users/{user_id}/roles/{role_id}", status_code=204)
async def revoke_role(
    user_id: UUID,
    role_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    _require_admin(ctx)
    tenant_id = _resolve_tenant(ctx)
    ok = await rbac_service.revoke_role(db, user_id=user_id, role_id=role_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Cet utilisateur ne porte pas ce rôle")
    await audit_service.log(
        db, tenant_id=tenant_id, action=AuditAction.user_updated,
        resource_type="user", resource_id=str(user_id),
        actor_type="user", actor_id=str(ctx.user_id),
        details={"action": "role_revoked", "role_id": str(role_id)},
    )
    await db.commit()


# ====================================================================== #
# Permissions effectives de l'utilisateur courant
# ====================================================================== #
@router.get("/api/me/permissions")
async def my_permissions(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Retourne le snapshot des permissions effectives de l'utilisateur connecté.

    Le frontend l'utilise pour masquer/afficher les actions selon les droits.
    """
    perms = await rbac_service.effective_permissions(db, ctx)
    return {
        "role_system": ctx.role.value,
        "is_super_admin": ctx.is_super_admin,
        "permissions": perms,
        "modules": list(MODULES),
        "actions": list(ACTIONS),
    }
