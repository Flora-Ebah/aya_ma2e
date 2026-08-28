"""API audit logs et conversations pour le back-office."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.tenancy import AuthContext, get_auth_context, tenant_filter
from app.services import rbac_service
from app.models import (
    AuditAction,
    AuditLog,
    Conversation,
    EndUser,
    Message,
    MessageDirection,
)

router = APIRouter(prefix="/api/audit", tags=["audit"])


# ----------------------------------------------------------------------
#  Audit logs (système)
# ----------------------------------------------------------------------
class AuditLogOut(BaseModel):
    id: UUID
    action: str
    actor_type: str
    actor_id: Optional[str]
    resource_type: Optional[str]
    resource_id: Optional[str]
    details: dict
    created_at: datetime


@router.get("/logs", response_model=list[AuditLogOut])
async def list_audit_logs(
    tenant_id: Optional[UUID] = Query(None),
    action: Optional[str] = Query(None),
    actor_type: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    target = tenant_filter(ctx, tenant_id)
    stmt = (
        select(AuditLog)
        .where(AuditLog.tenant_id == target)
        .order_by(desc(AuditLog.created_at))
        .limit(limit)
    )
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if actor_type:
        stmt = stmt.where(AuditLog.actor_type == actor_type)
    rows = (await db.execute(stmt)).scalars().all()
    return [
        AuditLogOut(
            id=r.id,
            action=r.action.value,
            actor_type=r.actor_type,
            actor_id=r.actor_id,
            resource_type=r.resource_type,
            resource_id=r.resource_id,
            details=r.details or {},
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.get("/logs/stats")
async def audit_stats(
    tenant_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    target = tenant_filter(ctx, tenant_id)
    rows = (
        await db.execute(
            select(AuditLog.action, func.count(AuditLog.id))
            .where(AuditLog.tenant_id == target)
            .group_by(AuditLog.action)
        )
    ).all()
    return {"total": sum(c for _, c in rows), "by_action": {a.value: c for a, c in rows}}


@router.get("/logs/export.csv")
async def export_audit_csv(
    tenant_id: Optional[UUID] = Query(None),
    action: Optional[str] = Query(None),
    actor_type: Optional[str] = Query(None),
    since: Optional[datetime] = Query(None),
    until: Optional[datetime] = Query(None),
    limit: int = Query(default=50000, ge=1, le=200000),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Export CSV du journal d'audit (US-27 règle métier).

    Encodage UTF-8 avec BOM (compatible Excel). Audité via `data_export`.

    F-02 — la permission `audit.export` est requise. Un compte en lecture
    seule (viewer) n'a pas ce droit et reçoit 403.
    """
    await rbac_service.require_permission(db, ctx, "audit", "export")

    import csv
    import io
    from fastapi.responses import StreamingResponse

    target = tenant_filter(ctx, tenant_id)
    stmt = (
        select(AuditLog)
        .where(AuditLog.tenant_id == target)
        .order_by(desc(AuditLog.created_at))
        .limit(limit)
    )
    if action:
        stmt = stmt.where(AuditLog.action == AuditAction(action))
    if actor_type:
        stmt = stmt.where(AuditLog.actor_type == actor_type)
    if since:
        stmt = stmt.where(AuditLog.created_at >= since)
    if until:
        stmt = stmt.where(AuditLog.created_at <= until)

    rows = list((await db.execute(stmt)).scalars().all())

    buf = io.StringIO()
    buf.write("﻿")  # BOM UTF-8 pour Excel
    writer = csv.writer(buf, delimiter=";")
    writer.writerow([
        "id", "created_at_utc", "actor_type", "actor_id", "ip_address",
        "user_agent", "action", "resource_type", "resource_id",
        "details", "entry_hash", "previous_hash",
    ])
    import json
    for r in rows:
        writer.writerow([
            str(r.id),
            r.created_at.isoformat() if r.created_at else "",
            r.actor_type or "",
            r.actor_id or "",
            r.ip_address or "",
            (r.user_agent or "")[:256],
            r.action.value if r.action else "",
            r.resource_type or "",
            r.resource_id or "",
            json.dumps(r.details, ensure_ascii=False, sort_keys=True),
            r.entry_hash or "",
            r.previous_hash or "",
        ])

    # Audit du téléchargement (US-25 règle pour les exports sensibles)
    from app.services import audit_service
    await audit_service.log(
        db, tenant_id=target, action=AuditAction.data_export,
        resource_type="audit_log_export", resource_id="csv",
        actor_type="user", actor_id=str(ctx.user_id),
        details={
            "rows_exported": len(rows),
            "filter_action": action,
            "filter_actor_type": actor_type,
            "filter_since": since.isoformat() if since else None,
            "filter_until": until.isoformat() if until else None,
        },
    )
    await db.commit()

    buf.seek(0)
    filename = f"audit_logs_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ----------------------------------------------------------------------
#  Conversations (chats WhatsApp / Web)
# ----------------------------------------------------------------------
class ConversationOut(BaseModel):
    id: UUID
    channel: str
    state: str
    end_user_id: UUID
    end_user_name: Optional[str]
    end_user_phone: Optional[str]
    messages_count: int
    last_message_at: Optional[datetime]
    created_at: datetime
    device_info: dict


@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(
    tenant_id: Optional[UUID] = Query(None),
    channel: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    target = tenant_filter(ctx, tenant_id)
    stmt = (
        select(Conversation, EndUser)
        .join(EndUser, EndUser.id == Conversation.end_user_id)
        .where(Conversation.tenant_id == target)
        .order_by(desc(Conversation.last_activity_at))
        .limit(limit)
    )
    if channel:
        stmt = stmt.where(Conversation.channel == channel)
    rows = (await db.execute(stmt)).all()

    out: list[ConversationOut] = []
    for conv, user in rows:
        nb = (
            await db.execute(
                select(func.count(Message.id)).where(Message.conversation_id == conv.id)
            )
        ).scalar() or 0
        last_msg = (
            await db.execute(
                select(Message.created_at)
                .where(Message.conversation_id == conv.id)
                .order_by(desc(Message.created_at))
                .limit(1)
            )
        ).scalar()
        ctx_data = conv.context or {}
        out.append(
            ConversationOut(
                id=conv.id,
                channel=conv.channel.value,
                state=conv.state or "—",
                end_user_id=user.id,
                end_user_name=user.name,
                end_user_phone=user.phone or user.telegram_id,
                messages_count=nb,
                last_message_at=last_msg,
                created_at=conv.created_at,
                device_info={
                    "user_agent": ctx_data.get("user_agent"),
                    "ip": ctx_data.get("ip"),
                    "lang": ctx_data.get("lang"),
                    "session_id": ctx_data.get("session_id"),
                },
            )
        )
    return out


class MessageOut(BaseModel):
    id: UUID
    direction: str
    content: Optional[str]
    media_url: Optional[str]
    extra: dict
    created_at: datetime


class ConversationDetailOut(BaseModel):
    id: UUID
    channel: str
    state: str
    end_user: dict
    context: dict
    messages: list[MessageOut]
    created_at: datetime
    updated_at: datetime


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailOut)
async def get_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    conv = (
        await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    ).scalar_one_or_none()
    if not conv:
        raise HTTPException(404, "conversation not found")
    if not ctx.is_super_admin and conv.tenant_id != ctx.tenant_id:
        raise HTTPException(403, "forbidden")

    user = (
        await db.execute(select(EndUser).where(EndUser.id == conv.end_user_id))
    ).scalar_one()
    msgs = (
        await db.execute(
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.created_at.asc())
        )
    ).scalars().all()
    return ConversationDetailOut(
        id=conv.id,
        channel=conv.channel.value,
        state=conv.state or "—",
        end_user={
            "id": str(user.id),
            "name": user.name,
            "phone": user.phone,
            "telegram_id": user.telegram_id,
        },
        context=conv.context or {},
        messages=[
            MessageOut(
                id=m.id,
                direction=m.direction.value,
                content=m.content,
                media_url=m.media_url,
                extra=m.extra or {},
                created_at=m.created_at,
            )
            for m in msgs
        ],
        created_at=conv.created_at,
        updated_at=conv.last_activity_at,
    )
