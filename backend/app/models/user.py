import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, Index, UniqueConstraint, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class UserRole(str, enum.Enum):
    super_admin = "super_admin"
    tenant_admin = "tenant_admin"
    agent = "agent"
    # Rôle lecture-seule : accède en lecture aux dossiers, audit, conversations,
    # référentiels. Aucune action de modification (pas de validation, pas de
    # rejet, pas d'édition de workflow ni de settings). Utile pour auditeurs
    # externes, consultants, observateurs de démo.
    viewer = "viewer"


class AuthMethod(str, enum.Enum):
    """Méthode d'authentification d'un utilisateur back-office.

    - `password` : login email + mot de passe local (POC + tenant admin externes)
    - `ad` : authentification déléguée à l'Active Directory ERANOVE (US-02)
            Aucun mot de passe stocké côté MA2E.
    """
    password = "password"
    ad = "ad"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        Index("ix_users_tenant", "tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True
    )

    email: Mapped[str] = mapped_column(String(255), nullable=False)
    # password_hash est nullable car les comptes AD n'en ont pas
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole, name="user_role"), nullable=False)
    auth_method: Mapped[AuthMethod] = mapped_column(
        SAEnum(AuthMethod, name="auth_method"),
        default=AuthMethod.password,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # MFA TOTP — secret base32 (Google Authenticator / Authy compatibles)
    mfa_secret: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    mfa_enabled: Mapped[bool] = mapped_column(default=False, nullable=False)
    mfa_enrolled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
