"""Workflow conversationnel dynamique.

Tous les parcours conversationnels sont stockés en BD et édités depuis le
back-office. Plusieurs workflows peuvent être actifs en parallèle (`active = True`)
et coexister (Inscription, Consultation, Modification, Chat libre).

Chaque `WorkflowStep` est identifié par un `code` unique au sein du workflow
et porte :
- un `template_code` (lien vers `message_templates.code`) pour le contenu
- un `type` (message / question / action / decision)
- des transitions (`next_step_code`, `branches`) qui pointent vers les codes
  d'autres steps du même workflow.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy import DateTime, Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class WorkflowStepType(str, enum.Enum):
    """Type d'étape — détermine comment le moteur l'exécute."""

    message = "message"
    """Envoie un template et passe immédiatement à l'étape suivante."""

    question = "question"
    """Envoie un template, attend une réponse, valide, puis transition."""

    action = "action"
    """Appelle une fonction backend (anti-doublon, OCR, référentiel…) et
    transitionne selon le résultat (clé du `branches` JSON)."""

    decision = "decision"
    """Évalue une condition sur le contexte de conversation et branche."""


class Workflow(Base):
    __tablename__ = "workflows"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Un seul workflow actif à la fois (validé en service, pas par contrainte BD
    # pour permettre la création d'un brouillon avant bascule).
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    """Ordre d'affichage des workflows. Détermine aussi l'ordre dans le menu
    welcome (variable {parcours_list}) et la position pour le routage dynamique
    (1, 2, 3…). Modifiable via /api/workflows/reorder."""

    start_step_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    """Code de la première étape — référence à WorkflowStep.code dans ce workflow."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    steps: Mapped[list["WorkflowStep"]] = relationship(
        back_populates="workflow",
        cascade="all, delete-orphan",
        order_by="WorkflowStep.position",
    )


class WorkflowStep(Base):
    __tablename__ = "workflow_steps"
    __table_args__ = (
        UniqueConstraint("workflow_id", "code", name="uq_workflow_step_code"),
        Index("ix_workflow_steps_workflow_position", "workflow_id", "position"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False
    )

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    """Identifiant court de l'étape, ex. 'ask_matricule'. Unique au sein du workflow."""

    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    """Ordre d'affichage dans l'éditeur (par tranches de 10 pour insérer entre)."""

    type: Mapped[WorkflowStepType] = mapped_column(
        SAEnum(WorkflowStepType, name="workflow_step_type"),
        nullable=False,
        default=WorkflowStepType.message,
    )

    label: Mapped[str] = mapped_column(String(255), nullable=False)
    """Titre lisible affiché dans l'éditeur."""

    template_code: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    """Lien vers `message_templates.code`. Optionnel pour les steps de type 'action'."""

    action_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    """Pour type='action' : nom de la fonction backend à invoquer
    (ex. 'verify_matricule', 'anti_doublon', 'ocr_extract')."""

    # Transitions
    next_step_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    """Étape suivante en cas de succès / chemin nominal."""

    branches: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    """Branchements conditionnels :
    - type='question'  : {"on_invalid": "ask_matricule_retry"}
    - type='action'    : {"success": "next_code", "doublon": "show_dup", "invalid": "retry"}
    - type='decision'  : {"yes": "step_yes", "no": "step_no"}
    """

    # Configuration
    validation_rules: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    """Pour type='question' : {"regex": "^[0-9]{6}$", "min_len": 6, ...}"""

    prompt_variables: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    """Variables fixes à injecter dans le template (en plus des SYSTEM_VARIABLES)."""

    meta: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    """Champ libre pour configuration future."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    workflow: Mapped["Workflow"] = relationship(back_populates="steps")
