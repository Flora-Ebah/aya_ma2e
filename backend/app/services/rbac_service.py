"""Service RBAC : gestion des rôles métier et vérification de permissions.

Approche additive : `super_admin` et `tenant_admin` ont TOUTES les permissions
par défaut (équivalents `*`), peu importe les rôles métier attachés.
Les `agent` n'ont **aucune permission** par défaut — les permissions sont
accordées par l'admin via l'attribution de rôles métier.
"""
from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenancy import AuthContext
from app.models import (
    ACTIONS,
    CustomRole,
    MODULES,
    User,
    UserCustomRole,
    UserRole,
    empty_permissions,
)

logger = logging.getLogger(__name__)


# ====================================================================== #
# CRUD rôles métier (US-03)
# ====================================================================== #
async def list_roles(db: AsyncSession, tenant_id: UUID) -> list[CustomRole]:
    stmt = select(CustomRole).where(CustomRole.tenant_id == tenant_id).order_by(CustomRole.name)
    return list((await db.execute(stmt)).scalars().all())


async def get_role(db: AsyncSession, role_id: UUID) -> Optional[CustomRole]:
    return (await db.execute(select(CustomRole).where(CustomRole.id == role_id))).scalar_one_or_none()


async def create_role(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    name: str,
    description: Optional[str],
    permissions: dict,
    created_by: UUID,
) -> CustomRole:
    # Vérif doublon (unique constraint en BD, mais on lève proprement)
    existing = (
        await db.execute(
            select(CustomRole).where(
                CustomRole.tenant_id == tenant_id,
                CustomRole.name == name,
            )
        )
    ).first()
    if existing:
        raise ValueError(f"Un rôle « {name} » existe déjà pour ce tenant.")

    role = CustomRole(
        tenant_id=tenant_id,
        name=name.strip(),
        description=description,
        permissions=_normalize_permissions(permissions),
        created_by=created_by,
    )
    db.add(role)
    await db.flush()
    return role


async def update_role(
    db: AsyncSession,
    role: CustomRole,
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
    permissions: Optional[dict] = None,
    is_active: Optional[bool] = None,
) -> CustomRole:
    if name and name != role.name:
        # check doublon hors lui-même
        existing = (
            await db.execute(
                select(CustomRole).where(
                    CustomRole.tenant_id == role.tenant_id,
                    CustomRole.name == name,
                    CustomRole.id != role.id,
                )
            )
        ).first()
        if existing:
            raise ValueError(f"Un autre rôle s'appelle déjà « {name} ».")
        role.name = name.strip()
    if description is not None:
        role.description = description
    if permissions is not None:
        role.permissions = _normalize_permissions(permissions)
    if is_active is not None:
        role.is_active = is_active
    await db.flush()
    return role


async def delete_role(db: AsyncSession, role: CustomRole) -> None:
    """Supprime un rôle. **Refuse** si encore affecté à au moins un user
    (US-03 règle métier)."""
    assigned = (
        await db.execute(
            select(UserCustomRole).where(UserCustomRole.custom_role_id == role.id).limit(1)
        )
    ).first()
    if assigned:
        raise ValueError(
            "Ce rôle est encore affecté à au moins un utilisateur. "
            "Désaffectez-le d'abord, ou désactivez-le au lieu de le supprimer."
        )
    await db.delete(role)
    await db.flush()


# ====================================================================== #
# Attribution / révocation (US-04)
# ====================================================================== #
async def assign_role(
    db: AsyncSession, *, user_id: UUID, role_id: UUID, granted_by: UUID
) -> UserCustomRole:
    # Idempotent : si déjà assigné, retourne l'existant
    existing = (
        await db.execute(
            select(UserCustomRole).where(
                UserCustomRole.user_id == user_id,
                UserCustomRole.custom_role_id == role_id,
            )
        )
    ).scalar_one_or_none()
    if existing:
        return existing
    link = UserCustomRole(user_id=user_id, custom_role_id=role_id, granted_by=granted_by)
    db.add(link)
    await db.flush()
    return link


async def revoke_role(db: AsyncSession, *, user_id: UUID, role_id: UUID) -> bool:
    link = (
        await db.execute(
            select(UserCustomRole).where(
                UserCustomRole.user_id == user_id,
                UserCustomRole.custom_role_id == role_id,
            )
        )
    ).scalar_one_or_none()
    if link is None:
        return False
    await db.delete(link)
    await db.flush()
    return True


async def list_user_roles(db: AsyncSession, user_id: UUID) -> list[CustomRole]:
    stmt = (
        select(CustomRole)
        .join(UserCustomRole, UserCustomRole.custom_role_id == CustomRole.id)
        .where(UserCustomRole.user_id == user_id, CustomRole.is_active.is_(True))
    )
    return list((await db.execute(stmt)).scalars().all())


# ====================================================================== #
# Vérification de permission (cœur du RBAC)
# ====================================================================== #
async def require_permission(
    db: AsyncSession, ctx: AuthContext, module: str, action: str
) -> None:
    """Lève une HTTPException 403 si l'utilisateur n'a pas la permission demandée."""
    from fastapi import HTTPException
    ok = await has_permission(db, ctx, module, action)
    if not ok:
        raise HTTPException(
            status_code=403,
            detail=f"Accès refusé : permission {module}.{action} requise.",
        )


async def has_permission(
    db: AsyncSession, ctx: AuthContext, module: str, action: str
) -> bool:
    """True si l'utilisateur courant a la permission `module.action`.

    Logique :
    1. super_admin et tenant_admin → True pour tout (rôle système)
    2. agent → True UNIQUEMENT si un de ses rôles métier accorde la permission
    """
    if module not in MODULES or action not in ACTIONS:
        return False

    if ctx.role in (UserRole.super_admin, UserRole.tenant_admin):
        return True

    # Viewer = lecture seule (uniquement action="read")
    if ctx.role == UserRole.viewer:
        return action == "read"

    if ctx.user_id is None:
        return False

    roles = await list_user_roles(db, ctx.user_id)
    for r in roles:
        perms = r.permissions or {}
        if perms.get(module, {}).get(action, False):
            return True
    return False


def _seal_audit_immutability(perms: dict, role: UserRole) -> dict:
    """F-12 — la piste d'audit est strictement append-only, SANS EXCEPTION.

    Le rapport pentest v1.0 exige :
      « Traiter la piste d'audit comme strictement immuable, sans exception
        de rôle. »

    Donc AUCUN rôle applicatif (super_admin inclus) ne peut avoir
    `audit.write` ou `audit.delete`. Cette règle prime sur la matrice RBAC
    en base : même si un rôle métier est mal configuré, `effective_permissions`
    renvoie ces droits à False.

    Break-glass : le setting `settings.audit_break_glass_enabled` permet
    (uniquement en debug/incident majeur, jamais en prod) de restaurer les
    droits pour `super_admin`. Cette exception :
      - est explicitement contrôlée par une variable d'environnement
      - est refusée en production (`APP_ENV=production`) par sécurité
      - devrait être auditée hors bande si elle est activée
    """
    from app.core.config import settings

    break_glass = (
        settings.audit_break_glass_enabled
        and settings.app_env != "production"
        and role == UserRole.super_admin
    )
    if break_glass:
        return perms
    if "audit" in perms:
        perms["audit"]["write"] = False
        perms["audit"]["delete"] = False
    return perms


async def effective_permissions(db: AsyncSession, ctx: AuthContext) -> dict:
    """Snapshot des permissions agrégées pour l'utilisateur courant.

    Règles :
    - super_admin / tenant_admin → TOUT à True (admins systèmes)
    - viewer → `read` à True sur tous les modules, write/delete/export à False
              (consultation seulement)
    - agent → UNION de tous ses rôles métier attribués
    - autre / non connecté → tout à False (sécurité par défaut)

    En sortie, `_seal_audit_immutability` verrouille `audit.write` et
    `audit.delete` à False pour tous sauf super_admin (F-12).
    """
    if ctx.role in (UserRole.super_admin, UserRole.tenant_admin):
        return _seal_audit_immutability(
            {m: {a: True for a in ACTIONS} for m in MODULES},
            ctx.role,
        )

    # Viewer = lecture seule sur tous les modules
    if ctx.role == UserRole.viewer:
        return {m: {a: (a == "read") for a in ACTIONS} for m in MODULES}

    out = empty_permissions()
    if ctx.user_id is None:
        return out
    roles = await list_user_roles(db, ctx.user_id)
    for r in roles:
        perms = r.permissions or {}
        for m in MODULES:
            for a in ACTIONS:
                if perms.get(m, {}).get(a, False):
                    out[m][a] = True
    return _seal_audit_immutability(out, ctx.role)


# ====================================================================== #
# Helpers internes
# ====================================================================== #
def _normalize_permissions(perms: dict) -> dict:
    """Force la matrice à n'avoir QUE les clés (modules, actions) connues
    et avec des bools."""
    out = empty_permissions()
    if not isinstance(perms, dict):
        return out
    for m in MODULES:
        if not isinstance(perms.get(m), dict):
            continue
        for a in ACTIONS:
            v = perms[m].get(a, False)
            out[m][a] = bool(v)
    return out


# ====================================================================== #
# Seed des rôles métier MA2E par défaut (à appeler une fois par tenant)
# ====================================================================== #
DEFAULT_ROLES: list[dict] = [
    {
        "name": "Agent Validateur",
        "description": "Examine et tranche les dossiers (validation, refus, complément).",
        "permissions": {
            "validation": {"read": True, "write": True, "delete": False, "export": False},
            "reporting": {"read": True, "write": False, "delete": False, "export": False},
            "administration": {"read": False, "write": False, "delete": False, "export": False},
            "audit": {"read": False, "write": False, "delete": False, "export": False},
            "conformite": {"read": False, "write": False, "delete": False, "export": False},
        },
    },
    {
        "name": "Superviseur",
        "description": "Pilotage de l'activité, KPI et exports métier.",
        "permissions": {
            "validation": {"read": True, "write": True, "delete": False, "export": True},
            "reporting": {"read": True, "write": True, "delete": False, "export": True},
            "administration": {"read": True, "write": False, "delete": False, "export": False},
            "audit": {"read": True, "write": False, "delete": False, "export": False},
            "conformite": {"read": True, "write": False, "delete": False, "export": False},
        },
    },
    {
        "name": "Lecteur",
        "description": "Lecture seule (dashboards, dossiers, audit).",
        "permissions": {
            "validation": {"read": True, "write": False, "delete": False, "export": False},
            "reporting": {"read": True, "write": False, "delete": False, "export": False},
            "administration": {"read": False, "write": False, "delete": False, "export": False},
            "audit": {"read": True, "write": False, "delete": False, "export": False},
            "conformite": {"read": False, "write": False, "delete": False, "export": False},
        },
    },
    {
        "name": "IT",
        "description": "Support technique : settings, intégrations, monitoring.",
        "permissions": {
            "validation": {"read": True, "write": False, "delete": False, "export": False},
            "reporting": {"read": True, "write": False, "delete": False, "export": False},
            "administration": {"read": True, "write": True, "delete": False, "export": True},
            "audit": {"read": True, "write": False, "delete": False, "export": True},
            "conformite": {"read": True, "write": False, "delete": False, "export": False},
        },
    },
]


async def seed_default_roles(db: AsyncSession, tenant_id: UUID, created_by: Optional[UUID] = None) -> int:
    """Crée les 4 rôles métier MA2E par défaut si absents. Retourne le nombre créé."""
    existing_names = {
        r.name
        for r in (await db.execute(
            select(CustomRole).where(CustomRole.tenant_id == tenant_id)
        )).scalars().all()
    }
    created = 0
    for spec in DEFAULT_ROLES:
        if spec["name"] in existing_names:
            continue
        role = CustomRole(
            tenant_id=tenant_id,
            name=spec["name"],
            description=spec["description"],
            permissions=spec["permissions"],
            created_by=created_by,
        )
        db.add(role)
        created += 1
    if created > 0:
        await db.flush()
    return created
