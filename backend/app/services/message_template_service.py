"""MessageTemplateService — CRUD + cache + rendu des templates de messages.

Garanties :
- Lecture : valeur courante (BD) ou contenu par défaut (registry) si non personnalisé
- Cache Redis (TTL 5 min) sur les lectures
- Écriture : validation des variables via le registry, snapshot dans
  `message_template_history`, invalidation du cache, audit log
- Rendu : substitution `{var}` → valeur ; les variables manquantes restent
  telles quelles (pas d'exception, le LLM/agent doit décider quoi faire)

Pattern d'usage typique (depuis le moteur conversationnel) :

    content = await message_template_service.render(
        db,
        tenant_id=tenant_id,
        code="validation.dossier_valide",
        variables={"prenom": "Awa", "numero_societaire": "MA2E-00042"},
    )
"""
from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache
from app.models import AuditAction
from app.models.message_template import (
    MessageChannel,
    MessageTemplate,
    MessageTemplateHistory,
)
from app.services import audit_service
from app.services.message_template_registry import (
    MessageTemplateDescriptor,
    get_template_descriptor,
    template_registry,
)

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 300
DEFAULT_LANGUAGE = "fr"


def _cache_key(tenant_id: UUID, code: str, language: str) -> str:
    return f"template:{tenant_id}:{code}:{language}"


# ====================================================================== #
# Lecture
# ====================================================================== #
async def get_template(
    db: AsyncSession,
    tenant_id: UUID,
    code: str,
    language: str = DEFAULT_LANGUAGE,
) -> tuple[MessageTemplateDescriptor, Optional[MessageTemplate]]:
    """Retourne (descriptor, row).

    - `descriptor` : déclaration depuis le registry (toujours présent)
    - `row` : ligne BD si personnalisée, sinon None (→ utiliser le défaut du registry)
    """
    descriptor = get_template_descriptor(code)

    stmt = select(MessageTemplate).where(
        MessageTemplate.tenant_id == tenant_id,
        MessageTemplate.code == code,
        MessageTemplate.language == language,
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    return descriptor, row


async def get_content(
    db: AsyncSession,
    tenant_id: UUID,
    code: str,
    language: str = DEFAULT_LANGUAGE,
) -> tuple[Optional[str], str]:
    """Retourne (subject, content) prêts à être rendus.

    Si pas personnalisé en BD, retourne les valeurs par défaut du registry.
    Lit le cache d'abord.
    """
    ck = _cache_key(tenant_id, code, language)
    cached = await cache.get_json(ck)
    if cached is not None:
        return cached.get("subject"), cached.get("content", "")

    descriptor, row = await get_template(db, tenant_id, code, language)
    if row is None:
        subject = descriptor.default_subject_fr
        content = descriptor.default_fr
    else:
        subject = row.subject
        content = row.content

    await cache.set_json(ck, {"subject": subject, "content": content}, ttl=CACHE_TTL_SECONDS)
    return subject, content


async def render(
    db: AsyncSession,
    tenant_id: UUID,
    code: str,
    variables: Optional[dict[str, str]] = None,
    language: str = DEFAULT_LANGUAGE,
) -> tuple[Optional[str], str]:
    """Charge le template puis substitue les variables. Renvoie (subject, content).

    Les variables système (`assistant_name`, `support_phone`, `support_email`,
    `support_hours`) sont auto-injectées depuis les settings du tenant.
    Les variables explicites de l'appelant priment en cas de collision.
    """
    subject, content = await get_content(db, tenant_id, code, language)
    sys_vars = await _system_variables(db, tenant_id)
    vars_ = {**sys_vars, **(variables or {})}
    rendered_subject = template_registry.render(subject, vars_) if subject else None
    rendered_content = template_registry.render(content, vars_)
    return rendered_subject, rendered_content


async def _system_variables(db: AsyncSession, tenant_id: UUID) -> dict[str, str]:
    """Variables auto-injectées dans tous les templates depuis settings.

    - `assistant_name`, `support_phone`, `support_email`, `support_hours` ← settings.general
    - `artci_url` ← settings.general.artci_page_url (US-29 AC1)
    - `dpo_email` ← settings.security.dpo_email
    """
    from app.services import settings_service
    out: dict[str, str] = {}
    try:
        general = await settings_service.get_category(db, tenant_id, "general")
        for k in ("assistant_name", "support_phone", "support_email", "support_hours"):
            if k in general and general[k] is not None:
                out[k] = str(general[k])
        if general.get("artci_page_url"):
            out["artci_url"] = str(general["artci_page_url"])
    except Exception as e:  # noqa: BLE001
        logger.warning("system_variables : settings.general indisponible (%s)", e)

    try:
        security = await settings_service.get_category(db, tenant_id, "security")
        if security.get("dpo_email"):
            out["dpo_email"] = str(security["dpo_email"])
    except Exception as e:  # noqa: BLE001
        logger.warning("system_variables : settings.security indisponible (%s)", e)

    return out


async def list_templates(
    db: AsyncSession,
    tenant_id: UUID,
    group: Optional[str] = None,
    language: str = DEFAULT_LANGUAGE,
) -> list[tuple[MessageTemplateDescriptor, Optional[MessageTemplate]]]:
    """Liste tous les templates du registry (filtrés par groupe si fourni),
    en croisant avec les valeurs personnalisées en BD."""
    descriptors = (
        template_registry.by_group(group) if group else template_registry.all()
    )
    if not descriptors:
        return []

    codes = [d.code for d in descriptors]
    stmt = select(MessageTemplate).where(
        MessageTemplate.tenant_id == tenant_id,
        MessageTemplate.code.in_(codes),
        MessageTemplate.language == language,
    )
    rows = {r.code: r for r in (await db.execute(stmt)).scalars().all()}

    return [(d, rows.get(d.code)) for d in descriptors]


# ====================================================================== #
# Écriture
# ====================================================================== #
async def upsert_template(
    db: AsyncSession,
    tenant_id: UUID,
    code: str,
    content: str,
    subject: Optional[str] = None,
    channel: Optional[MessageChannel] = None,
    language: str = DEFAULT_LANGUAGE,
    updated_by: Optional[UUID] = None,
    change_reason: Optional[str] = None,
) -> MessageTemplate:
    """Crée ou met à jour un template.

    - Valide le contenu via le registry (variables obligatoires, longueur max…)
    - Si la valeur est identique à l'existante, ne fait rien (idempotence)
    - Snapshot dans message_template_history avant modification
    - Invalide le cache, écrit un audit log
    """
    descriptor = get_template_descriptor(code)

    # Validation
    template_registry.validate_template(descriptor, content)

    stmt = select(MessageTemplate).where(
        MessageTemplate.tenant_id == tenant_id,
        MessageTemplate.code == code,
        MessageTemplate.language == language,
    )
    row = (await db.execute(stmt)).scalar_one_or_none()

    effective_channel = channel or descriptor.channel
    previous_content: Optional[str] = None

    if row is None:
        row = MessageTemplate(
            tenant_id=tenant_id,
            code=code,
            language=language,
            subject=subject,
            content=content,
            channel=effective_channel,
            version=1,
            is_active=True,
            updated_by=updated_by,
        )
        db.add(row)
        await db.flush()
    else:
        # Idempotence
        if row.content == content and row.subject == subject and row.channel == effective_channel:
            return row

        previous_content = row.content
        # Snapshot avant modification
        snapshot = MessageTemplateHistory(
            template_id=row.id,
            version=row.version,
            subject=row.subject,
            content=row.content,
            changed_by=row.updated_by,
            change_reason=None,
        )
        db.add(snapshot)
        row.subject = subject
        row.content = content
        row.channel = effective_channel
        row.version += 1
        row.updated_by = updated_by

    await db.flush()

    await cache.invalidate(_cache_key(tenant_id, code, language))

    await audit_service.log(
        db,
        tenant_id=tenant_id,
        action=AuditAction.template_changed,
        resource_type="message_template",
        resource_id=str(row.id),
        actor_type="user" if updated_by else "system",
        actor_id=str(updated_by) if updated_by else None,
        details={
            "code": code,
            "language": language,
            "version": row.version,
            "channel": effective_channel.value,
            "previous_content_length": len(previous_content) if previous_content else 0,
            "new_content_length": len(content),
            "change_reason": change_reason,
        },
    )

    return row


async def reset_to_default(
    db: AsyncSession,
    tenant_id: UUID,
    code: str,
    language: str = DEFAULT_LANGUAGE,
    updated_by: Optional[UUID] = None,
) -> MessageTemplate:
    """Réinitialise un template à sa valeur par défaut (depuis le registry)."""
    descriptor = get_template_descriptor(code)
    return await upsert_template(
        db,
        tenant_id=tenant_id,
        code=code,
        content=descriptor.default_fr,
        subject=descriptor.default_subject_fr,
        channel=descriptor.channel,
        language=language,
        updated_by=updated_by,
        change_reason="Reset to default",
    )


# ====================================================================== #
# Historique / rollback
# ====================================================================== #
async def list_history(
    db: AsyncSession,
    tenant_id: UUID,
    code: str,
    language: str = DEFAULT_LANGUAGE,
    limit: int = 50,
) -> list[MessageTemplateHistory]:
    get_template_descriptor(code)  # validation existence

    stmt = (
        select(MessageTemplateHistory)
        .join(MessageTemplate, MessageTemplateHistory.template_id == MessageTemplate.id)
        .where(
            MessageTemplate.tenant_id == tenant_id,
            MessageTemplate.code == code,
            MessageTemplate.language == language,
        )
        .order_by(desc(MessageTemplateHistory.version))
        .limit(limit)
    )
    return list((await db.execute(stmt)).scalars().all())


async def rollback_to_version(
    db: AsyncSession,
    tenant_id: UUID,
    code: str,
    target_version: int,
    language: str = DEFAULT_LANGUAGE,
    updated_by: Optional[UUID] = None,
) -> MessageTemplate:
    stmt = (
        select(MessageTemplateHistory)
        .join(MessageTemplate, MessageTemplateHistory.template_id == MessageTemplate.id)
        .where(
            MessageTemplate.tenant_id == tenant_id,
            MessageTemplate.code == code,
            MessageTemplate.language == language,
            MessageTemplateHistory.version == target_version,
        )
    )
    snapshot = (await db.execute(stmt)).scalar_one_or_none()
    if snapshot is None:
        raise ValueError(
            f"Version {target_version} introuvable pour template {code} ({language})"
        )

    return await upsert_template(
        db,
        tenant_id=tenant_id,
        code=code,
        content=snapshot.content,
        subject=snapshot.subject,
        language=language,
        updated_by=updated_by,
        change_reason=f"Rollback vers version {target_version}",
    )
