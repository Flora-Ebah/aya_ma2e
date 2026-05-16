import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, Index, Text, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class AuditAction(str, enum.Enum):
    consent_given = "consent_given"
    consent_refused = "consent_refused"
    consent_revoked = "consent_revoked"
    dossier_created = "dossier_created"
    dossier_submitted = "dossier_submitted"
    dossier_validated = "dossier_validated"
    dossier_rejected = "dossier_rejected"
    dossier_complement_requested = "dossier_complement_requested"
    piece_uploaded = "piece_uploaded"
    piece_ocr_completed = "piece_ocr_completed"
    piece_viewed = "piece_viewed"
    droits_request = "droits_request"
    data_export = "data_export"
    user_login = "user_login"


class AuditLog(Base):
    """Journal d'audit append-only.

    PRD §10.3 : toute opération sensible (consentement, accès aux pièces,
    validation, exercice de droits, export) génère un événement.
    Stockage append-only au niveau applicatif + hash chaîné (V2 : support WORM).
    """

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_tenant_action", "tenant_id", "action"),
        Index("ix_audit_tenant_created", "tenant_id", "created_at"),
        Index("ix_audit_resource", "resource_type", "resource_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )

    actor_type: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    action: Mapped[AuditAction] = mapped_column(SAEnum(AuditAction, name="audit_action"), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    details: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    previous_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    entry_hash: Mapped[str] = mapped_column(String(128), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
