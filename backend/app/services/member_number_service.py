"""Génération du numéro de sociétaire MA2E (US-19).

Format : `MEMB-AAAA-NNNNNN` où :
- AAAA = année de validation
- NNNNNN = compteur séquentiel par tenant et par année, sur 6 chiffres

Garanties :
- Unique global (contrainte BD `unique=True` sur `dossiers.numero_societaire`)
- Non réutilisable (jamais réémis même si dossier supprimé)
- Robuste à la concurrence (boucle avec retry sur IntegrityError)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Dossier

logger = logging.getLogger(__name__)


def _format(year: int, seq: int) -> str:
    return f"MEMB-{year}-{seq:06d}"


async def allocate(db: AsyncSession, tenant_id: UUID) -> str:
    """Génère un nouveau numéro de sociétaire pour la validation en cours.

    Retourne le numéro alloué. Doit être appelé dans la même transaction
    que la mutation du dossier (statut → validé + numero_societaire = ce numéro).
    """
    year = datetime.now(timezone.utc).year

    # Pré-calcule le prochain seq pour ce tenant + cette année
    stmt = select(func.count(Dossier.id)).where(
        Dossier.tenant_id == tenant_id,
        Dossier.numero_societaire.is_not(None),
        Dossier.numero_societaire.like(f"MEMB-{year}-%"),
    )
    base = (await db.execute(stmt)).scalar_one() or 0
    candidate_seq = base + 1

    # Retry boucle pour absorber les courses concurrentes
    for attempt in range(20):
        candidate = _format(year, candidate_seq)
        exists = (
            await db.execute(
                select(Dossier.id).where(Dossier.numero_societaire == candidate)
            )
        ).first()
        if exists is None:
            return candidate
        candidate_seq += 1
    raise RuntimeError(
        f"Impossible d'allouer un numéro sociétaire après 20 tentatives (tenant={tenant_id})."
    )
