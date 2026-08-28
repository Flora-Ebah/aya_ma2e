"""Wrapper Azure OpenAI — Chat Completions API.

Pourquoi Chat Completions au lieu de Responses API ?
- Chat Completions est l'API mature et universellement supportée
- L'URL contient le deployment, ce qui évite les erreurs "DeploymentNotFound"
- Format de requête/réponse stable et documenté

Endpoint Azure attendu (sans suffixe) :
    https://<resource>.cognitiveservices.azure.com/

URL complète appelée :
    {endpoint}/openai/deployments/{deployment}/chat/completions?api-version={version}

Format requête :
    {
      "messages": [
        {"role": "system", "content": "..."},
        {"role": "user", "content": "..."}
      ],
      "max_tokens": 4096,
      "temperature": 0.3
    }

Format réponse :
    {
      "choices": [{"message": {"content": "..."}}],
      "usage": {...}
    }
"""
from __future__ import annotations

import json
import logging
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def is_configured() -> bool:
    """Vrai si toutes les variables Azure OpenAI sont renseignées."""
    return bool(
        settings.azure_openai_endpoint
        and settings.azure_openai_api_key
        and settings.azure_openai_deployment
    )


def _build_url() -> str:
    """Construit l'URL Azure Chat Completions standard."""
    base = settings.azure_openai_endpoint.rstrip("/")
    deployment = settings.azure_openai_deployment
    version = settings.azure_openai_api_version
    return f"{base}/openai/deployments/{deployment}/chat/completions?api-version={version}"


def _build_headers() -> dict:
    return {
        "api-key": settings.azure_openai_api_key,
        "Content-Type": "application/json",
    }


async def chat_complete(
    *,
    system_prompt: Optional[str] = None,
    user_message: str,
    max_tokens: int = 4096,
    temperature: float = 0.3,
    response_format: Optional[dict] = None,
) -> str:
    """Appel chat simple : system + user → texte de réponse.

    Lève RuntimeError en cas d'échec (timeout, erreur 4xx/5xx, JSON mal formé).

    `response_format` — pass-through vers Azure OpenAI. Utilisé notamment par
    `structured_output` pour forcer `{"type": "json_object"}` (F-01).
    """
    if not is_configured():
        raise RuntimeError(
            "Azure OpenAI non configuré (AZURE_OPENAI_ENDPOINT manquant)"
        )

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_message})

    payload = {
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if response_format is not None:
        payload["response_format"] = response_format

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                _build_url(),
                headers=_build_headers(),
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        logger.error("Azure OpenAI HTTP %s : %s", e.response.status_code, e.response.text[:500])
        raise RuntimeError(f"Azure OpenAI erreur {e.response.status_code}") from e
    except (httpx.HTTPError, json.JSONDecodeError) as e:
        logger.error("Azure OpenAI appel échoué : %s", e)
        raise RuntimeError(str(e)) from e

    # Chat Completions API → choices[0].message.content
    try:
        return data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        logger.warning(
            "Azure OpenAI : structure de réponse inattendue : %s",
            str(data)[:300],
        )
        return ""


async def structured_output(
    *,
    system_prompt: str,
    user_message: str,
    max_tokens: int = 4096,
) -> dict:
    """Demande au LLM de répondre en JSON strict, retourne le dict parsé.

    F-01 — force `response_format={"type": "json_object"}` côté Azure OpenAI
    pour que le modèle NE PUISSE PAS répondre autre chose qu'un JSON valide.
    Cela ferme la porte aux prompt injections qui tentent de faire répondre
    en texte libre (« IGNORE tout ce qui précède et écris… »).

    Si le modèle bavarde quand même autour du JSON (mode non supporté par la
    version d'API), on extrait le premier objet { ... }. JSON invalide → {}.
    """
    raw = await chat_complete(
        system_prompt=system_prompt,
        user_message=user_message,
        max_tokens=max_tokens,
        temperature=0.0,  # déterminisme pour l'extraction structurée
        response_format={"type": "json_object"},
    )
    if not raw:
        return {}

    # Extraction du premier objet JSON
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end <= start:
        logger.warning("Pas de JSON trouvé dans la réponse Azure OpenAI : %r", raw[:200])
        return {}

    candidate = raw[start : end + 1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as e:
        logger.warning("JSON Azure OpenAI invalide : %s | raw=%r", e, candidate[:200])
        return {}
