"""Clôture automatique des dossiers en complément sans réponse (US-21 AC4).

Règle métier : si un dossier en statut `complement_requis` n'a pas reçu de
réponse du sociétaire pendant plus de `complement_response_deadline_days`
jours, il est clôturé automatiquement et l'agent qui l'a demandé est notifié.

Conservation : le dossier reste en BD (archivage). Une nouvelle demande
nécessite un nouveau parcours (règle métier US-21).

Audit : trace `dossier_complement_requested` (déjà), nouvelle action
`dossier_complement_auto_closed` (à ajouter à AuditAction).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models import (
    AuditAction,
    Dossier,
    DossierStatus,
    Tenant,
    User,
)
from app.services import audit_service, settings_service

logger = logging.getLogger(__name__)


async def run_once() -> dict:
    """Tour de scan : clôture les dossiers complément périmés.

    Retourne un résumé pour les logs/monitoring : nb scannés, nb clôturés.
    """
    closed = 0
    scanned = 0
    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as db:
        # Récupère tous les tenants pour appliquer leur seuil propre
        tenants = list((await db.execute(select(Tenant))).scalars().all())

        for tenant in tenants:
            try:
                deadline_days = await settings_service.get_value(
                    db, tenant.id, "general", "complement_response_deadline_days"
                )
            except Exception as e:  # noqa: BLE001
                logger.warning("Lecture deadline tenant %s : %s", tenant.id, e)
                continue
            cutoff = now - timedelta(days=int(deadline_days))

            stmt = select(Dossier).where(
                Dossier.tenant_id == tenant.id,
                Dossier.status == DossierStatus.complement_requis,
                Dossier.updated_at < cutoff,
            )
            rows = list((await db.execute(stmt)).scalars().all())
            scanned += len(rows)

            for dossier in rows:
                dossier.status = DossierStatus.rejete
                dossier.rejection_motive = (
                    f"Clôture automatique : pas de réponse au complément demandé "
                    f"depuis plus de {deadline_days} jours."
                )

                await audit_service.log(
                    db,
                    tenant_id=tenant.id,
                    action=AuditAction.dossier_complement_auto_closed,
                    resource_type="dossier",
                    resource_id=str(dossier.id),
                    actor_type="system",
                    actor_id="scheduler",
                    details={
                        "dossier_number": dossier.dossier_number,
                        "deadline_days": int(deadline_days),
                        "last_activity_at": dossier.updated_at.isoformat() if dossier.updated_at else None,
                    },
                )
                closed += 1

        if closed > 0:
            await db.commit()
            logger.info("Auto-close complément : %d dossier(s) clôturé(s)", closed)

    return {"scanned": scanned, "closed": closed, "ran_at": now.isoformat()}
