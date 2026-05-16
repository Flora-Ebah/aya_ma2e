"""Service d'embeddings via Azure OpenAI (text-embedding-3-small, 1536 dims).

Endpoint configuré dans .env :
    AZURE_OPENAI_EMBEDDING=https://<resource>.openai.azure.com/openai/deployments/text-embedding-3-small/embeddings?api-version=2023-05-15
    AZURE_OPENAI_API_KEY_EMBEDDING=<key>
"""
from __future__ import annotations

import asyncio
import logging
from typing import Iterable

import httpx

from app.core.config import settings

log = logging.getLogger(__name__)

EMBEDDING_DIM = 1536
BATCH_SIZE = 16  # Azure tolère plus, mais on garde la marge
HTTP_TIMEOUT = httpx.Timeout(60.0, connect=10.0)


class EmbeddingError(RuntimeError):
    pass


async def embed_one(text: str) -> list[float]:
    vectors = await embed_many([text])
    return vectors[0]


async def embed_many(texts: list[str]) -> list[list[float]]:
    """Vectorise une liste de textes en batchs. Retourne une liste de vecteurs (1536 floats)."""
    if not settings.azure_openai_embedding or not settings.azure_openai_api_key_embedding:
        raise EmbeddingError(
            "Azure OpenAI embedding non configuré (AZURE_OPENAI_EMBEDDING / AZURE_OPENAI_API_KEY_EMBEDDING)"
        )

    cleaned = [(t or "").strip() for t in texts]
    if not any(cleaned):
        return [[0.0] * EMBEDDING_DIM for _ in cleaned]

    out: list[list[float]] = [None] * len(cleaned)  # type: ignore
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        for start in range(0, len(cleaned), BATCH_SIZE):
            batch = cleaned[start : start + BATCH_SIZE]
            # Azure n'aime pas les chaînes vides
            valid_indexes = [i for i, t in enumerate(batch) if t]
            valid_texts = [batch[i] for i in valid_indexes]

            if not valid_texts:
                for i in range(start, start + len(batch)):
                    out[i] = [0.0] * EMBEDDING_DIM
                continue

            try:
                resp = await client.post(
                    settings.azure_openai_embedding,
                    headers={
                        "api-key": settings.azure_openai_api_key_embedding,
                        "Content-Type": "application/json",
                    },
                    json={"input": valid_texts},
                )
                resp.raise_for_status()
                data = resp.json().get("data", [])
                if len(data) != len(valid_texts):
                    raise EmbeddingError(
                        f"Réponse Azure incohérente: {len(data)} vecteurs pour {len(valid_texts)} textes"
                    )
                for local_i, item in zip(valid_indexes, data):
                    vec = item.get("embedding", [])
                    if len(vec) != EMBEDDING_DIM:
                        raise EmbeddingError(
                            f"Dimension inattendue: {len(vec)} (attendu {EMBEDDING_DIM})"
                        )
                    out[start + local_i] = vec
                # Remplir les indexes vides
                for i, t in enumerate(batch):
                    if not t and out[start + i] is None:
                        out[start + i] = [0.0] * EMBEDDING_DIM
            except httpx.HTTPStatusError as e:
                log.error("embeddings http error: %s | %s", e.response.status_code, e.response.text[:300])
                raise EmbeddingError(f"Azure OpenAI {e.response.status_code}") from e
            except Exception as e:
                log.exception("embeddings failed")
                raise EmbeddingError(str(e)) from e

            # Rate-limit cool-down soft entre batchs
            if start + BATCH_SIZE < len(cleaned):
                await asyncio.sleep(0.05)

    return out  # type: ignore
