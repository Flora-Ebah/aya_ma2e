"""Modèles de messages (templates) tenant-scoped + versioning.

Un MessageTemplate est identifié par un `code` (ex. "onboarding.welcome",
"onboarding.ask_matricule", "validation.dossier_valide"…).
Pour chaque code on peut avoir plusieurs langues (`language` = fr/en).
Le contenu est un texte avec des variables `{prenom}`, `{nom}`, etc.

Le contrôle des variables obligatoires se fait à la sauvegarde via
`MessageTemplateRegistry.validate_template`.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, Index, UniqueConstraint, Integer, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class MessageChannel(str, enum.Enum):
    """Canal de livraison cible — détermine les contraintes (taille, format…)."""
    whatsapp = "whatsapp"
    email = "email"
    web_chat = "web_chat"
    sms = "sms"
    any_ = "any"  # template générique


class MessageTemplate(Base):
    """Template actif courant pour un (tenant, code, language)."""

    __tablename__ = "message_templates"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", "language", name="uq_template_code_lang"),
        Index("ix_templates_tenant_code", "tenant_id", "code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )

    code: Mapped[str] = mapped_column(String(128), nullable=False)
    language: Mapped[str] = mapped_column(String(8), nullable=False, default="fr")

    subject: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    channel: Mapped[MessageChannel] = mapped_column(
        SAEnum(MessageChannel, name="message_channel"),
        nullable=False,
        default=MessageChannel.any_,
    )

    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    history: Mapped[list["MessageTemplateHistory"]] = relationship(
        back_populates="template", cascade="all, delete-orphan"
    )


class MessageTemplateHistory(Base):
    """Historique des versions d'un template (rollback + audit)."""

    __tablename__ = "message_template_history"
    __table_args__ = (
        Index("ix_template_history_template_version", "template_id", "version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("message_templates.id", ondelete="CASCADE"), nullable=False
    )

    version: Mapped[int] = mapped_column(Integer, nullable=False)
    subject: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    changed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    change_reason: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    template: Mapped["MessageTemplate"] = relationship(back_populates="history")
