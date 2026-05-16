"""Recherche vectorielle (RAG) sur la base de connaissances MA2E.

Pipeline multi-turn :
1. Query rewrite : transforme le message courant en question autonome via Groq + historique
2. Vector search : top-K chunks via pgvector
3. Answer generation : Groq + history + chunks + instructions de clarification
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from sqlalchemy import desc, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.conversation.llm import chat_complete
from app.models import KnowledgeChunk, Message, MessageDirection
from app.services.embeddings import embed_one

log = logging.getLogger(__name__)

DEFAULT_TOP_K = 5
MIN_SIMILARITY = 0.42  # seuil un peu plus souple pour les follow-ups
HISTORY_LIMIT = 8  # nombre de messages à conserver pour le contexte


@dataclass
class RetrievedChunk:
    content: str
    source: str
    title: str
    similarity: float


@dataclass
class RagAnswer:
    answer: str
    sources: list[RetrievedChunk]
    confidence: float


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
async def fetch_history(
    db: AsyncSession, conversation_id: UUID, limit: int = HISTORY_LIMIT
) -> list[dict]:
    """Récupère les N derniers messages d'une conversation au format chat."""
    rows = (
        await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(desc(Message.created_at))
            .limit(limit)
        )
    ).scalars().all()
    rows = list(reversed(rows))  # ordre chronologique
    out: list[dict] = []
    for m in rows:
        if not m.content:
            continue
        role = "user" if m.direction == MessageDirection.inbound else "assistant"
        out.append({"role": role, "content": m.content})
    return out


async def rewrite_query(message: str, history: list[dict]) -> str:
    """Réécrit le message courant en question autonome en s'aidant de l'historique.

    Indispensable pour les follow-ups type "oui plus de précisions", "et pour les cadres ?", etc.
    Sans réécriture, la recherche vectorielle sur ces messages courts est inefficace.
    """
    if not history:
        return message

    # Si la conversation est très courte, garder la question telle quelle
    if len(message) > 80 and "?" in message:
        return message

    # Construit un mini-transcript pour le LLM
    snippets = []
    for m in history[-6:]:  # 6 derniers tours suffisent
        prefix = "User" if m["role"] == "user" else "AYA"
        snippets.append(f"{prefix}: {m['content'][:200]}")
    transcript = "\n".join(snippets)

    system = (
        "Tu transformes le dernier message de l'utilisateur en une QUESTION AUTONOME, "
        "compréhensible sans le contexte de la conversation, en français.\n\n"
        "Règles :\n"
        "- Garde le sujet exact de la conversation\n"
        "- Si l'utilisateur dit «oui», «plus de précisions», «et pour X», intègre le sujet précédent\n"
        "- Reste concis (1 phrase, max 20 mots)\n"
        "- Si la question est DÉJÀ autonome, renvoie-la telle quelle\n"
        "- Ne réponds PAS, réécris UNIQUEMENT la question\n"
        "- Pas de guillemets, pas de préfixe, juste la question"
    )
    user_prompt = (
        f"Transcript récent :\n{transcript}\n\n"
        f"Dernier message utilisateur : {message}\n\n"
        "Question autonome :"
    )

    try:
        rewritten = await chat_complete(system_prompt=system, user_message=user_prompt)
        rewritten = (rewritten or "").strip().strip('"').strip("'")
        if rewritten and len(rewritten) > 3:
            log.info("query rewrite: %r -> %r", message, rewritten)
            return rewritten
    except Exception as e:
        log.warning("query rewrite failed: %s", e)
    return message


# ----------------------------------------------------------------------
# Search
# ----------------------------------------------------------------------
async def search_chunks(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    query: str,
    top_k: int = DEFAULT_TOP_K,
) -> list[RetrievedChunk]:
    """Recherche vectorielle pure (cosine via pgvector)."""
    query_vec = await embed_one(query)
    vec_literal = "[" + ",".join(f"{x:.6f}" for x in query_vec) + "]"

    sql = text(
        """
        SELECT
            content,
            source,
            COALESCE(extra->>'title', '') AS title,
            1 - (embedding <=> CAST(:vec AS vector)) AS similarity
        FROM knowledge_chunks
        WHERE tenant_id = :tenant_id
          AND embedding IS NOT NULL
        ORDER BY embedding <=> CAST(:vec AS vector)
        LIMIT :k
        """
    )
    rows = (
        await db.execute(
            sql, {"vec": vec_literal, "tenant_id": str(tenant_id), "k": top_k}
        )
    ).all()
    return [
        RetrievedChunk(
            content=row.content,
            source=row.source,
            title=row.title or row.source,
            similarity=float(row.similarity),
        )
        for row in rows
    ]


# ----------------------------------------------------------------------
# Main answer pipeline
# ----------------------------------------------------------------------
async def answer_question(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    tenant_name: str,
    question: str,
    history: Optional[list[dict]] = None,
    top_k: int = DEFAULT_TOP_K,
) -> RagAnswer:
    """Pipeline RAG complet : rewrite + retrieve + generate avec historique."""
    history = history or []

    # 1. Query rewrite si on a un historique
    search_query = question
    if history:
        search_query = await rewrite_query(question, history)

    # 2. Vector search
    chunks = await search_chunks(db, tenant_id=tenant_id, query=search_query, top_k=top_k)

    if not chunks:
        return RagAnswer(
            answer=(
                f"Je n'ai pas encore d'informations sur ce sujet. "
                f"Je vous invite à contacter directement {tenant_name} ou un agent humain."
            ),
            sources=[],
            confidence=0.0,
        )

    best_sim = max(c.similarity for c in chunks)

    if best_sim < MIN_SIMILARITY:
        # Cas où on a rien de pertinent → demander une clarification CONTEXTUELLE MA2E
        clarif_system = (
            f"Tu es AYA, assistante virtuelle de {tenant_name} (Mutuelle des Agents de l'Eau "
            "et de l'Électricité, Côte d'Ivoire). MA2E est une mutuelle d'épargne et de crédit qui "
            "propose à ses sociétaires : crédits (ordinaire, express, immobilier, immobilier différé), "
            "produits d'épargne (express, ordinaire, logement, dépôts), projets immobiliers, "
            "et le statut de sociétaire lui-même.\n\n"
            f"L'utilisateur t'a posé une question mais tu n'as pas trouvé d'information précise.\n\n"
            "Historique récent :\n"
            + ("\n".join(f"- {h['role']}: {h['content'][:200]}" for h in history[-4:]) if history else "(début de conversation)")
            + f"\n\nDernier message utilisateur : « {question} »\n\n"
            "Tâche : pose UNE question de clarification CHALEUREUSE pour comprendre exactement "
            "ce qu'il veut, en proposant des options PERTINENTES dans l'univers MA2E. "
            "Exemple si le message est «conditions pour intégrer» → demander «intégrer quoi exactement ? "
            "Devenir sociétaire MA2E, ouvrir un produit d'épargne, ou souscrire à un crédit ?». "
            "Reste en français, 1-2 phrases max, ne propose JAMAIS d'options hors MA2E."
        )
        clarif = await chat_complete(system_prompt=clarif_system, user_message=question)
        return RagAnswer(
            answer=(clarif or "").strip()
            or "Pouvez-vous préciser votre demande ? Souhaitez-vous des informations sur un crédit, une épargne, ou devenir sociétaire ?",
            sources=chunks[:3],
            confidence=best_sim,
        )

    # 3. Build context blocks
    context_blocks = []
    for i, c in enumerate(chunks, 1):
        context_blocks.append(f"[Source {i} — {c.title}]\n{c.content.strip()}")
    context = "\n\n---\n\n".join(context_blocks)

    # 4. Système prompt orienté contexte conversationnel
    system = (
        f"Tu es AYA, assistante virtuelle officielle de {tenant_name} "
        f"(Mutuelle des Agents de l'Eau et de l'Électricité, Côte d'Ivoire).\n\n"
        f"Tu poursuis une conversation. L'historique des messages t'est fourni — tiens-en compte "
        f"pour comprendre le contexte (le sociétaire peut faire référence à un sujet précédent).\n\n"
        f"Règles :\n"
        f"- Réponds en français, chaleureuse, concise, professionnelle\n"
        f"- Utilise UNIQUEMENT les informations des SOURCES ci-dessous\n"
        f"- Si la question est ambiguë (ex: «conditions pour intégrer» sans préciser quoi), "
        f"DEMANDE une clarification au lieu de deviner\n"
        f"- Si la question est un follow-up («oui», «plus de détails»), reprends le SUJET PRÉCÉDENT "
        f"de la conversation et donne plus d'informations sur ce sujet\n"
        f"- Maximum 6 phrases ou une liste courte\n"
        f"- Termine par une question ouverte si pertinent\n"
        f"- Si la personne veut s'identifier / mettre à jour / vérifier son statut → "
        f"oriente vers le menu (tapez *menu*)\n\n"
        f"SOURCES MA2E :\n\n{context}"
    )

    answer = await chat_complete(
        system_prompt=system, user_message=question, history=history
    )
    return RagAnswer(
        answer=(answer or "").strip(),
        sources=chunks,
        confidence=best_sim,
    )
