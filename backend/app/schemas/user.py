"""Schémas Pydantic pour l'API users."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.models.user import AuthMethod, UserRole


class UserOut(BaseModel):
    id: UUID
    tenant_id: Optional[UUID] = None
    email: EmailStr
    name: str
    role: UserRole
    auth_method: AuthMethod
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserCreateIn(BaseModel):
    """Création directe par un admin.

    - Si `auth_method=password` : `password` est OBLIGATOIRE
    - Si `auth_method=ad` : aucun mot de passe demandé (auth déléguée à l'AD ERANOVE)
    """
    email: EmailStr
    name: str = Field(min_length=1, max_length=255)
    role: UserRole
    auth_method: AuthMethod = AuthMethod.password
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)
    tenant_id: Optional[UUID] = Field(
        default=None,
        description="Uniquement pour super_admin créant un user dans un autre tenant. "
                    "Ignoré pour tenant_admin (force son propre tenant).",
    )

    @model_validator(mode="after")
    def _check_password_consistency(self) -> "UserCreateIn":
        if self.auth_method == AuthMethod.password and not self.password:
            raise ValueError(
                "Un mot de passe est requis pour les comptes en authentification locale."
            )
        if self.auth_method == AuthMethod.ad and self.password:
            raise ValueError(
                "Aucun mot de passe ne doit être fourni pour les comptes AD "
                "(authentification déléguée à ERANOVE)."
            )
        return self


class UserUpdateIn(BaseModel):
    """Mise à jour des champs modifiables."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class PasswordResetIn(BaseModel):
    """Reset password par un admin."""
    new_password: str = Field(min_length=8, max_length=128)


class PasswordChangeIn(BaseModel):
    """Changement de mot de passe par l'utilisateur lui-même."""
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)
