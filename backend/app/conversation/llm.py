"""LLM conversationnel — bascule vers Azure OpenAI (gpt-5.4-mini).

Garde l'interface (chat_complete, classify_intent, smart_reply,
tenant_chat_complete) **identique** à l'ancienne version Groq pour que les
modules appelants (workflow_executor, default_actions, rag…) n'aient
rien à modifier.

Le routage technique se fait dans `llm_azure.py` qui parle directement à
la Responses API Azure.
"""
import json
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.conversation import llm_azure


async def chat_complete(
    system_prompt: str,
    user_message: str,
    history: Optional[list[dict]] = None,
    model: Optional[str] = None,  # ignoré : Azure utilise le deployment configuré
    temperature: float = 0.3,
    max_tokens: int = 512,
) -> str:
    """Appel LLM avec historique optionnel.

    La Responses API Azure accepte un tableau `input` de role/content.
    On reconstruit ce tableau à partir du system prompt + historique + dernier
    message utilisateur.
    """
    # NB: notre wrapper Azure ne gère pas (encore) l'historique multi-tours en
    # natif. On le sérialise dans le user_message au format conversationnel
    # quand il est fourni, ce qui couvre les besoins actuels (RAG + chat libre).
    if history:
        rendered_history = "\n".join(
            f"{m['role'].upper()} : {m['content']}" for m in history if m.get('content')
        )
        user_message = (
            f"Historique récent de la conversation :\n{rendered_history}\n\n"
            f"Message courant de l'utilisateur :\n{user_message}"
        )

    return await llm_azure.chat_complete(
        system_prompt=system_prompt,
        user_message=user_message,
        max_tokens=max_tokens,
        temperature=temperature,
    )


async def classify_intent(
    user_message: str, menu_options: list[dict], tenant_name: str,
) -> dict:
    """Classifie un message dans l'une des options du menu (ou 'other')."""
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


async def smart_reply(
    system_prompt: str, user_message: str, history: list[dict],
) -> str:
    return await chat_complete(
        system_prompt=system_prompt, user_message=user_message, history=history,
    )


async def tenant_chat_complete(
    db: AsyncSession,
    tenant_id: Optional[UUID],
    *,
    task_prompt: str,
    user_message: str,
    history: Optional[list[dict]] = None,
) -> str:
    """High-level helper qui charge les settings IA du tenant.

    Le `task_prompt` est concaténé à la persona globale (ai_persona_intro) pour
    bâtir le system prompt final. Permet à chaque tenant d'avoir un ton/des
    règles propres tout en gardant des consignes par tâche.
    """
    from app.services.ai_settings_service import get_for_tenant

    ai = await get_for_tenant(db, tenant_id)
    system_prompt = ai.build_system_prompt(task_prompt)

    if history and ai.max_history_messages > 0:
        history = history[-ai.max_history_messages:]
    elif history and ai.max_history_messages == 0:
        history = None

    return await chat_complete(
        system_prompt=system_prompt,
        user_message=user_message,
        history=history,
        temperature=ai.temperature,
        max_tokens=ai.max_tokens,
    )
