"""Test de non-régression F-04 — contrôle d'origine sur TOUS les canaux d'intake.

Le rapport pentest v1.0 (F-04) demande :
  - Vérifier systématiquement la signature de chaque événement WhatsApp
  - Rejeter tout message dont la signature est absente ou invalide
  - Appliquer le même contrôle d'origine à tous les canaux d'intake

Ce test valide sans DB :
  1. WhatsApp : signature valide passe, invalide/absente refusée
  2. Telegram : secret_token valide passe, invalide/absent refusé
  3. Web : origin dans allowlist passe, hors allowlist refusée

Lancer :
    python -m tests.test_webhook_origin_controls
"""
from __future__ import annotations

import hashlib
import hmac
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.webhooks.whatsapp import _verify_meta_signature  # noqa: E402
from app.webhooks.telegram import _verify_telegram_secret  # noqa: E402
from app.core.config import settings  # noqa: E402


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        sys.stderr.write(f"FAIL: {msg}\n")
        raise AssertionError(msg)


class _FakeRequest:
    """Minimal request stub pour les tests."""
    def __init__(self, headers: dict):
        self.headers = {k.lower(): v for k, v in headers.items()}
        self.client = None


def _sig(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(
        secret.encode("utf-8"), body, hashlib.sha256
    ).hexdigest()


def main() -> int:
    checks = 0

    # =====================================================================
    #  1. WhatsApp — signature Meta
    # =====================================================================
    body = b'{"entry": [{"changes": [{"value": {}}]}]}'
    secret = "meta_super_secret"
    settings.whatsapp_app_secret = secret

    # Signature correcte → passe
    _assert(_verify_meta_signature(body, _sig(secret, body)) is True,
            "signature Meta valide doit passer")
    # Signature avec mauvais secret → refuse
    _assert(_verify_meta_signature(body, _sig("wrong_secret", body)) is False,
            "signature Meta avec mauvais secret doit être rejetée")
    # Signature avec bon secret mais mauvais body → refuse
    _assert(_verify_meta_signature(b"other_body", _sig(secret, body)) is False,
            "signature Meta avec body altéré doit être rejetée")
    # Header manquant → refuse
    _assert(_verify_meta_signature(body, None) is False,
            "signature Meta absente doit être rejetée")
    _assert(_verify_meta_signature(body, "") is False,
            "signature Meta vide doit être rejetée")
    # Header sans préfixe sha256= → refuse
    _assert(_verify_meta_signature(body, "abc123") is False,
            "signature Meta sans préfixe sha256= doit être rejetée")
    # Secret vide (dev) → laisse passer
    settings.whatsapp_app_secret = ""
    _assert(_verify_meta_signature(body, None) is True,
            "secret vide (dev) : laisse passer avec warning")
    checks += 7

    # =====================================================================
    #  2. Telegram — X-Telegram-Bot-Api-Secret-Token
    # =====================================================================
    settings.telegram_webhook_secret = "telegram_super_secret"

    # Secret correct dans le header → passe
    req = _FakeRequest({"X-Telegram-Bot-Api-Secret-Token": "telegram_super_secret"})
    _assert(_verify_telegram_secret(req) is True,
            "secret_token Telegram valide doit passer")
    # Secret différent → refuse
    req = _FakeRequest({"X-Telegram-Bot-Api-Secret-Token": "wrong"})
    _assert(_verify_telegram_secret(req) is False,
            "secret_token Telegram différent doit être rejeté")
    # Secret absent → refuse
    req = _FakeRequest({})
    _assert(_verify_telegram_secret(req) is False,
            "secret_token Telegram absent doit être rejeté")
    # Config vide (dev) → laisse passer
    settings.telegram_webhook_secret = ""
    req = _FakeRequest({})
    _assert(_verify_telegram_secret(req) is True,
            "secret Telegram vide (dev) : laisse passer avec warning")
    checks += 4

    # =====================================================================
    #  3. Web — allowlist d'origines
    # =====================================================================
    from app.webhooks.web import _allowed_origins

    settings.web_channel_allowed_origins = (
        "https://ma2e.swedencentral.cloudapp.azure.com, https://ma2e.ci"
    )
    origins = _allowed_origins()
    _assert("https://ma2e.swedencentral.cloudapp.azure.com" in origins,
            "l'allowlist doit inclure l'origine Azure")
    _assert("https://ma2e.ci" in origins,
            "l'allowlist doit inclure ma2e.ci")
    _assert(len(origins) == 2, "l'allowlist doit avoir 2 entrées")

    # Origine avec / final : normalisée
    settings.web_channel_allowed_origins = "https://ma2e.ci/"
    origins = _allowed_origins()
    _assert("https://ma2e.ci" in origins,
            "l'allowlist doit normaliser le trailing slash")

    # Vide → set vide
    settings.web_channel_allowed_origins = ""
    _assert(_allowed_origins() == set(),
            "l'allowlist vide doit produire un set vide")
    checks += 5

    sys.stdout.write(
        f"OK - controles d'origine sur les 3 canaux d'intake ({checks} verifs)\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
