"""RBAC dynamique : rôles métier + permissions par module (US-03, US-04).

Architecture additive — coexiste avec `UserRole` (rôle système) :

- **UserRole** (enum dans `user.py`) : 3 rôles système (super_admin, tenant_admin, agent).
  Détermine les droits techniques minimaux (créer un user, voir le journal d'audit…).

- **CustomRole** (table `custom_roles`) : rôles métier nommés par MA2E
  (« Agent Validateur », « Superviseur », « Lecteur », « IT »). Tenant-scoped.

- **UserCustomRole** (table `user_custom_roles`) : un user peut porter
  plusieurs rôles métier (US-04 AC3 "Un utilisateur peut porter plusieurs rôles").

- **Permission** : chaque CustomRole expose une matrice de permissions
  `{module: {action: bool}}` stockée en JSONB pour souplesse.

Modules supportés (mappés sur les API existantes) :
- `validation` : valider/refuser/complément dossiers
- `reporting` : voir reporting et exports
- `administration` : gérer settings, employeurs, users, templates
- `audit` : voir le journal d'audit + exports CSV
- `conformite` : anonymisation, exports RGPD, ARTCI

Actions standard : `read`, `write`, `delete`, `export`.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, Index, UniqueConstraint, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


# ====================================================================== #
# Modules et actions standard (constantes Python pour validation)
# ====================================================================== #
MODULES = ("validation", "reporting", "administration", "audit", "conformite")
ACTIONS = ("read", "write", "delete", "export")


def empty_permissions() -> dict:
    """Matrice par défaut — tout à False (sécurité par défaut)."""
    return {m: {a: False for a in ACTIONS} for m in MODULES}


class CustomRole(Base):
    """Rôle métier nommé, défini par l'admin du tenant (US-03)."""

    __tablename__ = "custom_roles"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_custom_role_name"),
        Index("ix_custom_roles_tenant", "tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )

    name: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Matrice de permissions : {module: {action: bool}}
    # Exemple : {"validation": {"read": true, "write": true, "delete": false, "export": false}, ...}
    permissions: Mapped[dict] = mapped_column(JSONB, default=empty_permissions, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class UserCustomRole(Base):
    """Association many-to-many : un user peut porter plusieurs rôles métier (US-04)."""

    __tablename__ = "user_custom_roles"
    __table_args__ = (
        UniqueConstraint("user_id", "custom_role_id", name="uq_user_custom_role"),
        Index("ix_user_custom_roles_user", "user_id"),
        Index("ix_user_custom_roles_role", "custom_role_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    custom_role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("custom_roles.id", ondelete="CASCADE"), nullable=False
    )

    granted_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
