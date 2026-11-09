"""SettingsService — lecture et mise à jour des paramètres tenant-scoped.

Garanties :
- Lecture : valeur courante (BD) ou défaut (registry) si non-paramétrée
- Cache Redis (TTL 5 min) sur les lectures pour éviter d'aller en BD à chaque appel LLM
- Écriture : validation via registry, snapshot dans `tenant_setting_history`,
  invalidation du cache, audit log
- Rollback : possibilité de revenir à une version antérieure

Pattern d'usage :
    val = await settings_service.get_value(db, tenant_id, "general", "assistant_name")
    await settings_service.set_value(db, tenant_id, "general", "assistant_name",
                                     "Assistante MA2E", updated_by=user.id, reason="MAJ branding")
"""
from __future__ import annotations

import logging
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache
from app.models import AuditAction
from app.models.setting import (
    SettingValueType,
    TenantSetting,
    TenantSettingHistory,
)
from app.services import audit_service
from app.services.settings_registry import SettingDescriptor, get_descriptor, registry

logger = logging.getLogger(__name__)

# 5 minutes — assez court pour que les changements de paramètres se propagent
# rapidement, assez long pour éviter de bombarder la BD.
CACHE_TTL_SECONDS = 300


def _cache_key(tenant_id: UUID, category: str, key: str) -> str:
    return f"setting:{tenant_id}:{category}:{key}"


# ====================================================================== #
# Lecture
# ====================================================================== #
async def get_value(
    db: AsyncSession,
    tenant_id: UUID,
    category: str,
    key: str,
) -> Any:
    """Retourne la valeur courante du setting, ou la valeur par défaut du registry.

    Lève KeyError si le setting n'existe pas dans le registry.
    """
    descriptor = get_descriptor(category, key)

    # 1) Cache
    ck = _cache_key(tenant_id, category, key)
    cached = await cache.get_json(ck)
    if cached is not None:
        return _unwrap(cached)

    # 2) BD
    stmt = select(TenantSetting).where(
        TenantSetting.tenant_id == tenant_id,
        TenantSetting.category == category,
        TenantSetting.key == key,
    )
    row = (await db.execute(stmt)).scalar_one_or_none()

    if row is None:
        # Pas de valeur paramétrée → on retourne le défaut (sans le mettre en BD)
        value = descriptor.default
    else:
        value = _unwrap(row.value)

    # 3) Cache write-through
    await cache.set_json(ck, _wrap(value), ttl=CACHE_TTL_SECONDS)
    return value


async def get_category(
    db: AsyncSession,
    tenant_id: UUID,
    category: str,
) -> dict[str, Any]:
    """Retourne toutes les valeurs d'une catégorie sous forme de dict {key: value}."""
    descriptors = registry.list_category(category)
    if not descriptors:
        return {}

    # On charge toutes les valeurs paramétrées en une requête
    stmt = select(TenantSetting).where(
        TenantSetting.tenant_id == tenant_id,
        TenantSetting.category == category,
    )
    rows = {r.key: r for r in (await db.execute(stmt)).scalars().all()}

    out: dict[str, Any] = {}
    for d in descriptors:
        if d.key in rows:
            out[d.key] = _unwrap(rows[d.key].value)
        else:
            out[d.key] = d.default
    return out


# ====================================================================== #
# Écriture
# ====================================================================== #
async def set_value(
    db: AsyncSession,
    tenant_id: UUID,
    category: str,
    key: str,
    raw_value: Any,
    updated_by: Optional[UUID] = None,
    change_reason: Optional[str] = None,
) -> TenantSetting:
    """Met à jour (ou crée) un setting.

    Étapes :
    1. Validation via le registry (type, bornes, enum, etc.)
    2. Snapshot de la valeur courante dans tenant_setting_history (si modification)
    3. Upsert de la valeur dans tenant_settings
    4. Invalidation cache
    5. Audit log
    """
    descriptor = get_descriptor(category, key)
    new_value = registry.validate(descriptor, raw_value)

    # Récupère la ligne courante (s'il y en a une)
    stmt = select(TenantSetting).where(
        TenantSetting.tenant_id == tenant_id,
        TenantSetting.category == category,
        TenantSetting.key == key,
    )
    row = (await db.execute(stmt)).scalar_one_or_none()

    if row is None:
        # Création initiale (version 1)
        row = TenantSetting(
            tenant_id=tenant_id,
            category=category,
            key=key,
            value=_wrap(new_value),
            value_type=descriptor.value_type,
            version=1,
            updated_by=updated_by,
        )
        db.add(row)
        await db.flush()
        previous_value: Any = descriptor.default
    else:
        previous_value = _unwrap(row.value)
        # Pas de changement réel ? on ne fait rien (idempotence)
        if previous_value == new_value:
            return row
        # Snapshot avant modification
        snapshot = TenantSettingHistory(
            setting_id=row.id,
            version=row.version,
            value=row.value,
            value_type=row.value_type,
            changed_by=row.updated_by,
            change_reason=None,
        )
        db.add(snapshot)
        row.value = _wrap(new_value)
        row.value_type = descriptor.value_type
        row.version += 1
        row.updated_by = updated_by

    await db.flush()

    # Cache invalidation
    await cache.invalidate(_cache_key(tenant_id, category, key))

    # Audit log — on ne loggue pas la valeur en clair si sensible
    audit_details = {
        "category": category,
        "key": key,
        "version": row.version,
        "previous_value": "***" if descriptor.sensitive else previous_value,
        "new_value": "***" if descriptor.sensitive else new_value,
        "change_reason": change_reason,
    }
    await audit_service.log(
        db,
        tenant_id=tenant_id,
        action=AuditAction.setting_changed,
        resource_type="tenant_setting",
        resource_id=str(row.id),
        actor_type="user" if updated_by else "system",
        actor_id=str(updated_by) if updated_by else None,
        details=audit_details,
    )

    return row


async def list_history(
    db: AsyncSession,
    tenant_id: UUID,
    category: str,
    key: str,
    limit: int = 50,
) -> list[TenantSettingHistory]:
    """Retourne l'historique des versions d'un setting (du plus récent au plus ancien)."""
    get_descriptor(category, key)  # validation existence

    stmt = (
        select(TenantSettingHistory)
        .join(TenantSetting, TenantSettingHistory.setting_id == TenantSetting.id)
        .where(
            TenantSetting.tenant_id == tenant_id,
            TenantSetting.category == category,
            TenantSetting.key == key,
        )
        .order_by(desc(TenantSettingHistory.version))
        .limit(limit)
    )
    return list((await db.execute(stmt)).scalars().all())


async def rollback_to_version(
    db: AsyncSession,
    tenant_id: UUID,
    category: str,
    key: str,
    target_version: int,
    updated_by: Optional[UUID] = None,
    change_reason: Optional[str] = None,
) -> TenantSetting:
    """Restaure la valeur d'une version antérieure (qui devient la nouvelle version
    courante avec un numéro de version supérieur)."""
    stmt = (
        select(TenantSettingHistory)
        .join(TenantSetting, TenantSettingHistory.setting_id == TenantSetting.id)
        .where(
            TenantSetting.tenant_id == tenant_id,
            TenantSetting.category == category,
            TenantSetting.key == key,
            TenantSettingHistory.version == target_version,
        )
    )
    snapshot = (await db.execute(stmt)).scalar_one_or_none()
    if snapshot is None:
        raise ValueError(f"Version {target_version} introuvable pour {category}.{key}")

    target_value = _unwrap(snapshot.value)
    reason = change_reason or f"Rollback vers version {target_version}"
    return await set_value(
        db,
        tenant_id=tenant_id,
        category=category,
        key=key,
        raw_value=target_value,
        updated_by=updated_by,
        change_reason=reason,
    )


# ====================================================================== #
# Helpers internes
# ====================================================================== #
def _wrap(value: Any) -> dict:
    """Enrobe une valeur primitive dans un dict pour JSONB (cohérence)."""
    return {"v": value}


def _unwrap(stored: dict) -> Any:
    """Récupère la valeur primitive depuis le dict JSONB stocké."""
    if isinstance(stored, dict) and "v" in stored:
        return stored["v"]
    # Tolérance si la valeur a été stockée brute
    return stored
