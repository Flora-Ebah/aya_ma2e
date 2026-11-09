"""Référentiel des collaborateurs ERANOVE éligibles à la mutuelle MA2E.

Un Collaborateur représente un agent du groupe (CIE, SODECI, ERANOVE, etc.)
identifié par son matricule. Il peut, mais n'est pas obligé de, devenir
sociétaire MA2E.

Ce référentiel sert à :
- Pré-vérifier qu'un matricule saisi par un sociétaire est légitime
- Importer en masse depuis un CSV/Excel transmis par le SI RH ERANOVE
- Synchroniser à terme via API REST (US-33 — Phase 3)

Doublons : (tenant_id, employeur_code, matricule) est unique.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, Index, UniqueConstraint, Date
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class Collaborateur(Base):
    """Travailleur du groupe ERANOVE référencé par MA2E."""

    __tablename__ = "collaborateurs"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "employeur_code", "matricule",
            name="uq_collaborateur_matricule",
        ),
        Index("ix_collab_tenant_employeur", "tenant_id", "employeur_code"),
        Index("ix_collab_tenant_matricule", "tenant_id", "matricule"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )

    # Identité administrative
    matricule: Mapped[str] = mapped_column(String(32), nullable=False)
    employeur_code: Mapped[str] = mapped_column(String(32), nullable=False)

    # État civil de base (corrobore la CNI quand le sociétaire s'enrôle)
    nom: Mapped[str] = mapped_column(String(255), nullable=False)
    prenoms: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    telephone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # Données pro
    fonction: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    date_embauche: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    statut: Mapped[str] = mapped_column(
        String(32), default="actif", nullable=False,
        # valeurs courantes : actif | retraite | demission | licencie | inactif
    )

    # Extras (pour absorber les colonnes RH ERANOVE imprévues à l'import)
    extra: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
