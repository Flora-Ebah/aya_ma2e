"""Endpoints de santé pour orchestrateurs (Kubernetes, Container Apps, Railway…).

Trois niveaux distincts :

- `/health/liveness` : ne vérifie rien, retourne 200 si le process tourne.
  → Kubernetes : redémarre le pod si elle échoue plusieurs fois de suite.

- `/health/readiness` : vérifie les dépendances critiques (DB, Redis).
  Retourne 200 seulement si on peut servir du trafic.
  → Kubernetes : retire le pod du load balancer tant qu'elle échoue.

- `/health/system-info` : snapshot opérationnel (admin uniquement).
  Versions, uptime, env, status des dépendances. Pour les écrans ops.
"""
from __future__ import annotations

import os
import platform
import sys
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache
from app.core.config import settings
from app.core.database import get_db
from app.core.tenancy import AuthContext, get_auth_context
from app.models import UserRole

router = APIRouter(prefix="/health", tags=["health"])

# Démarrage du process — utilisé pour calculer l'uptime
_PROCESS_STARTED_AT = time.monotonic()
_PROCESS_STARTED_AT_ISO = datetime.now(timezone.utc).isoformat()


@router.get("/liveness")
async def liveness():
    """Indique simplement que le process est en vie.

    NE PAS vérifier les dépendances ici — sinon une coupure de Redis ferait
    redémarrer tous les pods, ce qui aggrave la situation.
    """
    return {"status": "alive"}


@router.get("/readiness")
async def readiness(db: AsyncSession = Depends(get_db)):
    """Vérifie que les dépendances critiques répondent.

    DB → blocant pour le trafic (retourne 503 si KO)
    Redis → dégrade mais ne bloque pas (cache désactivé en mode dégradé)
    """
    checks = {
        "database": await _check_database(db),
        "cache": await _check_cache(),
    }

    blocking_ok = checks["database"]["ok"]
    overall = "ready" if blocking_ok else "not_ready"

    body = {
        "status": overall,
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if not blocking_ok:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=body,
        )
    return body


@router.get("/system-info")
async def system_info(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Snapshot opérationnel complet. Admin uniquement (pas de fuite vers le public)."""
    if ctx.role not in (UserRole.super_admin, UserRole.tenant_admin):
        raise HTTPException(
            status_code=403,
            detail="Accès admin requis.",
        )

    uptime_s = time.monotonic() - _PROCESS_STARTED_AT
    db_check = await _check_database(db)
    cache_check = await _check_cache()

    return {
        "service": {
            "name": "ma2e-identification-platform",
            "version": "0.2.0",
            "environment": settings.app_env,
            "started_at": _PROCESS_STARTED_AT_ISO,
            "uptime_seconds": round(uptime_s, 1),
            "uptime_human": _humanize_seconds(uptime_s),
        },
        "runtime": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "pid": os.getpid(),
        },
        "dependencies": {
            "database": db_check,
            "cache": cache_check,
        },
        "configuration": {
            # Pas de fuite de secrets : on confirme juste l'existence/format
            "groq_model": settings.groq_model,
            "jwt_algorithm": settings.jwt_algorithm,
            "jwt_expire_minutes": settings.jwt_expire_minutes,
        },
    }


# ====================================================================== #
# Helpers de checks
# ====================================================================== #
async def _check_database(db: AsyncSession) -> dict:
    """SELECT 1 sur Postgres. Mesure la latence."""
    started = time.monotonic()
    try:
        await db.execute(text("SELECT 1"))
        latency_ms = (time.monotonic() - started) * 1000
        return {"ok": True, "latency_ms": round(latency_ms, 1)}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)[:200]}


async def _check_cache() -> dict:
    """SET + GET sur Redis avec une clé éphémère."""
    started = time.monotonic()
    try:
        await cache.set_json("_health_probe", {"ts": time.time()}, ttl=10)
        v = await cache.get_json("_health_probe")
        latency_ms = (time.monotonic() - started) * 1000
        if v is None:
            return {"ok": False, "error": "set/get round-trip échoue", "degraded": True}
        return {"ok": True, "latency_ms": round(latency_ms, 1)}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)[:200], "degraded": True}


def _humanize_seconds(s: float) -> str:
    s = int(s)
    if s < 60:
        return f"{s}s"
    m, s = divmod(s, 60)
    if m < 60:
        return f"{m}m {s}s"
    h, m = divmod(m, 60)
    if h < 24:
        return f"{h}h {m}m"
    d, h = divmod(h, 24)
    return f"{d}j {h}h"
