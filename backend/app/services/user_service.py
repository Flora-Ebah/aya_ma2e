"""Service CRUD utilisateurs back-office.

Règles métier :
- Un super_admin peut tout faire (cross-tenant)
- Un tenant_admin gère uniquement les users de son tenant
- Un agent n'a pas accès à ce service
- Les passwords sont hashés via bcrypt
- Toute opération sensible est auditée (user_created, user_updated, user_deactivated, user_password_reset)
- Suppression = soft delete via `is_active = False` (préservation de l'historique des dossiers traités)
- L'email est unique global (pas par tenant) — un user ne peut appartenir qu'à un seul tenant
"""
from __future__ import annotations

import logging
from typing import Optional
import uuid
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models import AuditAction, AuthMethod, User, UserRole
from app.services import audit_service, security_policy

logger = logging.getLogger(__name__)


# ====================================================================== #
# Lecture
# ====================================================================== #
async def list_users(
    db: AsyncSession,
    *,
    tenant_id: Optional[UUID] = None,
    include_inactive: bool = True,
) -> list[User]:
    """Liste les users. Si tenant_id fourni, filtre — sinon retourne tous (super_admin)."""
    stmt = select(User)
    if tenant_id is not None:
        stmt = stmt.where(User.tenant_id == tenant_id)
    if not include_inactive:
        stmt = stmt.where(User.is_active.is_(True))
    stmt = stmt.order_by(User.created_at.desc())
    return list((await db.execute(stmt)).scalars().all())


async def get_user(db: AsyncSession, user_id: UUID) -> Optional[User]:
    return (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()


async def get_by_email(db: AsyncSession, email: str) -> Optional[User]:
    return (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()


# ====================================================================== #
# Création
# ====================================================================== #
async def create_user(
    db: AsyncSession,
    *,
    email: str,
    name: str,
    role: UserRole,
    password: Optional[str],
    tenant_id: Optional[UUID],
    actor_id: UUID,
    auth_method: AuthMethod = AuthMethod.password,
) -> User:
    """Crée un user.

    - `auth_method=password` : `password` est obligatoire et hashé
    - `auth_method=ad` : `password` doit être None — l'auth est déléguée à l'AD ERANOVE

    Lève ValueError si l'email existe déjà, si le mot de passe ne respecte pas
    la politique ou si la combinaison auth_method/password est incohérente.
    """
    existing = await get_by_email(db, email)
    if existing is not None:
        raise ValueError(f"Un utilisateur avec l'email {email} existe déjà")

    # US-04 règle métier : email professionnel (domaine du groupe) obligatoire
    # si la liste `allowed_email_domains` n'est pas vide.
    try:
        from app.services import settings_service
        allowed = await settings_service.get_value(
            db, tenant_id or uuid.uuid4(), "security", "allowed_email_domains"
        )
    except Exception:
        allowed = []
    if allowed:
        domain = email.lower().strip().split("@")[-1]
        if domain not in [d.lower().strip() for d in allowed]:
            raise ValueError(
                f"Email hors périmètre : seuls les domaines {allowed} sont acceptés "
                f"pour les comptes back-office (politique MA2E)."
            )

    if auth_method == AuthMethod.password:
        if not password:
            raise ValueError("Mot de passe requis pour l'authentification locale.")
        policy = await security_policy.get_policy(db, tenant_id)
        security_policy.validate_password(password, policy)
        password_hash = hash_password(password)
    else:
        # AD : pas de mot de passe local. On refuse si l'admin tente d'en fournir un.
        if password:
            raise ValueError(
                "Aucun mot de passe ne doit être fourni pour un compte AD."
            )
        password_hash = None

    # Cohérence : un super_admin n'a pas de tenant_id
    if role == UserRole.super_admin:
        tenant_id = None
    elif tenant_id is None:
        raise ValueError("tenant_id requis pour un user non super_admin")

    user = User(
        email=email.lower().strip(),
        name=name.strip(),
        role=role,
        auth_method=auth_method,
        password_hash=password_hash,
        tenant_id=tenant_id,
        is_active=True,
    )
    db.add(user)
    await db.flush()

    audit_tenant_id = tenant_id or user.id  # fallback pour super_admin (rare)
    await audit_service.log(
        db,
        tenant_id=audit_tenant_id,
        action=AuditAction.user_created,
        resource_type="user",
        resource_id=str(user.id),
        actor_type="user",
        actor_id=str(actor_id),
        details={
            "email": email,
            "role": role.value,
            "auth_method": auth_method.value,
            "target_tenant_id": str(tenant_id) if tenant_id else None,
        },
    )
    return user


# ====================================================================== #
# Mise à jour
# ====================================================================== #
async def update_user(
    db: AsyncSession,
    user: User,
    *,
    name: Optional[str] = None,
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
    actor_id: UUID,
) -> User:
    """Met à jour un user. Audite uniquement les changements effectifs."""
    changes: dict[str, dict] = {}

    if name is not None and name != user.name:
        changes["name"] = {"from": user.name, "to": name}
        user.name = name.strip()

    if role is not None and role != user.role:
        changes["role"] = {"from": user.role.value, "to": role.value}
        user.role = role
        # Si on promeut au rang super_admin, on retire le tenant
        if role == UserRole.super_admin:
            user.tenant_id = None

    deactivation = False
    if is_active is not None and is_active != user.is_active:
        changes["is_active"] = {"from": user.is_active, "to": is_active}
        user.is_active = is_active
        deactivation = not is_active

    if not changes:
        return user

    await db.flush()

    action = AuditAction.user_deactivated if deactivation else AuditAction.user_updated
    await audit_service.log(
        db,
        tenant_id=user.tenant_id or user.id,
        action=action,
        resource_type="user",
        resource_id=str(user.id),
        actor_type="user",
        actor_id=str(actor_id),
        details={"changes": changes},
    )
    return user


# ====================================================================== #
# Reset password
# ====================================================================== #
async def reset_password(
    db: AsyncSession,
    user: User,
    *,
    new_password: str,
    actor_id: UUID,
) -> User:
    """Reset par un admin — pas besoin de connaître l'ancien mot de passe.
    Applique la politique de sécurité du tenant.

    Refuse les comptes AD : leur mot de passe est géré côté AD ERANOVE.
    """
    if user.auth_method == AuthMethod.ad:
        raise ValueError(
            "Ce compte utilise l'authentification AD. "
            "Le mot de passe est géré par votre administrateur ERANOVE, pas par MA2E."
        )
    policy = await security_policy.get_policy(db, user.tenant_id)
    security_policy.validate_password(new_password, policy)
    user.password_hash = hash_password(new_password)
    await db.flush()

    await audit_service.log(
        db,
        tenant_id=user.tenant_id or user.id,
        action=AuditAction.user_password_reset,
        resource_type="user",
        resource_id=str(user.id),
        actor_type="user",
        actor_id=str(actor_id),
        details={"by_admin": True, "target_email": user.email},
    )
    return user


async def change_own_password(
    db: AsyncSession,
    user: User,
    *,
    current_password: str,
    new_password: str,
) -> User:
    """Self-change : vérifie l'ancien mot de passe + politique.
    Refusé pour les comptes AD (mot de passe géré côté ERANOVE)."""
    if user.auth_method == AuthMethod.ad:
        raise ValueError(
            "Ce compte utilise l'authentification AD ERANOVE. "
            "Changez votre mot de passe via les outils habituels de votre service IT."
        )
    if not user.password_hash or not verify_password(current_password, user.password_hash):
        raise ValueError("Mot de passe actuel incorrect")
    policy = await security_policy.get_policy(db, user.tenant_id)
    security_policy.validate_password(new_password, policy)
    user.password_hash = hash_password(new_password)
    await db.flush()

    await audit_service.log(
        db,
        tenant_id=user.tenant_id or user.id,
        action=AuditAction.user_password_reset,
        resource_type="user",
        resource_id=str(user.id),
        actor_type="user",
        actor_id=str(user.id),
        details={"by_admin": False, "self_service": True},
    )
    return user
