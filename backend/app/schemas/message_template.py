"""Schémas Pydantic pour l'API des templates de messages."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class TemplateOut(BaseModel):
    """Représentation d'un template (vue admin)."""
    code: str
    language: str
    label: str
    description: str
    group: str
    channel: str
    subject: Optional[str] = None
    content: str
    required_vars: list[str] = Field(default_factory=list)
    optional_vars: list[str] = Field(default_factory=list)
    max_length: Optional[int] = None
    version: int
    is_default: bool = Field(
        description="True si le contenu correspond au défaut du registry (non personnalisé)"
    )
    updated_at: Optional[datetime] = None
    updated_by: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)


class TemplateUpsertIn(BaseModel):
    """Payload pour PUT /api/templates/{code}."""
    content: str = Field(min_length=1, max_length=8192)
    subject: Optional[str] = Field(default=None, max_length=255)
    channel: Optional[str] = Field(
        default=None,
        description="whatsapp | email | web_chat | sms | any",
    )
    change_reason: Optional[str] = Field(default=None, max_length=512)


class TemplatePreviewIn(BaseModel):
    """Payload pour POST /api/templates/{code}/preview — rendu d'aperçu sans persistance."""
    variables: dict[str, str] = Field(default_factory=dict)
    content: Optional[str] = Field(
        default=None,
        description="Si fourni, prévisualise ce contenu plutôt que celui en BD",
    )


class TemplatePreviewOut(BaseModel):
    subject: Optional[str] = None
    rendered: str
    missing_variables: list[str] = Field(
        default_factory=list,
        description="Variables référencées dans le contenu mais non fournies au rendu",
    )


class TemplateHistoryOut(BaseModel):
    version: int
    subject: Optional[str] = None
    content: str
    changed_by: Optional[UUID] = None
    change_reason: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TemplateGroupOut(BaseModel):
    group: str
    templates: list[TemplateOut]
