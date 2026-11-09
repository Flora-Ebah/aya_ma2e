"""Référentiels fermés — listes de valeurs énumérables pour les parcours IA.

Quand le LLM extrait un parcours depuis un Word, chaque champ texte peut être
soit libre (nom, prénoms, email…), soit lié à un référentiel fermé (civilité,
situation matrimoniale, type de pièce d'identité, catégorie professionnelle…).

Un `ReferenceList` est une liste tenant-scoped de couples `(code, label)` avec
synonymes acceptés. Les listes `is_system=True` sont pré-seedées et protégées
contre la suppression. Les administrateurs peuvent ajouter leurs propres listes
depuis le back-office « Référentiels ».

Format des items (JSONB) :
    [
      {"code": "mlle", "label": "Mlle", "synonyms": ["mademoiselle", "mll"]},
      {"code": "mme",  "label": "Mme",  "synonyms": ["madame"]},
      ...
    ]
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Boolean, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class ReferenceList(Base):
    """Liste fermée de valeurs réutilisable par les parcours."""

    __tablename__ = "reference_lists"
    __table_args__ = (
        UniqueConstraint("tenant_id", "key", name="uq_reference_list_key"),
        Index("ix_reference_lists_tenant", "tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )

    # Clé technique utilisée par le LLM (ex: "civilites", "situations_matrimoniales").
    # snake_case, sans accents.
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    # Libellé humain affiché dans le back-office.
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    # Phrases « déclenchantes » qui aident le post-processeur à matcher ce
    # référentiel face à un label de champ (ex: ["civilité", "titre", "sexe"]).
    aliases: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    # Items de la liste — voir docstring du module pour la structure.
    items: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    # Protection : les listes système (civilités, situations) ne peuvent pas
    # être supprimées depuis l'UI. On peut toujours les éditer.
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Autoriser une saisie libre (« Autre : XXX ») en plus des items.
    allow_other: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
