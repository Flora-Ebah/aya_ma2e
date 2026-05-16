import json
from typing import Optional

from groq import AsyncGroq

from app.core.config import settings

_client: Optional[AsyncGroq] = None


def _get_client() -> AsyncGroq:
    global _client
    if _client is None:
        _client = AsyncGroq(api_key=settings.groq_api_key)
    return _client


async def chat_complete(system_prompt: str, user_message: str, history: Optional[list[dict]] = None, model: Optional[str] = None) -> str:
    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    client = _get_client()
    resp = await client.chat.completions.create(
        model=model or settings.groq_model,
        messages=messages,
        temperature=0.3,
        max_tokens=512,
    )
    return resp.choices[0].message.content or ""


async def classify_intent(user_message: str, menu_options: list[dict], tenant_name: str) -> dict:
    options_str = "\n".join([f"- {opt['key']}: {opt['label']}" for opt in menu_options])
    system = (
        f"Tu es un classificateur d'intentions pour l'assistant virtuel de {tenant_name}. "
        f"Classe le message de l'utilisateur dans l'UNE des options suivantes :\n{options_str}\n"
        f"- other: si aucune option ne convient.\n\n"
        f"Réponds UNIQUEMENT en JSON valide : "
        f'{{"intent": "<key>", "confidence": 0.0-1.0, "rationale": "<courte explication>"}}'
    )
    try:
        raw = await chat_complete(system_prompt=system, user_message=user_message)
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            return json.loads(raw[start : end + 1])
    except Exception:
        pass
    return {"intent": "other", "confidence": 0.0, "rationale": "fallback"}


async def smart_reply(system_prompt: str, user_message: str, history: list[dict]) -> str:
    return await chat_complete(system_prompt=system_prompt, user_message=user_message, history=history)
