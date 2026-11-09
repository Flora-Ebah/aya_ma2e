"""API « Référentiels » — gestion des listes fermées utilisées par les parcours IA.

Permet à l'administrateur de visualiser, créer, modifier et supprimer les
listes de valeurs énumérables (civilités, situations matrimoniales, types de
pièce, catégories professionnelles, employeurs, …).

Les listes `is_system=True` sont pré-seedées au boot. Elles sont éditables
(ajout/retrait d'items) mais pas supprimables.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.tenancy import AuthContext, get_auth_context, get_default_tenant_id
from app.models import UserRole
from app.services import reference_list_service

router = APIRouter(prefix="/api/reference-lists", tags=["reference-lists"])


def _require_admin(ctx: AuthContext) -> None:
    if ctx.role not in (UserRole.super_admin, UserRole.tenant_admin):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Réservé aux administrateurs.")


class ItemIn(BaseModel):
    code: Optional[str] = None
    label: str
    synonyms: List[str] = Field(default_factory=list)


class ReferenceListOut(BaseModel):
    id: UUID
    key: str
    label: str
    description: Optional[str]
    aliases: List[str]
    items: List[Dict[str, Any]]
    is_system: bool
    allow_other: bool
    created_at: str
    updated_at: str


class CreateIn(BaseModel):
    key: str
    label: str
    description: Optional[str] = None
    aliases: List[str] = Field(default_factory=list)
    items: List[ItemIn] = Field(default_factory=list)
    allow_other: bool = False


class UpdateIn(BaseModel):
    label: Optional[str] = None
    description: Optional[str] = None
    aliases: Optional[List[str]] = None
    items: Optional[List[ItemIn]] = None
    allow_other: Optional[bool] = None


def _to_out(rl) -> ReferenceListOut:
    return ReferenceListOut(
        id=rl.id,
        key=rl.key,
        label=rl.label,
        description=rl.description,
        aliases=list(rl.aliases or []),
        items=list(rl.items or []),
        is_system=rl.is_system,
        allow_other=rl.allow_other,
        created_at=rl.created_at.isoformat(),
        updated_at=rl.updated_at.isoformat(),
    )


@router.get("", response_model=List[ReferenceListOut])
async def list_lists(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    _require_admin(ctx)
    tenant_id = await get_default_tenant_id(db)
    # Garantit que les listes système sont présentes même si on a oublié le
    # seed au boot (dev, ancien backup, nouveau tenant…).
    await reference_list_service.seed_system_lists(db, tenant_id)
    rows = await reference_list_service.list_lists(db, tenant_id)
    return [_to_out(r) for r in rows]


@router.post("", response_model=ReferenceListOut, status_code=201)
async def create_list(
    payload: CreateIn,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    _require_admin(ctx)
    tenant_id = await get_default_tenant_id(db)
    rl = await reference_list_service.create_list(
        db,
        tenant_id,
        key=payload.key,
        label=payload.label,
        description=payload.description,
        aliases=payload.aliases,
        items=[it.model_dump() for it in payload.items],
        allow_other=payload.allow_other,
    )
    return _to_out(rl)


@router.patch("/{list_id}", response_model=ReferenceListOut)
async def update_list(
    list_id: UUID,
    payload: UpdateIn,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    _require_admin(ctx)
    tenant_id = await get_default_tenant_id(db)
    rl = await reference_list_service.update_list(
        db,
        tenant_id,
        list_id,
        label=payload.label,
        description=payload.description,
        aliases=payload.aliases,
        items=[it.model_dump() for it in payload.items] if payload.items is not None else None,
        allow_other=payload.allow_other,
    )
    return _to_out(rl)


@router.delete("/{list_id}", status_code=204)
async def delete_list(
    list_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    _require_admin(ctx)
    tenant_id = await get_default_tenant_id(db)
    await reference_list_service.delete_list(db, tenant_id, list_id)
    return Response(status_code=204)
