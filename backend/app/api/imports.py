"""API d'import en masse de référentiels (US-37).

Endpoints :
    GET    /api/imports/template/{target}
        → télécharge un CSV modèle

    POST   /api/imports/{target}     (multipart/form-data avec file=...)
        → importe le fichier ; rapport JSON détaillé en retour

    GET    /api/imports/targets
        → liste des référentiels supportés

Sécurité : admin (super_admin OU tenant_admin) uniquement.
"""
from __future__ import annotations

from dataclasses import asdict
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.tenancy import AuthContext, get_auth_context
from app.models import AuditAction, UserRole
from app.services import audit_service, importer_service

router = APIRouter(prefix="/api/imports", tags=["imports"])


def _require_admin(ctx: AuthContext) -> None:
    if ctx.role not in (UserRole.super_admin, UserRole.tenant_admin):
        raise HTTPException(status_code=403, detail="Accès admin requis.")


def _resolve_tenant(ctx: AuthContext) -> UUID:
    if not ctx.tenant_id:
        raise HTTPException(status_code=400, detail="Aucun tenant lié à la session.")
    return ctx.tenant_id


@router.get("/targets")
async def list_targets(
    ctx: AuthContext = Depends(get_auth_context),
):
    _require_admin(ctx)
    return {"targets": sorted(importer_service.SUPPORTED_TARGETS)}


@router.get("/template/{target}")
async def download_template(
    target: str,
    ctx: AuthContext = Depends(get_auth_context),
):
    """Modèle CSV téléchargeable pour le référentiel demandé."""
    _require_admin(ctx)
    try:
        content = importer_service.template_csv(target)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return StreamingResponse(
        iter([content]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="modele_{target}.csv"'
        },
    )


@router.post("/{target}")
async def import_referential(
    target: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Importe un fichier (CSV/Excel) pour peupler un référentiel.

    Réponse JSON :
        {
            "target": "employeurs",
            "total_lines": 12,
            "accepted": 12,
            "rejected": 0,
            "errors": [],
            "inserted_ids": ["..."]
        }
    """
    _require_admin(ctx)
    tenant_id = _resolve_tenant(ctx)

    raw = await file.read()
    try:
        report = await importer_service.import_referential(
            db,
            tenant_id=tenant_id,
            target=target,
            filename=file.filename or "upload",
            raw_bytes=raw,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if report.accepted > 0:
        await db.commit()

    # Audit (US-37 AC6 : tracé qui, quoi, quand, volume)
    await audit_service.log(
        db,
        tenant_id=tenant_id,
        action=AuditAction.data_export,  # on réutilise l'action existante
        resource_type=f"import:{target}",
        resource_id=file.filename or "",
        actor_type="user",
        actor_id=str(ctx.user_id),
        details={
            "filename": file.filename,
            "total_lines": report.total_lines,
            "accepted": report.accepted,
            "rejected": report.rejected,
        },
    )
    await db.commit()

    return asdict(report)
