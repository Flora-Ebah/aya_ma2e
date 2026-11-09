"""API CRUD des employeurs (US-05).

Règles métier :
- Création : nom ET code uniques par tenant (sinon 409)
- Modification : idem
- Désactivation préférée à la suppression (si dossiers rattachés)
- Société désactivée → masquée dans la liste sociétaire côté chatbot
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.tenancy import AuthContext, get_auth_context
from app.models import AuditAction, Dossier, Employeur, UserRole
from app.services import audit_service

router = APIRouter(prefix="/api/employeurs", tags=["employeurs"])


# ====================================================================== #
# Schémas Pydantic
# ====================================================================== #
class EmployeurOut(BaseModel):
    id: UUID
    tenant_id: UUID
    code: str
    name: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class EmployeurCreateIn(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=255)


class EmployeurUpdateIn(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    is_active: Optional[bool] = None


# ====================================================================== #
# Helpers
# ====================================================================== #
def _require_admin(ctx: AuthContext) -> None:
    if ctx.role not in (UserRole.super_admin, UserRole.tenant_admin):
        raise HTTPException(status_code=403, detail="Accès admin requis.")


def _resolve_tenant(ctx: AuthContext) -> UUID:
    if not ctx.tenant_id:
        raise HTTPException(status_code=400, detail="Aucun tenant lié à la session.")
    return ctx.tenant_id


async def _check_code_unique(db: AsyncSession, tenant_id: UUID, code: str, exclude_id: Optional[UUID] = None) -> None:
    stmt = select(Employeur).where(
        Employeur.tenant_id == tenant_id,
        func.lower(Employeur.code) == code.lower(),
    )
    if exclude_id is not None:
        stmt = stmt.where(Employeur.id != exclude_id)
    if (await db.execute(stmt)).first():
        raise HTTPException(
            status_code=409,
            detail=f"Le code « {code} » est déjà utilisé par un autre employeur de ce tenant.",
        )


async def _check_name_unique(db: AsyncSession, tenant_id: UUID, name: str, exclude_id: Optional[UUID] = None) -> None:
    stmt = select(Employeur).where(
        Employeur.tenant_id == tenant_id,
        func.lower(Employeur.name) == name.lower(),
    )
    if exclude_id is not None:
        stmt = stmt.where(Employeur.id != exclude_id)
    if (await db.execute(stmt)).first():
        raise HTTPException(
            status_code=409,
            detail=f"Le nom « {name} » est déjà utilisé par un autre employeur de ce tenant.",
        )


# ====================================================================== #
# Endpoints
# ====================================================================== #
@router.get("", response_model=list[EmployeurOut])
async def list_employeurs(
    include_inactive: bool = True,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Liste tous les employeurs du tenant courant (admin) ou actifs uniquement."""
    _require_admin(ctx)
    tenant_id = _resolve_tenant(ctx)
    stmt = select(Employeur).where(Employeur.tenant_id == tenant_id).order_by(Employeur.name)
    if not include_inactive:
        stmt = stmt.where(Employeur.is_active.is_(True))
    return list((await db.execute(stmt)).scalars().all())


@router.post("", response_model=EmployeurOut, status_code=201)
async def create_employeur(
    payload: EmployeurCreateIn,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    _require_admin(ctx)
    tenant_id = _resolve_tenant(ctx)
    await _check_code_unique(db, tenant_id, payload.code)
    await _check_name_unique(db, tenant_id, payload.name)

    employeur = Employeur(
        tenant_id=tenant_id,
        code=payload.code.strip().upper(),
        name=payload.name.strip(),
        is_active=True,
    )
    db.add(employeur)
    await db.flush()

    await audit_service.log(
        db, tenant_id=tenant_id, action=AuditAction.setting_changed,
        resource_type="employeur", resource_id=str(employeur.id),
        actor_type="user", actor_id=str(ctx.user_id),
        details={"action": "created", "code": employeur.code, "name": employeur.name},
    )
    await db.commit()
    await db.refresh(employeur)
    return employeur


@router.patch("/{employeur_id}", response_model=EmployeurOut)
async def update_employeur(
    employeur_id: UUID,
    payload: EmployeurUpdateIn,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    _require_admin(ctx)
    tenant_id = _resolve_tenant(ctx)
    employeur = (
        await db.execute(
            select(Employeur).where(Employeur.id == employeur_id, Employeur.tenant_id == tenant_id)
        )
    ).scalar_one_or_none()
    if employeur is None:
        raise HTTPException(status_code=404, detail="Employeur introuvable")

    changes: dict[str, dict] = {}
    if payload.name and payload.name != employeur.name:
        await _check_name_unique(db, tenant_id, payload.name, exclude_id=employeur.id)
        changes["name"] = {"from": employeur.name, "to": payload.name}
        employeur.name = payload.name.strip()
    if payload.is_active is not None and payload.is_active != employeur.is_active:
        changes["is_active"] = {"from": employeur.is_active, "to": payload.is_active}
        employeur.is_active = payload.is_active

    if changes:
        await db.flush()
        await audit_service.log(
            db, tenant_id=tenant_id, action=AuditAction.setting_changed,
            resource_type="employeur", resource_id=str(employeur.id),
            actor_type="user", actor_id=str(ctx.user_id),
            details={"action": "updated", "changes": changes},
        )
        await db.commit()
    await db.refresh(employeur)
    return employeur


@router.delete("/{employeur_id}", status_code=204)
async def delete_employeur(
    employeur_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Supprime un employeur. **Refus** si des dossiers le réfèrent
    (règle métier US-05 : désactivation préférée à la suppression)."""
    _require_admin(ctx)
    tenant_id = _resolve_tenant(ctx)
    employeur = (
        await db.execute(
            select(Employeur).where(Employeur.id == employeur_id, Employeur.tenant_id == tenant_id)
        )
    ).scalar_one_or_none()
    if employeur is None:
        raise HTTPException(status_code=404, detail="Employeur introuvable")

    linked = (
        await db.execute(
            select(func.count(Dossier.id)).where(
                Dossier.tenant_id == tenant_id,
                Dossier.employeur_code == employeur.code,
            )
        )
    ).scalar_one()
    if linked > 0:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Cet employeur est rattaché à {linked} dossier(s). "
                f"Préférez la désactivation (PATCH is_active=false) à la suppression."
            ),
        )

    await db.delete(employeur)
    await audit_service.log(
        db, tenant_id=tenant_id, action=AuditAction.setting_changed,
        resource_type="employeur", resource_id=str(employeur.id),
        actor_type="user", actor_id=str(ctx.user_id),
        details={"action": "deleted", "code": employeur.code, "name": employeur.name},
    )
    await db.commit()
