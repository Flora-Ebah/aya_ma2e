import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, Index, Text, UniqueConstraint, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class ConsentGate(str, enum.Enum):
    artci = "artci"
    ocr_validation = "ocr_validation"
    certification_finale = "certification_finale"
    communications = "communications"


class ConsentDecision(str, enum.Enum):
    accepte = "accepte"
    refuse = "refuse"
    revoque = "revoque"


class TexteConsentement(Base):
    """Versionning des textes de consentement affichés au sociétaire.

    Chaque modification du texte crée une nouvelle version.
    Les consentements antérieurs restent rattachés à leur version d'origine,
    conformément à la loi 2013-450 art.16.
    """

    __tablename__ = "textes_consentement"
    __table_args__ = (
        UniqueConstraint("tenant_id", "gate", "version", name="uq_texte_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )

    gate: Mapped[ConsentGate] = mapped_column(SAEnum(ConsentGate, name="consent_gate"), nullable=False)
    version: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    legal_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    is_current: Mapped[bool] = mapped_column(default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Consentement(Base):
    """Trace immuable de chaque décision de consentement / révocation."""

    __tablename__ = "consentements"
    __table_args__ = (
        Index("ix_consentement_dossier", "dossier_id"),
        Index("ix_consentement_tenant_gate", "tenant_id", "gate"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    dossier_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dossiers.id", ondelete="CASCADE"), nullable=True
    )
    end_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("end_users.id", ondelete="CASCADE"), nullable=False
    )

    gate: Mapped[ConsentGate] = mapped_column(SAEnum(ConsentGate, name="consent_gate"), nullable=False)
    decision: Mapped[ConsentDecision] = mapped_column(
        SAEnum(ConsentDecision, name="consent_decision"), nullable=False
    )
    texte_version: Mapped[str] = mapped_column(String(16), nullable=False)
    texte_hash: Mapped[str] = mapped_column(String(128), nullable=False)

    signature: Mapped[str] = mapped_column(String(256), nullable=False)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    ip_or_phone: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    extra: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    dossier: Mapped[Optional["Dossier"]] = relationship(back_populates="consentements")  # noqa: F821


class DemandeDroitsType(str, enum.Enum):
    acces = "acces"
    rectification = "rectification"
    effacement = "effacement"
    opposition = "opposition"
    portabilite = "portabilite"
    limitation = "limitation"


class DemandeDroitsStatus(str, enum.Enum):
    recue = "recue"
    en_cours = "en_cours"
    satisfaite = "satisfaite"
    rejetee = "rejetee"


class DemandeDroits(Base):
    """Demandes d'exercice des droits ARTCI (art.18-22 loi 2013-450)."""

    __tablename__ = "demandes_droits"
    __table_args__ = (Index("ix_demandes_droits_tenant", "tenant_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    end_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("end_users.id", ondelete="CASCADE"), nullable=False
    )

    type: Mapped[DemandeDroitsType] = mapped_column(
        SAEnum(DemandeDroitsType, name="demande_droits_type"), nullable=False
    )
    status: Mapped[DemandeDroitsStatus] = mapped_column(
        SAEnum(DemandeDroitsStatus, name="demande_droits_status"), default=DemandeDroitsStatus.recue, nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
