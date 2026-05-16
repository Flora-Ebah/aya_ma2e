"""Service de gestion des consentements ARTCI versionnés et signés.

PRD §10.4 — Granularité, traçabilité, révocabilité, versionnement, information.
"""
import hashlib
import hmac
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import (
    AuditAction,
    Consentement,
    ConsentDecision,
    ConsentGate,
    TexteConsentement,
)
from app.services import audit_service


async def get_current_text(db: AsyncSession, tenant_id: UUID, gate: ConsentGate) -> Optional[TexteConsentement]:
    stmt = select(TexteConsentement).where(
        TexteConsentement.tenant_id == tenant_id,
        TexteConsentement.gate == gate,
        TexteConsentement.is_current.is_(True),
    )
    return (await db.execute(stmt)).scalar_one_or_none()


def compute_text_hash(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def sign_consent(payload: dict) -> str:
    """Signature cryptographique du consentement (HMAC-SHA256).

    PRD §10.4 : chaque consentement horodaté + version + signature.
    """
    raw = "|".join(str(payload[k]) for k in sorted(payload.keys())).encode()
    return hmac.new(settings.jwt_secret.encode(), raw, hashlib.sha256).hexdigest()


async def record_consent(
    db: AsyncSession,
    tenant_id: UUID,
    end_user_id: UUID,
    dossier_id: Optional[UUID],
    gate: ConsentGate,
    decision: ConsentDecision,
    channel: str,
    ip_or_phone: Optional[str] = None,
    extra: Optional[dict] = None,
) -> Consentement:
    texte = await get_current_text(db, tenant_id, gate)
    if not texte:
        raise ValueError(f"no current consent text for gate={gate.value} tenant={tenant_id}")

    timestamp = datetime.now(timezone.utc).isoformat()
    signature = sign_consent({
        "tenant": str(tenant_id),
        "user": str(end_user_id),
        "gate": gate.value,
        "decision": decision.value,
        "version": texte.version,
        "hash": texte.content_hash,
        "ts": timestamp,
    })

    consent = Consentement(
        tenant_id=tenant_id,
        end_user_id=end_user_id,
        dossier_id=dossier_id,
        gate=gate,
        decision=decision,
        texte_version=texte.version,
        texte_hash=texte.content_hash,
        signature=signature,
        channel=channel,
        ip_or_phone=ip_or_phone,
        extra=extra or {"signed_at": timestamp},
    )
    db.add(consent)
    await db.flush()

    audit_action = {
        ConsentDecision.accepte: AuditAction.consent_given,
        ConsentDecision.refuse: AuditAction.consent_refused,
        ConsentDecision.revoque: AuditAction.consent_revoked,
    }[decision]

    await audit_service.log(
        db=db,
        tenant_id=tenant_id,
        action=audit_action,
        resource_type="consent",
        resource_id=str(consent.id),
        actor_type="end_user",
        actor_id=str(end_user_id),
        details={
            "gate": gate.value,
            "version": texte.version,
            "channel": channel,
            "dossier_id": str(dossier_id) if dossier_id else None,
        },
    )
    return consent
