"""Façade de lecture des paramètres IA pour un tenant.

Agrège les settings de la catégorie `ai` en une dataclass `AISettings`
consommée par le moteur conversationnel (`app/conversation/llm.py` et les
actions de workflow dans `default_actions.py`).

Avantages :
- Une seule passe BD/cache au lieu d'un get_value par paramètre
- Type-safe : les callers manipulent un objet plutôt qu'un dict
- Fallback : si la BD est indisponible, retourne les défauts du registry
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services import settings_service
from app.services.settings_registry import registry

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AISettings:
    """Snapshot des paramètres IA d'un tenant à un instant donné."""
    model: str
    temperature: float
    max_tokens: int
    max_history_messages: int
    persona_intro: str
    response_language: str
    fallback_message: str

    def build_system_prompt(self, task_specific: str) -> str:
        """Concatène la persona (préambule global) + un prompt spécifique à la tâche.

        Permet de garder la cohérence de ton et de règles RGPD entre toutes
        les invocations LLM (intent routing, RAG, escalade, etc.).
        """
        task = (task_specific or "").strip()
        if not task:
            return self.persona_intro
        return f"{self.persona_intro}\n\n---\n\n{task}"


def _registry_defaults() -> AISettings:
    """AISettings construite uniquement à partir des défauts du registry."""
    g = lambda k: registry.get("ai", k).default  # noqa: E731
    return AISettings(
        model=g("ai_model"),
        temperature=float(g("ai_temperature")),
        max_tokens=int(g("ai_max_tokens")),
        max_history_messages=int(g("ai_max_history_messages")),
        persona_intro=g("ai_persona_intro"),
        response_language=g("ai_response_language"),
        fallback_message=g("ai_fallback_message"),
    )


async def get_for_tenant(
    db: AsyncSession,
    tenant_id: Optional[UUID],
) -> AISettings:
    """Charge les paramètres IA effectifs du tenant.

    Si `tenant_id` est None ou en cas d'erreur, retourne les défauts registry.
    Profite du cache Redis embarqué dans settings_service.
    """
    if tenant_id is None:
        return _registry_defaults()

    try:
        values = await settings_service.get_category(db, tenant_id, "ai")
    except Exception as e:  # noqa: BLE001
        logger.warning("Lecture settings.ai impossible (%s), fallback registry", e)
        return _registry_defaults()

    defaults = _registry_defaults()
    return AISettings(
        model=values.get("ai_model", defaults.model),
        temperature=float(values.get("ai_temperature", defaults.temperature)),
        max_tokens=int(values.get("ai_max_tokens", defaults.max_tokens)),
        max_history_messages=int(values.get("ai_max_history_messages", defaults.max_history_messages)),
        persona_intro=values.get("ai_persona_intro", defaults.persona_intro),
        response_language=values.get("ai_response_language", defaults.response_language),
        fallback_message=values.get("ai_fallback_message", defaults.fallback_message),
    )
