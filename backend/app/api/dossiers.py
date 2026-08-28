from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.storage import presigned_from_minio_url
from app.core.tenancy import AuthContext, get_auth_context, tenant_filter
from app.models import (
    AuditAction,
    AuditLog,
    Consentement,
    DonneesPro,
    Dossier,
    DossierStatus,
    EndUser,
    PieceFace,
    PieceIdentite,
)
from app.schemas.dossier import (
    ComplementRequest,
    DossierDetail,
    DossierListItem,
    DossierListResponse,
    RejectRequest,
)
from app.services import audit_service, dossier_lock_service, member_number_service, notifications, rbac_service, webhook_service

router = APIRouter(prefix="/api/dossiers", tags=["dossiers"])


@router.get("", response_model=DossierListResponse)
async def list_dossiers(
    status_filter: Optional[str] = Query(None, alias="status"),
    statuses: Optional[str] = Query(
        None,
        description="Liste de statuts séparés par virgules (US-38 : combinable avec status simple)",
    ),
    employeur_code: Optional[str] = Query(None),
    matricule: Optional[str] = Query(None),
    agent_id: Optional[UUID] = Query(
        None, description="Filtre par agent assigné (validated_by) — US-38"
    ),
    min_ocr_score: Optional[float] = Query(None, ge=0.0, le=1.0),
    max_ocr_score: Optional[float] = Query(None, ge=0.0, le=1.0),
    priority_only: bool = Query(False, description="Uniquement les dossiers priority_review"),
    overdue_only: bool = Query(False, description="Uniquement les dossiers > 48h en attente"),
    since: Optional[datetime] = Query(None, description="created_at >= since"),
    until: Optional[datetime] = Query(None, description="created_at <= until"),
    sort: str = Query(
        "oldest_first",
        description="oldest_first (US-17 AC4 défaut) | newest_first | priority | overdue",
    ),
    tenant_id: Optional[UUID] = Query(None),
    # F-11 — `ge=1` empêche `?limit=-1` de renvoyer une 500.
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Liste paginée des dossiers avec filtres avancés combinables (US-38).

    Respecte US-17 AC4 (tri par ancienneté par défaut) et US-17 règle "> 48h prioritaire".
    Le tri "priority" remonte d'abord les `priority_review=True`.
    """
    target_tenant = tenant_filter(ctx, tenant_id)

    # Construction des filtres
    base_filters = [Dossier.tenant_id == target_tenant]

    statuses_list: list = []
    if status_filter:
        statuses_list.append(status_filter)
    if statuses:
        statuses_list.extend([s.strip() for s in statuses.split(",") if s.strip()])
    if statuses_list:
        try:
            base_filters.append(
                Dossier.status.in_([DossierStatus(s) for s in statuses_list])
            )
        except ValueError as e:
            raise HTTPException(status_code=422, detail=f"statut invalide : {e}")

    if employeur_code:
        base_filters.append(Dossier.employeur_code == employeur_code)
    if matricule:
        base_filters.append(func.lower(Dossier.matricule) == matricule.lower())
    if agent_id:
        base_filters.append(Dossier.validated_by == agent_id)
    if priority_only:
        base_filters.append(Dossier.priority_review.is_(True))
    if since:
        base_filters.append(Dossier.created_at >= since)
    if until:
        base_filters.append(Dossier.created_at <= until)

    # > 48h en attente
    overdue_cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
    if overdue_only:
        base_filters.append(
            Dossier.created_at < overdue_cutoff,
        )
        base_filters.append(
            Dossier.status.in_([
                DossierStatus.soumis,
                DossierStatus.en_validation,
                DossierStatus.complement_requis,
            ])
        )

    stmt = (
        select(Dossier, EndUser)
        .join(EndUser, EndUser.id == Dossier.end_user_id)
        .options(selectinload(Dossier.pieces))
        .where(*base_filters)
    )

    # Filtres dépendants des pièces (OCR score)
    if min_ocr_score is not None or max_ocr_score is not None:
        stmt = stmt.join(PieceIdentite, PieceIdentite.dossier_id == Dossier.id)
        if min_ocr_score is not None:
            stmt = stmt.where(PieceIdentite.ocr_confidence >= min_ocr_score)
        if max_ocr_score is not None:
            stmt = stmt.where(PieceIdentite.ocr_confidence <= max_ocr_score)
        stmt = stmt.distinct()

    # Tri
    if sort == "newest_first":
        stmt = stmt.order_by(desc(Dossier.created_at))
    elif sort == "priority":
        # Priorité d'abord, puis du plus ancien au plus récent (US-17)
        stmt = stmt.order_by(desc(Dossier.priority_review), Dossier.created_at.asc())
    elif sort == "overdue":
        stmt = stmt.order_by(Dossier.created_at.asc())
    else:
        # Défaut : oldest_first (US-17 AC4 "du plus ancien au plus récent")
        stmt = stmt.order_by(Dossier.created_at.asc())

    stmt = stmt.limit(limit)
    rows = (await db.execute(stmt)).all()

    now = datetime.now(timezone.utc)
    items: list[DossierListItem] = []
    for d, u in rows:
        age_hours = (now - d.created_at).total_seconds() / 3600 if d.created_at else None
        is_overdue = (
            d.status in (DossierStatus.soumis, DossierStatus.en_validation, DossierStatus.complement_requis)
            and d.created_at < overdue_cutoff
        )
        lock_info = dossier_lock_service.lock_status(d)
        items.append(DossierListItem(
            id=d.id,
            dossier_number=d.dossier_number,
            numero_societaire=d.numero_societaire,
            status=d.status.value,
            matricule=d.matricule,
            employeur_code=d.employeur_code,
            end_user_name=u.name,
            end_user_contact=u.phone or u.telegram_id,
            submitted_at=d.submitted_at,
            created_at=d.created_at,
            updated_at=d.updated_at,
            priority_review=d.priority_review,
            priority_reason=d.priority_reason,
            locked=lock_info.get("locked", False),
            locked_by=d.locked_by if lock_info.get("locked") else None,
            locked_at=d.locked_at if lock_info.get("locked") else None,
            age_hours=round(age_hours, 1) if age_hours is not None else None,
            is_overdue=is_overdue,
        ))

    # Récap synthétique recalculé sur le résultat filtré (US-38 AC3)
    by_status: dict[str, int] = {}
    overdue_count = 0
    priority_count = 0
    for it in items:
        by_status[it.status] = by_status.get(it.status, 0) + 1
        if it.is_overdue:
            overdue_count += 1
        if it.priority_review:
            priority_count += 1

    summary = {
        "total": len(items),
        "by_status": by_status,
        "overdue_count": overdue_count,
        "priority_count": priority_count,
    }

    filters_applied = {
        "status": statuses_list or None,
        "employeur_code": employeur_code,
        "matricule": matricule,
        "agent_id": str(agent_id) if agent_id else None,
        "min_ocr_score": min_ocr_score,
        "max_ocr_score": max_ocr_score,
        "priority_only": priority_only,
        "overdue_only": overdue_only,
        "since": since.isoformat() if since else None,
        "until": until.isoformat() if until else None,
        "sort": sort,
        "limit": limit,
    }

    return DossierListResponse(
        items=items,
        summary=summary,
        filters_applied=filters_applied,
    )


@router.get("/stats")
async def stats(
    tenant_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    target_tenant = tenant_filter(ctx, tenant_id)
    rows = (
        await db.execute(
            select(Dossier.status, func.count(Dossier.id))
            .where(Dossier.tenant_id == target_tenant)
            .group_by(Dossier.status)
        )
    ).all()
    by_status = {s.value: 0 for s in DossierStatus}
    for status, count in rows:
        by_status[status.value] = count
    return {
        "total": sum(by_status.values()),
        "by_status": by_status,
    }


async def _build_dossiers_export_rows(
    db: AsyncSession,
    *,
    tenant_target: UUID,
    status_filter: Optional[str],
    employeur_code: Optional[str],
    since: Optional[datetime],
    until: Optional[datetime],
    limit: int,
) -> list[dict]:
    """Construit les lignes (dict) prêtes pour l'export — partagé CSV/XLSX."""
    stmt = (
        select(Dossier)
        .where(Dossier.tenant_id == tenant_target)
        .options(
            selectinload(Dossier.pieces),
            selectinload(Dossier.donnees_pro),
        )
        .order_by(desc(Dossier.validated_at))
        .limit(limit)
    )
    if status_filter:
        try:
            stmt = stmt.where(Dossier.status == DossierStatus(status_filter))
        except ValueError:
            raise HTTPException(status_code=422, detail=f"status invalide : {status_filter}")
    if employeur_code:
        stmt = stmt.where(Dossier.employeur_code == employeur_code)
    if since:
        stmt = stmt.where(Dossier.validated_at >= since)
    if until:
        stmt = stmt.where(Dossier.validated_at <= until)

    rows = list((await db.execute(stmt)).scalars().all())

    end_user_ids = list({d.end_user_id for d in rows})
    end_users_map: dict = {}
    if end_user_ids:
        eu_rows = (
            await db.execute(select(EndUser).where(EndUser.id.in_(end_user_ids)))
        ).scalars().all()
        end_users_map = {u.id: u for u in eu_rows}

    out: list[dict] = []
    for d in rows:
        ocr = {}
        corrections = {}
        for piece in (d.pieces or []):
            if piece.face == PieceFace.recto:
                ocr = piece.ocr_data or {}
                corrections = piece.user_corrections or {}
                break

        def _val(key):
            return corrections.get(key) or ocr.get(key) or ""

        dp = d.donnees_pro
        eu = end_users_map.get(d.end_user_id)

        out.append({
            "numero_societaire": d.numero_societaire or "",
            "numero_dossier": d.dossier_number,
            "nom": _val("nom"),
            "prenoms": _val("prenoms"),
            "date_naissance": _val("date_naissance"),
            "numero_cni": _val("numero_piece") or _val("numero"),
            "societe_code": d.employeur_code or "",
            "matricule": d.matricule or "",
            "fonction": (dp.fonction if dp else "") or "",
            "anciennete_annees": (dp.anciennete_annees if dp else "") or "",
            "situation_familiale": (dp.situation_familiale if dp else "") or "",
            "nombre_ayants_droit": (dp.nombre_ayants_droit if dp else 0),
            "telephone": (eu.phone if eu else "") or "",
            "email": ((eu.extra or {}).get("email") if eu else "") or "",
            "date_soumission": d.submitted_at.strftime("%d/%m/%Y %H:%M")
                if d.submitted_at else "",
            "date_validation": d.validated_at.strftime("%d/%m/%Y %H:%M")
                if d.validated_at else "",
            "statut": d.status.value,
        })
    return out


@router.get("/export.xlsx")
async def export_dossiers_xlsx(
    status_filter: Optional[str] = Query(default="valide", alias="status"),
    employeur_code: Optional[str] = Query(default=None),
    since: Optional[datetime] = Query(default=None),
    until: Optional[datetime] = Query(default=None),
    tenant_id: Optional[UUID] = Query(default=None),
    limit: int = Query(default=50000, ge=1, le=200000),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Export Excel `.xlsx` des dossiers (US-25). Mise en forme :
    charte MA2E (blanc/gris/accent vert pâle), tout aligné à gauche,
    auto-filtre, ligne d'en-tête figée, première colonne en gras.
    """
    from fastapi.responses import Response
    from app.services.xlsx_export_service import render_dossiers_xlsx

    await rbac_service.require_permission(db, ctx, "reporting", "export")
    target = tenant_filter(ctx, tenant_id)

    rows = await _build_dossiers_export_rows(
        db,
        tenant_target=target,
        status_filter=status_filter,
        employeur_code=employeur_code,
        since=since,
        until=until,
        limit=limit,
    )

    # Résumé filtres pour l'en-tête du fichier
    filters_bits: list[str] = []
    if status_filter:
        filters_bits.append(f"statut={status_filter}")
    if employeur_code:
        filters_bits.append(f"société={employeur_code}")
    if since:
        filters_bits.append(f"depuis={since.strftime('%d/%m/%Y')}")
    if until:
        filters_bits.append(f"jusqu'au={until.strftime('%d/%m/%Y')}")
    filters_summary = ", ".join(filters_bits)

    period_label = (
        "Statut : " + status_filter if status_filter else "Tous statuts"
    )

    xlsx_bytes = render_dossiers_xlsx(
        rows, period_label=period_label, filters_summary=filters_summary
    )

    await audit_service.log(
        db, tenant_id=target, action=AuditAction.data_export,
        resource_type="dossier_export", resource_id="xlsx",
        actor_type="user", actor_id=str(ctx.user_id),
        details={
            "rows_exported": len(rows),
            "filter_status": status_filter,
            "filter_employeur_code": employeur_code,
            "filter_since": since.isoformat() if since else None,
            "filter_until": until.isoformat() if until else None,
            "format": "xlsx",
        },
    )
    await db.commit()

    filename = f"societaires_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return Response(
        content=xlsx_bytes,
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export.csv", deprecated=True)
async def export_dossiers_csv(
    status_filter: Optional[str] = Query(default="valide", alias="status"),
    employeur_code: Optional[str] = Query(default=None),
    since: Optional[datetime] = Query(default=None),
    until: Optional[datetime] = Query(default=None),
    tenant_id: Optional[UUID] = Query(default=None),
    limit: int = Query(default=50000, ge=1, le=200000),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """[Déprécié] Conservé pour compat. Préférer `/export.xlsx`."""
    import csv
    import io
    from fastapi.responses import StreamingResponse

    await rbac_service.require_permission(db, ctx, "reporting", "export")
    target = tenant_filter(ctx, tenant_id)

    rows = await _build_dossiers_export_rows(
        db, tenant_target=target,
        status_filter=status_filter, employeur_code=employeur_code,
        since=since, until=until, limit=limit,
    )

    buf = io.StringIO()
    buf.write("﻿")  # BOM UTF-8
    writer = csv.writer(buf, delimiter=";")
    headers = list(rows[0].keys()) if rows else [
        "numero_societaire", "numero_dossier", "nom", "prenoms",
        "date_naissance", "numero_cni", "societe_code", "matricule",
        "fonction", "anciennete_annees", "situation_familiale",
        "nombre_ayants_droit", "telephone", "email",
        "date_soumission", "date_validation", "statut",
    ]
    writer.writerow(headers)
    for r in rows:
        writer.writerow([r.get(h, "") for h in headers])

    await audit_service.log(
        db, tenant_id=target, action=AuditAction.data_export,
        resource_type="dossier_export", resource_id="csv",
        actor_type="user", actor_id=str(ctx.user_id),
        details={"rows_exported": len(rows), "format": "csv"},
    )
    await db.commit()

    buf.seek(0)
    filename = f"societaires_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{dossier_id}", response_model=DossierDetail)
async def get_dossier(
    dossier_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    stmt = (
        select(Dossier)
        .options(
            selectinload(Dossier.pieces),
            selectinload(Dossier.donnees_pro),
            selectinload(Dossier.consentements),
        )
        .where(Dossier.id == dossier_id)
    )
    dossier = (await db.execute(stmt)).scalar_one_or_none()
    if not dossier:
        raise HTTPException(status_code=404, detail="dossier not found")
    if not ctx.is_super_admin and dossier.tenant_id != ctx.tenant_id:
        raise HTTPException(status_code=403, detail="forbidden")

    # Soft-lock (US-17 AC3) : ouvre le dossier comme "en cours de traitement"
    # par cet agent. Un autre agent verra l'indicateur dans la liste.
    if dossier.status not in (DossierStatus.valide, DossierStatus.rejete):
        await dossier_lock_service.acquire(db, dossier, user_id=ctx.user_id)
        await db.commit()
        # `updated_at` a `onupdate=func.now()` côté serveur — après le commit,
        # SQLAlchemy expire cet attribut car la nouvelle valeur n'est connue
        # qu'en BD. On le rafraîchit explicitement pour éviter un lazy-load
        # (qui crash en contexte async — MissingGreenlet).
        await db.refresh(dossier, attribute_names=["updated_at"])

    end_user = (await db.execute(select(EndUser).where(EndUser.id == dossier.end_user_id))).scalar_one()

    audit_stmt = (
        select(AuditLog)
        .where(
            AuditLog.tenant_id == dossier.tenant_id,
            AuditLog.resource_type == "dossier",
            AuditLog.resource_id == str(dossier.id),
        )
        .order_by(AuditLog.created_at.asc())
    )
    audit_entries = (await db.execute(audit_stmt)).scalars().all()

    await audit_service.log(
        db=db,
        tenant_id=dossier.tenant_id,
        action=AuditAction.piece_viewed,
        resource_type="dossier",
        resource_id=str(dossier.id),
        actor_type="user",
        actor_id=str(ctx.user_id),
    )
    await db.commit()

    pieces = []
    for p in dossier.pieces:
        preview_url = presigned_from_minio_url(p.storage_key)
        pieces.append({
            "id": p.id,
            "piece_type": p.piece_type.value,
            "face": p.face.value,
            "storage_key": preview_url or p.storage_key,
            "ocr_status": p.ocr_status,
            "ocr_data": p.ocr_data,
            "mrz_data": p.mrz_data,
            "ocr_confidence": p.ocr_confidence,
            "user_corrections": p.user_corrections,
            "created_at": p.created_at,
        })

    return DossierDetail(
        id=dossier.id,
        tenant_id=dossier.tenant_id,
        dossier_number=dossier.dossier_number,
        status=dossier.status.value,
        matricule=dossier.matricule,
        employeur_code=dossier.employeur_code,
        rejection_motive=dossier.rejection_motive,
        additional_request=dossier.additional_request,
        submitted_at=dossier.submitted_at,
        validated_at=dossier.validated_at,
        created_at=dossier.created_at,
        updated_at=dossier.updated_at,
        pieces=pieces,
        donnees_pro=dossier.donnees_pro,
        consentements=[
            {
                "id": c.id,
                "gate": c.gate.value,
                "decision": c.decision.value,
                "texte_version": c.texte_version,
                "signature": c.signature[:32] + "…",
                "channel": c.channel,
                "created_at": c.created_at,
            }
            for c in dossier.consentements
        ],
        end_user={
            "id": str(end_user.id),
            "name": end_user.name,
            "phone": end_user.phone,
            "telegram_id": end_user.telegram_id,
        },
        audit_logs=[
            {
                "id": str(a.id),
                "action": a.action.value,
                "actor_type": a.actor_type,
                "actor_id": a.actor_id,
                "details": a.details or {},
                "created_at": a.created_at.isoformat(),
            }
            for a in audit_entries
        ],
    )


@router.post("/{dossier_id}/validate")
async def validate_dossier(
    dossier_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    # RBAC : besoin de permission validation.write
    await rbac_service.require_permission(db, ctx, "validation", "write")

    dossier = (await db.execute(select(Dossier).where(Dossier.id == dossier_id))).scalar_one_or_none()
    if not dossier:
        raise HTTPException(status_code=404, detail="not found")
    if not ctx.is_super_admin and dossier.tenant_id != ctx.tenant_id:
        raise HTTPException(status_code=403, detail="forbidden")

    dossier.status = DossierStatus.valide
    dossier.validated_by = ctx.user_id
    dossier.validated_at = datetime.now(timezone.utc)

    # Allouer le numéro de sociétaire (US-19) — unique, non réutilisable
    if not dossier.numero_societaire:
        dossier.numero_societaire = await member_number_service.allocate(db, dossier.tenant_id)
    await db.flush()

    await audit_service.log(
        db=db, tenant_id=dossier.tenant_id, action=AuditAction.dossier_validated,
        resource_type="dossier", resource_id=str(dossier.id),
        actor_type="user", actor_id=str(ctx.user_id),
        details={"numero_societaire": dossier.numero_societaire},
    )

    # Notification automatique au sociétaire
    tenant = (await db.execute(select(Dossier).where(Dossier.id == dossier_id))).scalar_one()
    from app.models import Tenant as _T
    t = (await db.execute(select(_T).where(_T.id == dossier.tenant_id))).scalar_one()
    end_user = (await db.execute(select(EndUser).where(EndUser.id == dossier.end_user_id))).scalar_one()
    notif_msg = await notifications.msg_dossier_valide(
        db, tenant_id=dossier.tenant_id,
        dossier_number=dossier.dossier_number, name=end_user.name,
        numero_societaire=dossier.numero_societaire,
    )
    notif = await notifications.notify_end_user(
        db, tenant=t, end_user=end_user, text=notif_msg,
        also_send_email=True,
        email_subject=f"[MA2E] Votre dossier {dossier.dossier_number} a été validé",
    )

    # Webhook compta (best-effort, ne bloque jamais la validation)
    await webhook_service.send_event(
        db,
        tenant_id=dossier.tenant_id,
        event_type="dossier_validated",
        resource_type="dossier",
        resource_id=str(dossier.id),
        payload={
            "event": "dossier_validated",
            "dossier_id": str(dossier.id),
            "dossier_number": dossier.dossier_number,
            "numero_societaire": dossier.numero_societaire,
            "matricule": dossier.matricule,
            "employeur_code": dossier.employeur_code,
            "validated_at": dossier.validated_at.isoformat() if dossier.validated_at else None,
            "end_user": {
                "name": end_user.name,
                "phone": end_user.phone,
            },
        },
    )
    await db.commit()
    await dossier_lock_service.release_on_decision(db, dossier)
    await db.commit()
    return {"ok": True, "status": dossier.status.value, "notification": notif}


@router.post("/{dossier_id}/reject")
async def reject_dossier(
    dossier_id: UUID,
    payload: RejectRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    await rbac_service.require_permission(db, ctx, "validation", "write")

    dossier = (await db.execute(select(Dossier).where(Dossier.id == dossier_id))).scalar_one_or_none()
    if not dossier:
        raise HTTPException(status_code=404, detail="not found")
    if not ctx.is_super_admin and dossier.tenant_id != ctx.tenant_id:
        raise HTTPException(status_code=403, detail="forbidden")

    dossier.status = DossierStatus.rejete
    dossier.rejection_motive = payload.motive
    dossier.validated_by = ctx.user_id
    dossier.validated_at = datetime.now(timezone.utc)
    await audit_service.log(
        db=db, tenant_id=dossier.tenant_id, action=AuditAction.dossier_rejected,
        resource_type="dossier", resource_id=str(dossier.id),
        actor_type="user", actor_id=str(ctx.user_id),
        details={"motive": payload.motive},
    )

    from app.models import Tenant as _T
    t = (await db.execute(select(_T).where(_T.id == dossier.tenant_id))).scalar_one()
    end_user = (await db.execute(select(EndUser).where(EndUser.id == dossier.end_user_id))).scalar_one()
    notif_msg = await notifications.msg_dossier_rejete(
        db, tenant_id=dossier.tenant_id,
        dossier_number=dossier.dossier_number, motive=payload.motive, name=end_user.name,
    )
    notif = await notifications.notify_end_user(
        db, tenant=t, end_user=end_user, text=notif_msg,
        also_send_email=True,
        email_subject=f"[MA2E] Décision sur votre dossier {dossier.dossier_number}",
    )

    # Webhook compta (déclenche si politique = decided ou all)
    await webhook_service.send_event(
        db,
        tenant_id=dossier.tenant_id,
        event_type="dossier_rejected",
        resource_type="dossier",
        resource_id=str(dossier.id),
        payload={
            "event": "dossier_rejected",
            "dossier_id": str(dossier.id),
            "dossier_number": dossier.dossier_number,
            "matricule": dossier.matricule,
            "employeur_code": dossier.employeur_code,
            "motive": payload.motive,
        },
    )
    await db.commit()
    await dossier_lock_service.release_on_decision(db, dossier)
    await db.commit()
    return {"ok": True, "status": dossier.status.value, "notification": notif}


@router.post("/{dossier_id}/complement")
async def request_complement(
    dossier_id: UUID,
    payload: ComplementRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    await rbac_service.require_permission(db, ctx, "validation", "write")

    dossier = (await db.execute(select(Dossier).where(Dossier.id == dossier_id))).scalar_one_or_none()
    if not dossier:
        raise HTTPException(status_code=404, detail="not found")
    if not ctx.is_super_admin and dossier.tenant_id != ctx.tenant_id:
        raise HTTPException(status_code=403, detail="forbidden")

    dossier.status = DossierStatus.complement_requis
    dossier.additional_request = payload.request_text
    await audit_service.log(
        db=db, tenant_id=dossier.tenant_id, action=AuditAction.dossier_complement_requested,
        resource_type="dossier", resource_id=str(dossier.id),
        actor_type="user", actor_id=str(ctx.user_id),
        details={"request": payload.request_text},
    )

    from app.models import Tenant as _T
    t = (await db.execute(select(_T).where(_T.id == dossier.tenant_id))).scalar_one()
    end_user = (await db.execute(select(EndUser).where(EndUser.id == dossier.end_user_id))).scalar_one()
    notif_msg = await notifications.msg_complement_requis(
        db, tenant_id=dossier.tenant_id,
        dossier_number=dossier.dossier_number, request_text=payload.request_text, name=end_user.name,
    )
    notif = await notifications.notify_end_user(
        db, tenant=t, end_user=end_user, text=notif_msg,
        also_send_email=True,
        email_subject=f"[MA2E] Complément requis pour votre dossier {dossier.dossier_number}",
    )
    await db.commit()
    await dossier_lock_service.release_on_decision(db, dossier)
    await db.commit()
    return {"ok": True, "status": dossier.status.value, "notification": notif}
