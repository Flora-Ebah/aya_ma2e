"""Wrapper Redis pour cache applicatif.

Pattern :
    from app.core.cache import cache

    await cache.get("user:123")              # -> str | None
    await cache.set("user:123", value, ttl=300)
    await cache.invalidate("user:123")
    await cache.invalidate_pattern("user:*")

Pour les structures Python : utiliser get_json / set_json.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

from app.core.redis import redis_client

logger = logging.getLogger(__name__)


class _Cache:
    """Helper Redis minimaliste mais cohérent avec le reste du projet.

    On évite d'introduire une lib lourde (cachetools, etc.) tant que les besoins
    sont simples : get / set / invalidate / set_json / get_json.
    """

    def __init__(self) -> None:
        self._r = redis_client

    # ------------------------------------------------------------------ #
    # Strings
    # ------------------------------------------------------------------ #
    async def get(self, key: str) -> Optional[str]:
        try:
            return await self._r.get(key)
        except Exception as e:
            # En cas d'incident Redis, on dégrade silencieusement vers "cache miss"
            # plutôt que de casser la requête métier.
            logger.warning("cache.get failed key=%s : %s", key, e)
            return None

    async def set(self, key: str, value: str, ttl: int = 300) -> None:
        try:
            await self._r.set(key, value, ex=ttl)
        except Exception as e:
            logger.warning("cache.set failed key=%s : %s", key, e)

    async def invalidate(self, key: str) -> None:
        try:
            await self._r.delete(key)
        except Exception as e:
            logger.warning("cache.invalidate failed key=%s : %s", key, e)

    async def invalidate_pattern(self, pattern: str) -> int:
        """Supprime toutes les clés matchant `pattern` (utilise SCAN).

        Retourne le nombre de clés supprimées.
        """
        try:
            count = 0
            async for key in self._r.scan_iter(match=pattern, count=200):
                await self._r.delete(key)
                count += 1
            return count
        except Exception as e:
            logger.warning("cache.invalidate_pattern failed pattern=%s : %s", pattern, e)
            return 0

    # ------------------------------------------------------------------ #
    # JSON
    # ------------------------------------------------------------------ #
    async def get_json(self, key: str) -> Optional[Any]:
        raw = await self.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (TypeError, ValueError) as e:
            logger.warning("cache.get_json invalid payload key=%s : %s", key, e)
            return None

    async def set_json(self, key: str, value: Any, ttl: int = 300) -> None:
        try:
            payload = json.dumps(value, default=str, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            logger.warning("cache.set_json non-serializable key=%s : %s", key, e)
            return
        await self.set(key, payload, ttl=ttl)


cache = _Cache()
