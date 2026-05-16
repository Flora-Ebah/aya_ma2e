"""Service de journalisation immuable (append-only) avec hash chaîné.

PRD §10.3 — Journal d'audit append-only de toutes les opérations sensibles.
"""
import hashlib
import json
from typing import Optional
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditAction, AuditLog


def _hash_entry(tenant_id: UUID, action: str, resource_id: Optional[str], details: dict, previous_hash: Optional[str]) -> str:
    payload = {
        "t": str(tenant_id),
        "a": action,
        "r": resource_id,
        "d": details,
        "p": previous_hash or "",
    }
    raw = json.dumps(payload, sort_keys=True, default=str).encode()
    return hashlib.sha256(raw).hexdigest()


async def log(
    db: AsyncSession,
    tenant_id: UUID,
    action: AuditAction,
    resource_type: str,
    resource_id: Optional[str] = None,
    actor_type: str = "system",
    actor_id: Optional[str] = None,
    details: Optional[dict] = None,
) -> AuditLog:
    stmt = (
        select(AuditLog.entry_hash)
        .where(AuditLog.tenant_id == tenant_id)
        .order_by(desc(AuditLog.created_at))
        .limit(1)
    )
    previous_hash = (await db.execute(stmt)).scalar_one_or_none()

    details = details or {}
    entry_hash = _hash_entry(tenant_id, action.value, resource_id, details, previous_hash)

    entry = AuditLog(
        tenant_id=tenant_id,
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        previous_hash=previous_hash,
        entry_hash=entry_hash,
    )
    db.add(entry)
    await db.flush()
    return entry


async def verify_chain(db: AsyncSession, tenant_id: UUID) -> tuple[bool, Optional[str]]:
    """Vérifie l'intégrité de la chaîne d'audit pour un tenant."""
    stmt = (
        select(AuditLog)
        .where(AuditLog.tenant_id == tenant_id)
        .order_by(AuditLog.created_at.asc())
    )
    entries = (await db.execute(stmt)).scalars().all()

    prev_hash: Optional[str] = None
    for entry in entries:
        expected = _hash_entry(
            entry.tenant_id, entry.action.value, entry.resource_id, entry.details, prev_hash
        )
        if entry.previous_hash != prev_hash:
            return False, f"broken link at {entry.id}"
        if entry.entry_hash != expected:
            return False, f"tampered entry {entry.id}"
        prev_hash = entry.entry_hash

    return True, None
