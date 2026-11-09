"""API anti-doublons (US-36).

Endpoints :
    GET    /api/duplicates/check
        → vérifie en amont un dossier (matricule, CNI, identité)

    GET    /api/duplicates/soft-matches
        → liste des groupes de doublons souples à arbitrer (back-office)
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.tenancy import AuthContext, get_auth_context
from app.models import UserRole
from app.services import duplicate_service

router = APIRouter(prefix="/api/duplicates", tags=["duplicates"])


def _resolve_tenant(ctx: AuthContext) -> UUID:
    if not ctx.tenant_id:
        raise HTTPException(status_code=400, detail="Aucun tenant lié à la session.")
    return ctx.tenant_id


@router.get("/check")
async def check(
    matricule: Optional[str] = Query(default=None, max_length=64),
    numero_cni: Optional[str] = Query(default=None, max_length=64),
    nom: Optional[str] = Query(default=None, max_length=128),
    prenoms: Optional[str] = Query(default=None, max_length=128),
    date_naissance: Optional[str] = Query(default=None, max_length=32),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Vérification anti-doublon AVANT soumission ou validation manuelle.

    Renvoie un agrégat : strict_matches (blocant) + soft_matches (à arbitrer).
    """
    tenant_id = _resolve_tenant(ctx)
    result = await duplicate_service.check_duplicates(
        db,
        tenant_id=tenant_id,
        matricule=matricule,
        numero_cni=numero_cni,
        nom=nom,
        prenoms=prenoms,
        date_naissance=date_naissance,
    )
    return {
        "has_strict": result.has_strict,
        "has_soft": result.has_soft,
        "strict_matches": [asdict(m) for m in result.strict_matches],
        "soft_matches": [asdict(m) for m in result.soft_matches],
    }


@router.get("/soft-matches")
async def soft_matches(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Liste les groupes de dossiers en doublon souple à arbitrer.
    Réservé aux gestionnaires et admins."""
    if ctx.role not in (UserRole.super_admin, UserRole.tenant_admin, UserRole.agent):
        raise HTTPException(status_code=403, detail="Accès refusé.")
    tenant_id = _resolve_tenant(ctx)
    groups = await duplicate_service.list_soft_duplicates_for_arbitration(db, tenant_id)
    return {"groups": groups, "count": len(groups)}
