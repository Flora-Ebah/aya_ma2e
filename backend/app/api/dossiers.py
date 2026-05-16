from datetime import datetime, timezone
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
    PieceIdentite,
)
from app.schemas.dossier import (
    ComplementRequest,
    DossierDetail,
    DossierListItem,
    RejectRequest,
)
from app.services import audit_service, notifications

router = APIRouter(prefix="/api/dossiers", tags=["dossiers"])


@router.get("", response_model=list[DossierListItem])
async def list_dossiers(
    status_filter: Optional[str] = Query(None, alias="status"),
    tenant_id: Optional[UUID] = Query(None),
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    target_tenant = tenant_filter(ctx, tenant_id)
    stmt = (
        select(Dossier, EndUser)
        .join(EndUser, EndUser.id == Dossier.end_user_id)
        .where(Dossier.tenant_id == target_tenant)
        .order_by(desc(Dossier.created_at))
        .limit(limit)
    )
    if status_filter:
        stmt = stmt.where(Dossier.status == status_filter)

    rows = (await db.execute(stmt)).all()
    return [
        DossierListItem(
            id=d.id,
            dossier_number=d.dossier_number,
            status=d.status.value,
            matricule=d.matricule,
            employeur_code=d.employeur_code,
            end_user_name=u.name,
            end_user_contact=u.phone or u.telegram_id,
            submitted_at=d.submitted_at,
            created_at=d.created_at,
        )
        for d, u in rows
    ]


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
    dossier = (await db.execute(select(Dossier).where(Dossier.id == dossier_id))).scalar_one_or_none()
    if not dossier:
        raise HTTPException(status_code=404, detail="not found")
    if not ctx.is_super_admin and dossier.tenant_id != ctx.tenant_id:
        raise HTTPException(status_code=403, detail="forbidden")

    dossier.status = DossierStatus.valide
    dossier.validated_by = ctx.user_id
    dossier.validated_at = datetime.now(timezone.utc)
    await audit_service.log(
        db=db, tenant_id=dossier.tenant_id, action=AuditAction.dossier_validated,
        resource_type="dossier", resource_id=str(dossier.id),
        actor_type="user", actor_id=str(ctx.user_id),
    )

    # Notification automatique au sociétaire
    tenant = (await db.execute(select(Dossier).where(Dossier.id == dossier_id))).scalar_one()
    from app.models import Tenant as _T
    t = (await db.execute(select(_T).where(_T.id == dossier.tenant_id))).scalar_one()
    end_user = (await db.execute(select(EndUser).where(EndUser.id == dossier.end_user_id))).scalar_one()
    notif_msg = notifications.msg_dossier_valide(dossier.dossier_number, end_user.name)
    notif = await notifications.notify_end_user(db, tenant=t, end_user=end_user, text=notif_msg)
    await db.commit()
    return {"ok": True, "status": dossier.status.value, "notification": notif}


@router.post("/{dossier_id}/reject")
async def reject_dossier(
    dossier_id: UUID,
    payload: RejectRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
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
    notif_msg = notifications.msg_dossier_rejete(dossier.dossier_number, payload.motive, end_user.name)
    notif = await notifications.notify_end_user(db, tenant=t, end_user=end_user, text=notif_msg)
    await db.commit()
    return {"ok": True, "status": dossier.status.value, "notification": notif}


@router.post("/{dossier_id}/complement")
async def request_complement(
    dossier_id: UUID,
    payload: ComplementRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
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
    notif_msg = notifications.msg_complement_requis(dossier.dossier_number, payload.request_text, end_user.name)
    notif = await notifications.notify_end_user(db, tenant=t, end_user=end_user, text=notif_msg)
    await db.commit()
    return {"ok": True, "status": dossier.status.value, "notification": notif}
