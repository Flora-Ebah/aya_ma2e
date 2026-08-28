"""API REST des statistiques et reporting MA2E.

Endpoints :
    GET    /api/stats/overview         → KPIs principaux (validation, refus, conversion…)
    GET    /api/stats/timeline         → série temporelle créés/validés/refusés
    GET    /api/stats/by-channel       → répartition par canal (WhatsApp / Web)
    GET    /api/stats/rejection-reasons → top motifs de refus
    GET    /api/stats/agents-performance → top gestionnaires (par décisions)
    GET    /api/stats/ocr-quality       → distribution des scores OCR
    GET    /api/stats/conversion-funnel → entonnoir conversation → validation

Tous les endpoints sont tenant-scoped + filtre période (`period_days`).
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.tenancy import AuthContext, get_auth_context
from app.services import rbac_service, stats_service

router = APIRouter(prefix="/api/stats", tags=["stats"])


def _resolve_tenant(ctx: AuthContext, tenant_id_param: Optional[UUID]) -> UUID:
    """Super-admin peut interroger n'importe quel tenant via ?tenant_id=,
    les autres rôles sont forcés sur leur propre tenant."""
    if ctx.is_super_admin and tenant_id_param is not None:
        return tenant_id_param
    if ctx.tenant_id is None:
        raise HTTPException(status_code=400, detail="Aucun tenant lié à la session.")
    return ctx.tenant_id


@router.get("/overview")
async def overview(
    period_days: int = Query(default=30, ge=1, le=365),
    compare_previous: bool = Query(default=True, description="US-26 AC2 : variation période précédente"),
    tenant_id: Optional[UUID] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    target = _resolve_tenant(ctx, tenant_id)
    # US-26 AC3 — récupère les seuils d'alerte configurés (best-effort)
    alert_thresholds = None
    try:
        from app.services import settings_service
        alert_thresholds = await settings_service.get_value(
            db, target, "general", "kpi_alert_thresholds"
        )
    except Exception:
        alert_thresholds = None

    result = await stats_service.get_overview(
        db, target,
        period_days=period_days,
        compare_previous=compare_previous,
        alert_thresholds=alert_thresholds,
    )
    return asdict(result)


@router.get("/overview.pdf")
async def overview_pdf(
    period_days: int = Query(default=30, ge=1, le=365),
    tenant_id: Optional[UUID] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Export PDF du tableau de bord exécutif (US-26 AC4).

    F-02 — la permission `reporting.export` est requise. Un compte en
    lecture seule (viewer) n'a pas ce droit et reçoit 403.
    """
    await rbac_service.require_permission(db, ctx, "reporting", "export")

    from fastapi.responses import StreamingResponse
    from app.services import pdf_report_service

    target = _resolve_tenant(ctx, tenant_id)
    # Récupère les données
    alert_thresholds = None
    try:
        from app.services import settings_service
        alert_thresholds = await settings_service.get_value(
            db, target, "general", "kpi_alert_thresholds"
        )
    except Exception:
        alert_thresholds = None

    overview_data = await stats_service.get_overview(
        db, target, period_days=period_days,
        compare_previous=True, alert_thresholds=alert_thresholds,
    )
    channels = await stats_service.get_by_channel(db, target)
    reasons = await stats_service.get_rejection_reasons(db, target, top_n=5)
    funnel = await stats_service.get_conversion_funnel(db, target, period_days=period_days)

    pdf_bytes = pdf_report_service.render_overview_pdf(
        overview=overview_data,
        channels=channels,
        reasons=reasons,
        funnel=funnel,
        period_days=period_days,
    )

    # Audit (export tracé)
    from app.services import audit_service
    from app.models import AuditAction
    await audit_service.log(
        db, tenant_id=target, action=AuditAction.data_export,
        resource_type="reporting_pdf", resource_id="overview",
        actor_type="user", actor_id=str(ctx.user_id),
        details={"period_days": period_days, "format": "pdf"},
    )
    await db.commit()

    from datetime import datetime as _dt
    filename = f"reporting_ma2e_{_dt.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/timeline")
async def timeline(
    period_days: int = Query(default=30, ge=1, le=365),
    tenant_id: Optional[UUID] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    target = _resolve_tenant(ctx, tenant_id)
    buckets = await stats_service.get_timeline(db, target, period_days=period_days)
    return [asdict(b) for b in buckets]


@router.get("/by-channel")
async def by_channel(
    tenant_id: Optional[UUID] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    target = _resolve_tenant(ctx, tenant_id)
    rows = await stats_service.get_by_channel(db, target)
    return [asdict(r) for r in rows]


@router.get("/rejection-reasons")
async def rejection_reasons(
    top_n: int = Query(default=10, ge=1, le=50),
    tenant_id: Optional[UUID] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    target = _resolve_tenant(ctx, tenant_id)
    rows = await stats_service.get_rejection_reasons(db, target, top_n=top_n)
    return [asdict(r) for r in rows]


@router.get("/agents-performance")
async def agents_performance(
    period_days: int = Query(default=90, ge=1, le=365),
    top_n: int = Query(default=10, ge=1, le=50),
    tenant_id: Optional[UUID] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    target = _resolve_tenant(ctx, tenant_id)
    rows = await stats_service.get_agents_performance(
        db, target, period_days=period_days, top_n=top_n,
    )
    return [asdict(r) for r in rows]


@router.get("/ocr-quality")
async def ocr_quality(
    period_days: int = Query(default=90, ge=1, le=365),
    tenant_id: Optional[UUID] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    target = _resolve_tenant(ctx, tenant_id)
    result = await stats_service.get_ocr_quality(db, target, period_days=period_days)
    return asdict(result)


@router.get("/conversion-funnel")
async def conversion_funnel(
    period_days: int = Query(default=30, ge=1, le=365),
    tenant_id: Optional[UUID] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    target = _resolve_tenant(ctx, tenant_id)
    result = await stats_service.get_conversion_funnel(db, target, period_days=period_days)
    return asdict(result)
