"""Service OTP email (US-22) — vérification d'adresse pour les sociétaires.

Backed par Redis pour la persistence courte (10 min de validité).
Trois mécanismes anti-abus :

- **Validité** : `otp_validity_minutes` (défaut 10) depuis settings.general
- **Tentatives max** : `otp_max_attempts` (défaut 3) → re-démarrage du flow après
- **Rate limit** : max 5 demandes par email / 15 min (anti-spam)

Conformité backlog US-22.
"""
from __future__ import annotations

import logging
import secrets
import time
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache
from app.services import settings_service

logger = logging.getLogger(__name__)

# Rate limit : 5 demandes par tranche de 15 min
RATE_LIMIT_WINDOW_SECONDS = 15 * 60
RATE_LIMIT_MAX = 5


def _code_key(email: str) -> str:
    return f"otp:{email.lower().strip()}"


def _ratelimit_key(email: str) -> str:
    return f"otp_rl:{email.lower().strip()}"


def _generate_code() -> str:
    """Code numérique à 6 chiffres, cryptographiquement aléatoire."""
    return f"{secrets.randbelow(10**6):06d}"


# ====================================================================== #
# Public API
# ====================================================================== #
async def request_otp(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    email: str,
) -> dict:
    """Génère un OTP et l'envoie par email.

    Retourne :
        {
            "issued": bool,
            "expires_in_seconds": int,    # si issued
            "rate_limited": bool,
            "reason": str | None,
        }
    """
    email_n = email.lower().strip()

    # Rate limit
    rl_state = await cache.get_json(_ratelimit_key(email_n)) or {"count": 0, "ts": time.time()}
    if rl_state["count"] >= RATE_LIMIT_MAX and (time.time() - rl_state["ts"]) < RATE_LIMIT_WINDOW_SECONDS:
        return {
            "issued": False,
            "rate_limited": True,
            "reason": f"Trop de demandes — réessayez dans {RATE_LIMIT_WINDOW_SECONDS // 60} minutes.",
        }

    # Génère le code et settings
    code = _generate_code()
    validity_min = await settings_service.get_value(db, tenant_id, "general", "otp_validity_minutes")
    ttl = int(validity_min) * 60

    await cache.set_json(
        _code_key(email_n),
        {
            "code": code,
            "attempts": 0,
            "issued_at": time.time(),
        },
        ttl=ttl,
    )

    # Update rate limit (reset si fenêtre expirée)
    if (time.time() - rl_state["ts"]) >= RATE_LIMIT_WINDOW_SECONDS:
        rl_state = {"count": 1, "ts": time.time()}
    else:
        rl_state["count"] += 1
    await cache.set_json(_ratelimit_key(email_n), rl_state, ttl=RATE_LIMIT_WINDOW_SECONDS)

    # Envoi email — best-effort, l'erreur SMTP ne bloque pas la création du code
    try:
        from app.services import email_service
        await email_service.send_otp_email(
            db, tenant_id=tenant_id, to_email=email_n, code=code,
            validity_minutes=int(validity_min),
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("Envoi OTP email échoué pour %s : %s", email_n, e)

    return {
        "issued": True,
        "expires_in_seconds": ttl,
        "rate_limited": False,
        "reason": None,
    }


async def verify_otp(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    email: str,
    code: str,
) -> dict:
    """Vérifie un code soumis. Retourne {ok, attempts_remaining, reason}."""
    email_n = email.lower().strip()
    state = await cache.get_json(_code_key(email_n))
    if state is None:
        return {"ok": False, "attempts_remaining": 0, "reason": "Code expiré ou inexistant. Demandez un nouveau code."}

    max_attempts = await settings_service.get_value(db, tenant_id, "general", "otp_max_attempts")
    attempts = state.get("attempts", 0) + 1

    if attempts > int(max_attempts):
        await cache.invalidate(_code_key(email_n))
        return {
            "ok": False,
            "attempts_remaining": 0,
            "reason": f"Trop de tentatives ({max_attempts}). Demandez un nouveau code.",
        }

    expected = state.get("code")
    if (code or "").strip() != expected:
        state["attempts"] = attempts
        # Préserve le TTL résiduel
        elapsed = time.time() - state.get("issued_at", time.time())
        validity_min = await settings_service.get_value(db, tenant_id, "general", "otp_validity_minutes")
        remaining_ttl = max(1, int(validity_min) * 60 - int(elapsed))
        await cache.set_json(_code_key(email_n), state, ttl=remaining_ttl)
        return {
            "ok": False,
            "attempts_remaining": int(max_attempts) - attempts,
            "reason": "Code incorrect.",
        }

    # OK → on consomme le code (one-shot)
    await cache.invalidate(_code_key(email_n))
    return {"ok": True, "attempts_remaining": int(max_attempts), "reason": None}
