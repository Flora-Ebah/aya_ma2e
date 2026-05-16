import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, Index, Text, UniqueConstraint, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class DossierStatus(str, enum.Enum):
    en_cours = "en_cours"
    soumis = "soumis"
    en_validation = "en_validation"
    valide = "valide"
    rejete = "rejete"
    complement_requis = "complement_requis"


class Dossier(Base):
    """Dossier d'identification d'un sociétaire MA2E."""

    __tablename__ = "dossiers"
    __table_args__ = (
        UniqueConstraint("tenant_id", "dossier_number", name="uq_dossier_number"),
        Index("ix_dossiers_tenant_status", "tenant_id", "status"),
        Index("ix_dossiers_tenant_created", "tenant_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )

    dossier_number: Mapped[str] = mapped_column(String(64), nullable=False)
    end_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("end_users.id", ondelete="CASCADE"), nullable=False
    )
    conversation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True
    )

    status: Mapped[DossierStatus] = mapped_column(
        SAEnum(DossierStatus, name="dossier_status"), default=DossierStatus.en_cours, nullable=False
    )

    matricule: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    employeur_code: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    rejection_motive: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    additional_request: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    validated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    pieces: Mapped[list["PieceIdentite"]] = relationship(
        back_populates="dossier", cascade="all, delete-orphan"
    )
    donnees_pro: Mapped[Optional["DonneesPro"]] = relationship(
        back_populates="dossier", uselist=False, cascade="all, delete-orphan"
    )
    consentements: Mapped[list["Consentement"]] = relationship(
        back_populates="dossier", cascade="all, delete-orphan"
    )


class PieceFace(str, enum.Enum):
    recto = "recto"
    verso = "verso"


class PieceType(str, enum.Enum):
    cni_uemoa = "cni_uemoa"
    carte_consulaire = "carte_consulaire"
    carte_resident = "carte_resident"
    passeport = "passeport"


class PieceIdentite(Base):
    """Pièce d'identité scannée et OCRisée."""

    __tablename__ = "pieces_identite"
    __table_args__ = (Index("ix_pieces_tenant_dossier", "tenant_id", "dossier_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    dossier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dossiers.id", ondelete="CASCADE"), nullable=False
    )

    piece_type: Mapped[PieceType] = mapped_column(SAEnum(PieceType, name="piece_type"), nullable=False)
    face: Mapped[PieceFace] = mapped_column(SAEnum(PieceFace, name="piece_face"), nullable=False)

    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(64), default="image/jpeg", nullable=False)

    ocr_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    ocr_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    mrz_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    ocr_confidence: Mapped[Optional[float]] = mapped_column(nullable=True)

    user_corrections: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    dossier: Mapped["Dossier"] = relationship(back_populates="pieces")


class DonneesPro(Base):
    """Données professionnelles et familiales saisies."""

    __tablename__ = "donnees_pro"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    dossier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dossiers.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    fonction: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    anciennete_annees: Mapped[Optional[int]] = mapped_column(nullable=True)
    situation_familiale: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    nombre_ayants_droit: Mapped[int] = mapped_column(default=0, nullable=False)
    rib: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    extra: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    dossier: Mapped["Dossier"] = relationship(back_populates="donnees_pro")


class Employeur(Base):
    """Liste fermée des sociétés du périmètre MA2E."""

    __tablename__ = "employeurs"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_employeur_code"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
