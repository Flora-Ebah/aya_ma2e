"""Soft-lock coopératif sur les dossiers (US-17 AC3).

Règle : un dossier ne peut être traité que par un seul agent à la fois.
Pour éviter les locks fantômes (agent qui ferme son onglet), le lock a un TTL
configurable (`dossier_lock_ttl_minutes`, défaut 30 min). Au-delà, un autre
agent peut prendre le lock automatiquement.

Le lock est **coopératif** : il n'empêche pas physiquement une opération en BD,
il sert d'indicateur visuel + de garde-fou côté UI / API REST.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Dossier

logger = logging.getLogger(__name__)

# TTL par défaut du lock — 30 min sans activité de l'agent → réutilisable.
DEFAULT_LOCK_TTL_MINUTES = 30


def is_locked_by_other(dossier: Dossier, user_id: UUID, ttl_minutes: int = DEFAULT_LOCK_TTL_MINUTES) -> bool:
    """True si le dossier est actuellement locké par un autre user (et non expiré)."""
    if dossier.locked_by is None or dossier.locked_at is None:
        return False
    if dossier.locked_by == user_id:
        return False
    expires_at = dossier.locked_at + timedelta(minutes=ttl_minutes)
    return datetime.now(timezone.utc) < expires_at


def lock_status(dossier: Dossier, ttl_minutes: int = DEFAULT_LOCK_TTL_MINUTES) -> dict:
    """Retourne un snapshot lisible pour le frontend (badge dans la liste)."""
    if dossier.locked_by is None or dossier.locked_at is None:
        return {"locked": False}
    expires_at = dossier.locked_at + timedelta(minutes=ttl_minutes)
    expired = datetime.now(timezone.utc) >= expires_at
    return {
        "locked": not expired,
        "locked_by": str(dossier.locked_by) if not expired else None,
        "locked_at": dossier.locked_at.isoformat() if not expired else None,
        "expires_at": expires_at.isoformat(),
    }


async def acquire(
    db: AsyncSession, dossier: Dossier, *, user_id: UUID,
    ttl_minutes: int = DEFAULT_LOCK_TTL_MINUTES,
) -> tuple[bool, Optional[str]]:
    """Tente de prendre le lock sur ce dossier pour l'agent `user_id`.

    Retourne (ok, message). Si déjà locké par quelqu'un d'autre et non expiré,
    renvoie False avec un message clair.
    """
    if is_locked_by_other(dossier, user_id, ttl_minutes):
        return False, (
            f"Ce dossier est en cours de traitement par un autre agent "
            f"jusqu'à {(dossier.locked_at + timedelta(minutes=ttl_minutes)).isoformat()}."
        )

    dossier.locked_by = user_id
    dossier.locked_at = datetime.now(timezone.utc)
    await db.flush()
    return True, None


async def release(db: AsyncSession, dossier: Dossier, user_id: UUID) -> None:
    """Relâche le lock — silencieusement no-op si le lock appartient à un autre."""
    if dossier.locked_by == user_id:
        dossier.locked_by = None
        dossier.locked_at = None
        await db.flush()


async def release_on_decision(db: AsyncSession, dossier: Dossier) -> None:
    """À appeler après une décision (valider/refuser/complément) — relâche
    forcément le lock car le dossier sort de la file de traitement."""
    if dossier.locked_by is not None:
        dossier.locked_by = None
        dossier.locked_at = None
        await db.flush()
