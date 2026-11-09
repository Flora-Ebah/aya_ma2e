"""API CRUD collaborateurs (référentiel ERANOVE).

Endpoints :
    GET    /api/collaborateurs                 → liste paginée + recherche
    GET    /api/collaborateurs/{id}            → détail
    POST   /api/collaborateurs                 → création
    PATCH  /api/collaborateurs/{id}            → mise à jour
    DELETE /api/collaborateurs/{id}            → suppression
    GET    /api/collaborateurs/lookup          → vérification matricule (utilisé par anti-fraude)
"""
from __future__ import annotations

from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.tenancy import AuthContext, get_auth_context
from app.models import Collaborateur, UserRole

router = APIRouter(prefix="/api/collaborateurs", tags=["collaborateurs"])


# ====================================================================== #
# Schémas
# ====================================================================== #
class CollaborateurOut(BaseModel):
    id: UUID
    tenant_id: UUID
    matricule: str
    employeur_code: str
    nom: str
    prenoms: str
    email: Optional[EmailStr] = None
    telephone: Optional[str] = None
    fonction: Optional[str] = None
    date_embauche: Optional[date] = None
    statut: str

    model_config = ConfigDict(from_attributes=True)


class CollaborateurCreateIn(BaseModel):
    matricule: str = Field(min_length=1, max_length=32)
    employeur_code: str = Field(min_length=1, max_length=32)
    nom: str = Field(min_length=1, max_length=255)
    prenoms: str = Field(min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    telephone: Optional[str] = Field(default=None, max_length=32)
    fonction: Optional[str] = Field(default=None, max_length=255)
    date_embauche: Optional[date] = None
    statut: str = Field(default="actif", max_length=32)


class CollaborateurUpdateIn(BaseModel):
    nom: Optional[str] = Field(default=None, min_length=1, max_length=255)
    prenoms: Optional[str] = Field(default=None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    telephone: Optional[str] = Field(default=None, max_length=32)
    fonction: Optional[str] = Field(default=None, max_length=255)
    date_embauche: Optional[date] = None
    statut: Optional[str] = Field(default=None, max_length=32)


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


# ====================================================================== #
# Endpoints
# ====================================================================== #
@router.get("", response_model=list[CollaborateurOut])
async def list_collaborateurs(
    employeur_code: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None, description="Recherche dans matricule, nom, prénoms, email"),
    statut: Optional[str] = Query(default=None),
    limit: int = Query(default=200, ge=1, le=2000),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    _require_admin(ctx)
    tenant_id = _resolve_tenant(ctx)
    stmt = (
        select(Collaborateur)
        .where(Collaborateur.tenant_id == tenant_id)
        .order_by(Collaborateur.nom.asc(), Collaborateur.prenoms.asc())
        .limit(limit)
    )
    if employeur_code:
        stmt = stmt.where(Collaborateur.employeur_code == employeur_code)
    if statut:
        stmt = stmt.where(Collaborateur.statut == statut)
    if search:
        q = f"%{search.lower()}%"
        stmt = stmt.where(or_(
            Collaborateur.matricule.ilike(q),
            Collaborateur.nom.ilike(q),
            Collaborateur.prenoms.ilike(q),
            Collaborateur.email.ilike(q),
        ))
    return list((await db.execute(stmt)).scalars().all())


@router.get("/lookup")
async def lookup(
    employeur_code: str = Query(...),
    matricule: str = Query(...),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Vérifie qu'un matricule existe dans le référentiel.
    Réponse compatible avec referential_service (same shape)."""
    _require_admin(ctx)
    tenant_id = _resolve_tenant(ctx)
    row = (
        await db.execute(
            select(Collaborateur).where(
                Collaborateur.tenant_id == tenant_id,
                Collaborateur.employeur_code == employeur_code.strip().upper(),
                Collaborateur.matricule == matricule.strip(),
            )
        )
    ).scalar_one_or_none()
    if row is None:
        return {
            "found": False,
            "matricule": matricule,
            "employeur": employeur_code,
            "source": "internal",
        }
    return {
        "found": True,
        "matricule": row.matricule,
        "employeur": row.employeur_code,
        "name": f"{row.nom} {row.prenoms}".strip(),
        "fonction": row.fonction,
        "status": row.statut,
        "source": "internal",
    }


@router.get("/{collab_id}", response_model=CollaborateurOut)
async def get_collaborateur(
    collab_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    _require_admin(ctx)
    tenant_id = _resolve_tenant(ctx)
    row = (await db.execute(
        select(Collaborateur).where(
            Collaborateur.id == collab_id,
            Collaborateur.tenant_id == tenant_id,
        )
    )).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Collaborateur introuvable")
    return row


@router.post("", response_model=CollaborateurOut, status_code=201)
async def create_collaborateur(
    payload: CollaborateurCreateIn,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    _require_admin(ctx)
    tenant_id = _resolve_tenant(ctx)
    # Unicité
    existing = (await db.execute(
        select(Collaborateur).where(
            Collaborateur.tenant_id == tenant_id,
            Collaborateur.employeur_code == payload.employeur_code.upper(),
            Collaborateur.matricule == payload.matricule,
        )
    )).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Le matricule {payload.matricule} existe déjà pour {payload.employeur_code}.",
        )
    row = Collaborateur(
        tenant_id=tenant_id,
        matricule=payload.matricule.strip(),
        employeur_code=payload.employeur_code.strip().upper(),
        nom=payload.nom.strip(),
        prenoms=payload.prenoms.strip(),
        email=payload.email,
        telephone=payload.telephone,
        fonction=payload.fonction,
        date_embauche=payload.date_embauche,
        statut=payload.statut,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


@router.patch("/{collab_id}", response_model=CollaborateurOut)
async def update_collaborateur(
    collab_id: UUID,
    payload: CollaborateurUpdateIn,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    _require_admin(ctx)
    tenant_id = _resolve_tenant(ctx)
    row = (await db.execute(
        select(Collaborateur).where(
            Collaborateur.id == collab_id,
            Collaborateur.tenant_id == tenant_id,
        )
    )).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Collaborateur introuvable")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    await db.commit()
    await db.refresh(row)
    return row


@router.delete("/{collab_id}", status_code=204)
async def delete_collaborateur(
    collab_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    _require_admin(ctx)
    tenant_id = _resolve_tenant(ctx)
    row = (await db.execute(
        select(Collaborateur).where(
            Collaborateur.id == collab_id,
            Collaborateur.tenant_id == tenant_id,
        )
    )).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Collaborateur introuvable")
    await db.delete(row)
    await db.commit()
