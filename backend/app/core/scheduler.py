"""Scheduler in-process (APScheduler) pour les tâches périodiques.

Démarré au lifespan startup de FastAPI, arrêté au shutdown.

Tâches enregistrées :
- `auto_close_overdue_complements` : 1× par jour à 02:00 UTC (US-21 AC4)

Note : ce scheduler est in-process (un seul container). En multi-replica,
il faut soit le contraindre à un seul replica (env var `SCHEDULER_ENABLED=true`
sur un seul service), soit basculer vers Celery beat. Le pattern est OK
pour la Phase 2 ; à industrialiser pour Phase 3.
"""
from __future__ import annotations

import logging
import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.services import complement_closer

logger = logging.getLogger(__name__)


_scheduler: AsyncIOScheduler | None = None


def _enabled() -> bool:
    """Permet de désactiver le scheduler (env SCHEDULER_ENABLED=false)
    en multi-replica ou en tests."""
    return os.environ.get("SCHEDULER_ENABLED", "true").lower() in ("1", "true", "yes")


async def _job_auto_close_complements():
    try:
        summary = await complement_closer.run_once()
        logger.info("scheduled.auto_close_complements: %s", summary)
    except Exception as e:  # noqa: BLE001
        logger.exception("scheduled.auto_close_complements failed: %s", e)


def start() -> None:
    """À appeler au démarrage de l'app (lifespan FastAPI)."""
    global _scheduler
    if not _enabled():
        logger.info("Scheduler désactivé (SCHEDULER_ENABLED=false)")
        return
    if _scheduler is not None:
        return

    _scheduler = AsyncIOScheduler(timezone="UTC")
    _scheduler.add_job(
        _job_auto_close_complements,
        CronTrigger(hour=2, minute=0),
        id="auto_close_complements",
        name="Clôture auto des compléments périmés (US-21)",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("APScheduler démarré (jobs : auto_close_complements 02:00 UTC)")


def shutdown() -> None:
    """À appeler à l'arrêt (lifespan FastAPI)."""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("APScheduler arrêté")
