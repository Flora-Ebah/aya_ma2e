"""Paramètres de plateforme (tenant-scoped) + versioning.

Conception générique : une seule table `tenant_settings` accueille TOUS les
types de paramètres (général, IA, conformité, etc.) — la valeur est typée via
une colonne `value_type` (string, int, bool, json…). La structure des valeurs
JSONB autorise la flexibilité maximale (objets, listes…).

Le versioning est stocké dans `tenant_setting_history` : chaque modification
crée une entrée historique permettant le rollback et l'audit.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, Index, UniqueConstraint, Integer
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class SettingValueType(str, enum.Enum):
    """Types primitifs supportés. La valeur JSONB se conforme au type déclaré."""
    string = "string"
    text = "text"          # texte long (textarea) — ex. system prompt LLM
    integer = "integer"
    boolean = "boolean"
    float_ = "float"
    json = "json"
    enum = "enum"


class TenantSetting(Base):
    """Paramètre courant (dernière version active) — un seul par (tenant, key)."""

    __tablename__ = "tenant_settings"
    __table_args__ = (
        UniqueConstraint("tenant_id", "key", name="uq_tenant_setting_key"),
        Index("ix_tenant_settings_tenant_category", "tenant_id", "category"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )

    # Identification du paramètre — doit matcher un descriptor du SettingsRegistry
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    key: Mapped[str] = mapped_column(String(128), nullable=False)

    # Valeur stockée en JSONB pour supporter tous les types
    # (string -> "x", integer -> 42, json -> {...})
    value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    value_type: Mapped[SettingValueType] = mapped_column(
        SAEnum(SettingValueType, name="setting_value_type"), nullable=False
    )

    # Version courante (incrémentée à chaque update — l'historique est dans
    # tenant_setting_history)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Traçabilité
    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    history: Mapped[list["TenantSettingHistory"]] = relationship(
        back_populates="setting", cascade="all, delete-orphan"
    )


class TenantSettingHistory(Base):
    """Historique de toutes les valeurs prises par un setting (rollback + audit)."""

    __tablename__ = "tenant_setting_history"
    __table_args__ = (
        Index("ix_setting_history_setting_version", "setting_id", "version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    setting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant_settings.id", ondelete="CASCADE"), nullable=False
    )

    version: Mapped[int] = mapped_column(Integer, nullable=False)
    value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    value_type: Mapped[SettingValueType] = mapped_column(
        SAEnum(SettingValueType, name="setting_value_type"), nullable=False
    )

    changed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    change_reason: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    setting: Mapped["TenantSetting"] = relationship(back_populates="history")
