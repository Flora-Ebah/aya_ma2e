"""Service dédié aux templates de message des steps de workflow.

Contrairement aux templates "système" (`message_template_service`) qui passent
par le registry strict (codes pré-déclarés, validation des variables
obligatoires, valeurs par défaut), les templates de workflow sont créés à la
volée depuis l'éditeur back-office. Leur `code` est défini par l'utilisateur
(ou auto-dérivé du `step.code`), pas par le registry.

Ce service :
- upsert un MessageTemplate sans passer par le registry (pas de descriptor)
- lit le contenu courant ; retourne `None` si pas encore créé (au lieu de
  lever, comme le ferait `get_content` du service standard)
- mutualise le cache Redis avec le service standard pour rester cohérent
"""
from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache
from app.models.message_template import (
    MessageChannel,
    MessageTemplate,
    MessageTemplateHistory,
)

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 300
DEFAULT_LANGUAGE = "fr"
WORKFLOW_TEMPLATE_PREFIX = "workflow"


def derive_code(step_code: str) -> str:
    """Auto-dérive un code de template à partir du code de step."""
    return f"{WORKFLOW_TEMPLATE_PREFIX}.{step_code}"


def _cache_key(tenant_id: UUID, code: str, language: str) -> str:
    return f"template:{tenant_id}:{code}:{language}"


async def get_content(
    db: AsyncSession,
    tenant_id: UUID,
    code: str,
    language: str = DEFAULT_LANGUAGE,
) -> Optional[str]:
    """Retourne le contenu courant du template, ou `None` si pas créé."""
    stmt = select(MessageTemplate).where(
        MessageTemplate.tenant_id == tenant_id,
        MessageTemplate.code == code,
        MessageTemplate.language == language,
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    return row.content if row else None


async def upsert(
    db: AsyncSession,
    tenant_id: UUID,
    code: str,
    content: str,
    *,
    subject: Optional[str] = None,
    channel: MessageChannel = MessageChannel.any_,
    language: str = DEFAULT_LANGUAGE,
    updated_by: Optional[UUID] = None,
) -> MessageTemplate:
    """Crée ou met à jour un template de workflow.

    Snapshot dans `message_template_history` à chaque modification non
    idempotente. Pas de validation registry (codes définis par l'utilisateur).
    """
    stmt = select(MessageTemplate).where(
        MessageTemplate.tenant_id == tenant_id,
        MessageTemplate.code == code,
        MessageTemplate.language == language,
    )
    row = (await db.execute(stmt)).scalar_one_or_none()

    if row is None:
        row = MessageTemplate(
            tenant_id=tenant_id,
            code=code,
            language=language,
            subject=subject,
            content=content,
            channel=channel,
            version=1,
            is_active=True,
            updated_by=updated_by,
        )
        db.add(row)
        await db.flush()
    else:
        # Idempotence
        if row.content == content and row.subject == subject and row.channel == channel:
            return row

        # Snapshot
        snapshot = MessageTemplateHistory(
            template_id=row.id,
            version=row.version,
            subject=row.subject,
            content=row.content,
            changed_by=row.updated_by,
            change_reason="workflow-step-edit",
        )
        db.add(snapshot)
        row.subject = subject
        row.content = content
        row.channel = channel
        row.version += 1
        row.updated_by = updated_by

    await db.flush()
    # Invalide le cache pour les lectures
    await cache.invalidate(_cache_key(tenant_id, code, language))
    return row
