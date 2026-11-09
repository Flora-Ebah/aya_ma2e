"""Schémas Pydantic pour les settings."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SettingDescriptorOut(BaseModel):
    """Métadonnées d'un setting (déclaré dans le registry).

    Sert au frontend pour construire dynamiquement les formulaires sans avoir
    à connaître les paramètres en dur.
    """
    category: str
    key: str
    value_type: str
    default: Any
    label: str
    description: str = ""
    enum_options: Optional[list[str]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    max_length: Optional[int] = None
    sensitive: bool = False
    group: Optional[str] = None


class SettingValueOut(BaseModel):
    """Valeur courante d'un setting (avec ses métadonnées)."""
    category: str
    key: str
    value: Any
    value_type: str
    version: int = 1
    is_default: bool = False
    updated_at: Optional[datetime] = None
    updated_by: Optional[UUID] = None
    # Métadonnées pour aider le rendu côté front
    label: str
    description: str = ""
    enum_options: Optional[list[str]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    max_length: Optional[int] = None
    sensitive: bool = False
    group: Optional[str] = None


class SettingUpdateIn(BaseModel):
    """Payload pour mettre à jour un setting."""
    value: Any
    change_reason: Optional[str] = Field(
        None, max_length=512, description="Raison du changement (audit log)"
    )


class SettingHistoryEntryOut(BaseModel):
    """Entrée historique d'un setting (rollback)."""
    version: int
    value: Any
    value_type: str
    changed_by: Optional[UUID] = None
    change_reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CategoryValuesOut(BaseModel):
    """Toutes les valeurs d'une catégorie sous forme de liste de SettingValueOut."""
    category: str
    settings: list[SettingValueOut]
