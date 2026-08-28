"""Rate limiter applicatif basé sur Redis (fixed-window).

Utilisation via le middleware `RateLimitMiddleware` monté dans `app/main.py`.
Aucune modification des endpoints n'est nécessaire — les règles sont
centralisées ici.

Fail-open : si Redis est indisponible, la requête passe (avec un WARNING
en log) plutôt que de bloquer toute l'application.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Callable, Literal, Optional

from app.core.redis import redis_client

log = logging.getLogger(__name__)

KeyStrategy = Literal["ip", "user_or_ip"]


@dataclass(frozen=True)
class RateRule:
    """Une règle de rate limit sur un endpoint."""
    method: str                    # "POST", "GET", "*"
    path_regex: re.Pattern         # compilé une seule fois
    limit: int                     # nombre max de requêtes
    window_seconds: int            # fenêtre en secondes
    key_strategy: KeyStrategy      # "ip" ou "user_or_ip"
    label: str                     # pour la métrique / debug


def _rule(method: str, pattern: str, limit: int, window: int,
          key_strategy: KeyStrategy = "user_or_ip", label: str = "") -> RateRule:
    return RateRule(
        method=method.upper(),
        path_regex=re.compile(pattern),
        limit=limit,
        window_seconds=window,
        key_strategy=key_strategy,
        label=label or pattern,
    )


# ────────────────────────────────────────────────────────────────────────
# Règles actives. Ordre indicatif — on applique la PREMIÈRE qui match.
# Les endpoints non listés ne sont pas rate-limités (webhooks, health, etc.).
# ────────────────────────────────────────────────────────────────────────
RULES: list[RateRule] = [
    # Actions décisives sur dossier (validation, refus, complément).
    # Un agent normal fait ~5-15 décisions/heure. 30/min laisse largement
    # de la marge mais bloque un script d'exfiltration ou un abus.
    _rule("POST", r"^/api/dossiers/[^/]+/(validate|reject|complement)$",
          limit=30, window=60, label="dossier_action"),

    # Exports lourds (DB scan + XLSX/CSV/PDF). 10/min = usage humain OK,
    # blocage d'un scraping automatisé.
    _rule("GET", r"^/api/dossiers/export\.(xlsx|csv)$",
          limit=10, window=60, label="export_dossiers"),
    _rule("GET", r"^/api/stats/overview\.pdf$",
          limit=10, window=60, label="export_pdf_stats"),
    _rule("GET", r"^/api/audit/logs/export\.csv$",
          limit=10, window=60, label="export_audit"),

    # Authentification — 2e couche après le lockout applicatif (5 essais/15 min).
    # Ici on limite au niveau IP pour bloquer un attaquant qui tenterait
    # plusieurs comptes différents depuis la même IP.
    _rule("POST", r"^/api/auth/(login|ad/login)$",
          limit=20, window=300, key_strategy="ip", label="auth_login"),
    _rule("POST", r"^/api/auth/mfa/verify$",
          limit=10, window=300, key_strategy="ip", label="auth_mfa"),
    # Refresh token : usage nominal ~1/heure par utilisateur. On limite à 30/5min
    # par IP pour bloquer un attaquant qui essaierait de brute-forcer des jti.
    _rule("POST", r"^/api/auth/refresh$",
          limit=30, window=300, key_strategy="ip", label="auth_refresh"),

    # OTP — anti brute-force sur le code à 6 chiffres.
    _rule("POST", r"^/api/otp/verify$",
          limit=5, window=60, key_strategy="ip", label="otp_verify"),
    _rule("POST", r"^/api/otp/send$",
          limit=3, window=60, label="otp_send"),

    # F-10 — Simulation de workflow. L'endpoint est admin-only depuis le fix
    # initial, mais l'impact pentest signale un risque de "charge sur le
    # serveur" par appel répété (chaque simulate lance le workflow_executor).
    # 30 simulations / 5 min / user est confortable pour un usage éditorial
    # légitime (test itératif d'un parcours) et coupe court à l'abus.
    _rule("POST", r"^/api/workflows/[^/]+/simulate$",
          limit=30, window=300, label="workflow_simulate"),

    # F-01 — Upload media web anonyme (canal /webhooks/web/upload/{slug}).
    # Le pentest a signalé qu'un attaquant pouvait pusher des fichiers OCR
    # forgés sans limite. 20 uploads / 10 min / IP couvre l'usage nominal
    # (recto + verso + éventuelle reprise) tout en bloquant un scan massif.
    _rule("POST", r"^/webhooks/web/upload/[^/]+$",
          limit=20, window=600, key_strategy="ip", label="webhooks_web_upload"),

    # F-01 — Chat web anonyme. Un attaquant qui automatise le parcours
    # inscription+OCR peut faire beaucoup de POST /webhooks/web/{slug}.
    # 60 messages / 5 min / IP ≈ 1 message / 5 s en pic, ce qui suffit.
    _rule("POST", r"^/webhooks/web/[^/]+$",
          limit=60, window=300, key_strategy="ip", label="webhooks_web_chat"),
]


def find_rule(method: str, path: str) -> Optional[RateRule]:
    """Retourne la première règle qui match, ou None."""
    method_upper = method.upper()
    for rule in RULES:
        if rule.method not in ("*", method_upper):
            continue
        if rule.path_regex.match(path):
            return rule
    return None


async def check_rate_limit(bucket_key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
    """Fixed-window counter dans Redis. Retourne (allowed, current_count).

    Fail-open sur erreur Redis (retourne (True, 0) et log un warning).
    """
    try:
        redis_key = f"rl:{bucket_key}"
        # Pipeline atomique : INCR + EXPIRE (si première requête).
        async with redis_client.pipeline(transaction=True) as pipe:
            await pipe.incr(redis_key)
            await pipe.expire(redis_key, window_seconds, nx=True)  # ne re-arme pas le TTL
            results = await pipe.execute()
        count = int(results[0])
        return (count <= limit, count)
    except Exception as e:  # noqa: BLE001
        log.warning("rate_limit: Redis unavailable, fail-open (%s)", e)
        return (True, 0)
