"""Configuration du logging applicatif.

Deux modes selon `settings.app_env` :
- `development` / `dev` : format console lisible (couleur si TTY)
- `production` / autres : JSON structuré (1 ligne = 1 événement), consommé par
  les agents log (App Insights, Datadog, Loki, etc.)

À appeler une seule fois au boot dans `app/main.py` AVANT toute log.
"""
from __future__ import annotations

import logging
import sys

import structlog

from app.core.config import settings
from app.core.pii_scrubber import PIIScrubberFilter, scrub_structlog_event


def configure_logging() -> None:
    """Initialise structlog + bridge stdlib logging vers structlog.

    Idempotent : ré-appeler ne provoque pas de double config.
    """
    is_dev = settings.app_env.lower() in ("development", "dev", "local")
    level = logging.INFO if is_dev else logging.INFO

    # Pipeline commun (avant le rendu final)
    # NB : le PII scrubber est placé JUSTE AVANT le rendu final pour
    # masquer aussi les champs ajoutés par les autres processors.
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        scrub_structlog_event,
    ]

    if is_dev:
        # Format lisible (couleurs si terminal)
        final = structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())
    else:
        # JSON pour production / agents
        final = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=shared_processors + [final],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )

    # Bridge le stdlib logging (uvicorn, sqlalchemy…) vers le même format
    handler = logging.StreamHandler(sys.stderr)
    if is_dev:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)-7s %(name)s %(message)s")
        )
    else:
        # JSON minimaliste pour les libs tierces
        handler.setFormatter(_JsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Filtre PII appliqué à TOUS les loggers stdlib (uvicorn, sqlalchemy,
    # les libs tierces, etc.). Le processor structlog s'occupe des logs
    # émis via structlog directement.
    handler.addFilter(PIIScrubberFilter())

    # Réduit le bruit
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


class _JsonFormatter(logging.Formatter):
    """Formateur JSON minimaliste pour les libs stdlib."""

    def format(self, record: logging.LogRecord) -> str:
        import json
        from datetime import datetime, timezone

        payload = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)
