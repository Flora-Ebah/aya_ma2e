"""API REST des paramètres tenant-scoped.

Endpoints :
    GET    /api/settings/categories
        → liste des catégories disponibles dans le registry

    GET    /api/settings/{category}
        → toutes les valeurs courantes de la catégorie (avec métadonnées)

    GET    /api/settings/{category}/{key}
        → une seule valeur (avec métadonnées)

    PUT    /api/settings/{category}/{key}
        → met à jour la valeur (validation registry + audit + invalidation cache)

    GET    /api/settings/{category}/{key}/history
        → historique des versions

    POST   /api/settings/{category}/{key}/rollback/{version}
        → rollback à une version antérieure
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.tenancy import AuthContext, get_auth_context
from app.models import UserRole
from app.models.setting import TenantSetting
from app.schemas.setting import (
    CategoryValuesOut,
    SettingHistoryEntryOut,
    SettingUpdateIn,
    SettingValueOut,
)
from app.services import settings_service
from app.services.settings_registry import registry

router = APIRouter(prefix="/api/settings", tags=["settings"])


# ====================================================================== #
# Helpers
# ====================================================================== #
def _resolve_tenant(ctx: AuthContext) -> UUID:
    """Résout le tenant cible — l'admin agit toujours sur son tenant.

    Un super_admin doit préciser ?tenant_id=... s'il veut viser un tenant
    spécifique (TODO : à exposer en query param plus tard).
    """
    if not ctx.tenant_id:
        raise HTTPException(
            status_code=400,
            detail="Aucun tenant associé à votre session — précisez le tenant cible.",
        )
    return ctx.tenant_id


def _require_admin(ctx: AuthContext) -> None:
    """Seul un admin (super_admin ou tenant_admin) peut modifier les settings."""
    if ctx.role not in (UserRole.super_admin, UserRole.tenant_admin):
        raise HTTPException(
            status_code=403,
            detail="Seuls les administrateurs peuvent modifier les paramètres.",
        )


def _to_value_out(
    descriptor,
    value,
    setting_row: TenantSetting | None,
) -> SettingValueOut:
    return SettingValueOut(
        category=descriptor.category,
        key=descriptor.key,
        value=value,
        value_type=descriptor.value_type.value,
        version=setting_row.version if setting_row else 1,
        is_default=setting_row is None,
        updated_at=setting_row.updated_at if setting_row else None,
        updated_by=setting_row.updated_by if setting_row else None,
        label=descriptor.label,
        description=descriptor.description,
        enum_options=descriptor.enum_options,
        min_value=descriptor.min_value,
        max_value=descriptor.max_value,
        max_length=descriptor.max_length,
        sensitive=descriptor.sensitive,
        group=descriptor.group,
    )


# ====================================================================== #
# Endpoints
# ====================================================================== #
@router.get("/categories", response_model=list[str])
async def list_categories(
    ctx: AuthContext = Depends(get_auth_context),
):
    """Liste des catégories de paramètres disponibles."""
    return registry.categories()


@router.get("/{category}", response_model=CategoryValuesOut)
async def get_category(
    category: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Retourne toutes les valeurs courantes d'une catégorie."""
    tenant_id = _resolve_tenant(ctx)
    descriptors = registry.list_category(category)
    if not descriptors:
        raise HTTPException(status_code=404, detail=f"Catégorie inconnue : {category}")

    # Charge les rows une seule fois
    stmt = select(TenantSetting).where(
        TenantSetting.tenant_id == tenant_id,
        TenantSetting.category == category,
    )
    rows = {r.key: r for r in (await db.execute(stmt)).scalars().all()}

    out_items = []
    for d in descriptors:
        row = rows.get(d.key)
        # Tolérance : la valeur stockée peut être directe ou wrappée {"v": ...}
        if row:
            stored = row.value
            value = stored["v"] if isinstance(stored, dict) and "v" in stored else stored
        else:
            value = d.default
        out_items.append(_to_value_out(d, value, row))

    return CategoryValuesOut(category=category, settings=out_items)


@router.get("/{category}/{key}", response_model=SettingValueOut)
async def get_setting(
    category: str,
    key: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Retourne la valeur courante d'un setting."""
    tenant_id = _resolve_tenant(ctx)
    descriptor = registry.get(category, key)
    if descriptor is None:
        raise HTTPException(status_code=404, detail=f"Setting inconnu : {category}.{key}")

    stmt = select(TenantSetting).where(
        TenantSetting.tenant_id == tenant_id,
        TenantSetting.category == category,
        TenantSetting.key == key,
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row:
        stored = row.value
        value = stored["v"] if isinstance(stored, dict) and "v" in stored else stored
    else:
        value = descriptor.default
    return _to_value_out(descriptor, value, row)


@router.put("/{category}/{key}", response_model=SettingValueOut)
async def update_setting(
    category: str,
    key: str,
    payload: SettingUpdateIn,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Met à jour un setting (admin uniquement)."""
    _require_admin(ctx)
    tenant_id = _resolve_tenant(ctx)
    descriptor = registry.get(category, key)
    if descriptor is None:
        raise HTTPException(status_code=404, detail=f"Setting inconnu : {category}.{key}")

    try:
        row = await settings_service.set_value(
            db,
            tenant_id=tenant_id,
            category=category,
            key=key,
            raw_value=payload.value,
            updated_by=ctx.user_id,
            change_reason=payload.change_reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    await db.commit()
    await db.refresh(row)

    stored = row.value
    value = stored["v"] if isinstance(stored, dict) and "v" in stored else stored
    return _to_value_out(descriptor, value, row)


@router.get(
    "/{category}/{key}/history",
    response_model=list[SettingHistoryEntryOut],
)
async def list_history(
    category: str,
    key: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Historique des versions d'un setting (du plus récent au plus ancien)."""
    tenant_id = _resolve_tenant(ctx)
    descriptor = registry.get(category, key)
    if descriptor is None:
        raise HTTPException(status_code=404, detail=f"Setting inconnu : {category}.{key}")

    history = await settings_service.list_history(
        db, tenant_id=tenant_id, category=category, key=key, limit=limit
    )
    return [
        SettingHistoryEntryOut(
            version=h.version,
            value=h.value["v"] if isinstance(h.value, dict) and "v" in h.value else h.value,
            value_type=h.value_type.value,
            changed_by=h.changed_by,
            change_reason=h.change_reason,
            created_at=h.created_at,
        )
        for h in history
    ]


@router.post(
    "/{category}/{key}/rollback/{target_version}",
    response_model=SettingValueOut,
)
async def rollback(
    category: str,
    key: str,
    target_version: int,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Restaure une version antérieure d'un setting."""
    _require_admin(ctx)
    tenant_id = _resolve_tenant(ctx)
    descriptor = registry.get(category, key)
    if descriptor is None:
        raise HTTPException(status_code=404, detail=f"Setting inconnu : {category}.{key}")

    try:
        row = await settings_service.rollback_to_version(
            db,
            tenant_id=tenant_id,
            category=category,
            key=key,
            target_version=target_version,
            updated_by=ctx.user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    await db.commit()
    await db.refresh(row)

    stored = row.value
    value = stored["v"] if isinstance(stored, dict) and "v" in stored else stored
    return _to_value_out(descriptor, value, row)
