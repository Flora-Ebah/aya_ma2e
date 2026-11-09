"""Application de la politique de sécurité (settings.security).

Centralise les vérifications réutilisées par auth, users et autres services :
- Validation de la complexité des mots de passe
- Gestion du verrouillage de compte après échecs de login
- Calcul de l'éligibilité à la purge (rétention ARTCI)

Toutes les fonctions chargent les settings via settings_service (avec cache
Redis), avec fallback sur les défauts du registry si BD/cache indisponibles.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services import settings_service
from app.services.settings_registry import registry

logger = logging.getLogger(__name__)

_SPECIAL_CHARS = r"!@#$%^&*()_+\-=\[\]{}|;:,.<>?/~`"


# ====================================================================== #
# Snapshot
# ====================================================================== #
@dataclass(frozen=True)
class SecurityPolicy:
    password_min_length: int
    password_require_special: bool
    password_require_digit: bool
    password_require_uppercase: bool
    login_max_failed_attempts: int
    login_lockout_minutes: int
    session_idle_minutes: int
    dossier_retention_years: int
    retention_grace_days: int
    dpo_response_days: int
    dpo_email: str


def _registry_defaults() -> SecurityPolicy:
    g = lambda k: registry.get("security", k).default  # noqa: E731
    return SecurityPolicy(
        password_min_length=int(g("password_min_length")),
        password_require_special=bool(g("password_require_special")),
        password_require_digit=bool(g("password_require_digit")),
        password_require_uppercase=bool(g("password_require_uppercase")),
        login_max_failed_attempts=int(g("login_max_failed_attempts")),
        login_lockout_minutes=int(g("login_lockout_minutes")),
        session_idle_minutes=int(g("session_idle_minutes")),
        dossier_retention_years=int(g("dossier_retention_years")),
        retention_grace_days=int(g("retention_grace_days")),
        dpo_response_days=int(g("dpo_response_days")),
        dpo_email=str(g("dpo_email")),
    )


async def get_policy(db: AsyncSession, tenant_id: Optional[UUID]) -> SecurityPolicy:
    """Charge la politique effective d'un tenant. Defaults registry si erreur."""
    if tenant_id is None:
        return _registry_defaults()
    try:
        values = await settings_service.get_category(db, tenant_id, "security")
    except Exception as e:  # noqa: BLE001
        logger.warning("Lecture settings.security indisponible (%s), fallback", e)
        return _registry_defaults()

    defaults = _registry_defaults()
    return SecurityPolicy(
        password_min_length=int(values.get("password_min_length", defaults.password_min_length)),
        password_require_special=bool(values.get("password_require_special", defaults.password_require_special)),
        password_require_digit=bool(values.get("password_require_digit", defaults.password_require_digit)),
        password_require_uppercase=bool(values.get("password_require_uppercase", defaults.password_require_uppercase)),
        login_max_failed_attempts=int(values.get("login_max_failed_attempts", defaults.login_max_failed_attempts)),
        login_lockout_minutes=int(values.get("login_lockout_minutes", defaults.login_lockout_minutes)),
        session_idle_minutes=int(values.get("session_idle_minutes", defaults.session_idle_minutes)),
        dossier_retention_years=int(values.get("dossier_retention_years", defaults.dossier_retention_years)),
        retention_grace_days=int(values.get("retention_grace_days", defaults.retention_grace_days)),
        dpo_response_days=int(values.get("dpo_response_days", defaults.dpo_response_days)),
        dpo_email=str(values.get("dpo_email", defaults.dpo_email)),
    )


# ====================================================================== #
# Password
# ====================================================================== #
def validate_password(password: str, policy: SecurityPolicy) -> None:
    """Lève ValueError avec un message clair si le mot de passe ne respecte
    pas la politique."""
    if len(password) < policy.password_min_length:
        raise ValueError(
            f"Mot de passe trop court ({len(password)} caractères, "
            f"minimum {policy.password_min_length})."
        )
    if policy.password_require_uppercase and not re.search(r"[A-Z]", password):
        raise ValueError("Le mot de passe doit contenir au moins une majuscule.")
    if policy.password_require_digit and not re.search(r"\d", password):
        raise ValueError("Le mot de passe doit contenir au moins un chiffre.")
    if policy.password_require_special and not re.search(f"[{_SPECIAL_CHARS}]", password):
        raise ValueError("Le mot de passe doit contenir au moins un caractère spécial.")


# ====================================================================== #
# Lockout (tracking en cache Redis — pas de persistance BD)
# ====================================================================== #
# On utilise le cache `cache` pour stocker un compteur par email + un
# timestamp de fin de verrouillage. Pas besoin de table dédiée pour le POC.
from app.core.cache import cache  # noqa: E402


def _attempts_key(email: str) -> str:
    return f"login_attempts:{email.lower().strip()}"


def _lockout_key(email: str) -> str:
    return f"login_lockout:{email.lower().strip()}"


async def is_locked(email: str) -> tuple[bool, Optional[datetime]]:
    """Retourne (locked, lockout_until_iso)."""
    raw = await cache.get_json(_lockout_key(email))
    if raw is None:
        return False, None
    try:
        until = datetime.fromisoformat(raw["until"])
    except (KeyError, ValueError):
        return False, None
    if until <= datetime.now(timezone.utc):
        await cache.invalidate(_lockout_key(email))
        await cache.invalidate(_attempts_key(email))
        return False, None
    return True, until


async def record_failed_attempt(
    email: str, policy: SecurityPolicy,
) -> tuple[int, Optional[datetime]]:
    """Incrémente le compteur d'échecs. Si dépassement, verrouille le compte.

    Retourne (attempts, lockout_until). lockout_until non-null = verrouillé.
    """
    state = await cache.get_json(_attempts_key(email))
    attempts = (state or {}).get("count", 0) + 1

    if attempts >= policy.login_max_failed_attempts:
        until = datetime.now(timezone.utc) + timedelta(minutes=policy.login_lockout_minutes)
        await cache.set_json(
            _lockout_key(email),
            {"until": until.isoformat()},
            ttl=policy.login_lockout_minutes * 60,
        )
        await cache.invalidate(_attempts_key(email))
        return attempts, until

    # TTL = la durée max où on garde la mémoire d'un échec isolé (1h)
    await cache.set_json(_attempts_key(email), {"count": attempts}, ttl=3600)
    return attempts, None


async def reset_attempts(email: str) -> None:
    """À appeler après un login réussi."""
    await cache.invalidate(_attempts_key(email))
    await cache.invalidate(_lockout_key(email))


# ====================================================================== #
# Rétention ARTCI
# ====================================================================== #
def compute_retention_deadline(
    last_activity_at: datetime, policy: SecurityPolicy,
) -> datetime:
    """Date à laquelle un dossier devient éligible à la purge."""
    base = last_activity_at + timedelta(days=365 * policy.dossier_retention_years)
    return base + timedelta(days=policy.retention_grace_days)


def is_eligible_for_purge(
    last_activity_at: datetime, policy: SecurityPolicy,
    now: Optional[datetime] = None,
) -> bool:
    """True si le dossier dépasse la durée légale + période de grâce."""
    now = now or datetime.now(timezone.utc)
    return now >= compute_retention_deadline(last_activity_at, policy)
