"""Schémas Pydantic pour les workflows conversationnels."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.workflow import WorkflowStepType


# ----------------------------------------------------------------------
# WorkflowStep
# ----------------------------------------------------------------------
class WorkflowStepBase(BaseModel):
    code: str = Field(..., min_length=2, max_length=64)
    label: str = Field(..., min_length=1, max_length=255)
    type: WorkflowStepType = WorkflowStepType.message
    template_code: Optional[str] = Field(None, max_length=128)
    action_name: Optional[str] = Field(None, max_length=128)
    next_step_code: Optional[str] = Field(None, max_length=64)
    branches: dict = Field(default_factory=dict)
    validation_rules: dict = Field(default_factory=dict)
    prompt_variables: dict = Field(default_factory=dict)
    meta: dict = Field(default_factory=dict)


class WorkflowStepCreate(WorkflowStepBase):
    position: Optional[int] = None
    template_content: Optional[str] = None
    """Contenu du message à upsert dans message_templates. Optionnel."""


class WorkflowStepUpdate(BaseModel):
    code: Optional[str] = Field(None, min_length=2, max_length=64)
    label: Optional[str] = Field(None, min_length=1, max_length=255)
    type: Optional[WorkflowStepType] = None
    template_code: Optional[str] = Field(None, max_length=128)
    action_name: Optional[str] = Field(None, max_length=128)
    next_step_code: Optional[str] = Field(None, max_length=64)
    branches: Optional[dict] = None
    validation_rules: Optional[dict] = None
    prompt_variables: Optional[dict] = None
    meta: Optional[dict] = None
    template_content: Optional[str] = None
    """Si fourni, upsert le contenu dans message_templates."""


class WorkflowStepOut(WorkflowStepBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    workflow_id: UUID
    position: int
    created_at: datetime
    updated_at: datetime
    template_content: Optional[str] = None
    """Contenu courant du template lié (None si pas encore créé)."""


class WorkflowStepReorderItem(BaseModel):
    code: str
    position: int


class WorkflowStepReorderRequest(BaseModel):
    items: list[WorkflowStepReorderItem]


# ----------------------------------------------------------------------
# Workflow
# ----------------------------------------------------------------------
class WorkflowBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    start_step_code: Optional[str] = Field(None, max_length=64)


class WorkflowCreate(WorkflowBase):
    pass


class WorkflowUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    start_step_code: Optional[str] = Field(None, max_length=64)


class WorkflowOut(WorkflowBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    active: bool
    version: int
    position: int = 0
    created_at: datetime
    updated_at: datetime


class WorkflowDetailOut(WorkflowOut):
    steps: list[WorkflowStepOut] = Field(default_factory=list)
