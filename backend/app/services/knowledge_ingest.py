"""Pipeline d'ingestion : scraping → chunking → embeddings → DB.

Approche chunking : par paragraphes sémantiques avec fenêtre de tokens (cible 400,
overlap ~50). Pas de tokenizer complexe, on approxime 1 token ≈ 4 caractères pour
les textes français.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KnowledgeChunk, KnowledgeSource
from app.services.embeddings import embed_many
from app.services.scraper import ScrapedPage, crawl_site

log = logging.getLogger(__name__)

# 1 token ≈ 4 chars (FR). On vise des chunks de ~400 tokens = ~1600 chars
CHUNK_TARGET_CHARS = 1600
CHUNK_OVERLAP_CHARS = 200
CHUNK_MIN_CHARS = 200


def _split_paragraphs(text: str) -> list[str]:
    """Split par lignes vides ou doubles sauts."""
    parts = re.split(r"\n\s*\n", text)
    return [p.strip() for p in parts if p.strip()]


def chunk_text(text: str) -> list[str]:
    """Découpe un texte en chunks sémantiques avec overlap."""
    paragraphs = _split_paragraphs(text)
    if not paragraphs:
        return []

    chunks: list[str] = []
    buffer = ""

    def flush():
        nonlocal buffer
        if len(buffer) >= CHUNK_MIN_CHARS:
            chunks.append(buffer.strip())
        buffer = ""

    for para in paragraphs:
        if len(buffer) + len(para) + 2 <= CHUNK_TARGET_CHARS:
            buffer = (buffer + "\n\n" + para).strip() if buffer else para
        else:
            # Si le buffer a déjà du contenu, on l'émet avec overlap
            if buffer:
                chunks.append(buffer.strip())
                tail = buffer[-CHUNK_OVERLAP_CHARS:] if len(buffer) > CHUNK_OVERLAP_CHARS else buffer
                buffer = (tail + "\n\n" + para).strip()
            else:
                # Paragraphe seul trop gros → split brut
                for i in range(0, len(para), CHUNK_TARGET_CHARS - CHUNK_OVERLAP_CHARS):
                    sub = para[i : i + CHUNK_TARGET_CHARS]
                    if len(sub) >= CHUNK_MIN_CHARS:
                        chunks.append(sub.strip())

    flush()
    return chunks


async def ingest_pages(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    pages: Iterable[ScrapedPage],
) -> dict:
    """Ingère un ensemble de pages scrapées dans la base vectorielle.

    Stratégie : upsert par URL (delete chunks existants si content_hash a changé).
    Retourne un récap.
    """
    stats = {"pages_inserted": 0, "pages_unchanged": 0, "chunks_inserted": 0}

    for page in pages:
        # Chercher source existante
        existing = await db.execute(
            select(KnowledgeSource).where(
                KnowledgeSource.tenant_id == tenant_id,
                KnowledgeSource.source_url == page.url,
            )
        )
        src = existing.scalar_one_or_none()

        if src and src.content_hash == page.content_hash:
            stats["pages_unchanged"] += 1
            continue

        if src is None:
            src = KnowledgeSource(
                tenant_id=tenant_id,
                type="url",
                source_url=page.url,
                title=page.title[:512] if page.title else None,
                content_hash=page.content_hash,
                status="ingesting",
                last_crawled_at=datetime.now(timezone.utc),
            )
            db.add(src)
            await db.flush()  # pour avoir src.id
        else:
            # Re-ingest : virer les anciens chunks
            await db.execute(
                KnowledgeChunk.__table__.delete().where(
                    KnowledgeChunk.source_id == src.id
                )
            )
            src.content_hash = page.content_hash
            src.title = page.title[:512] if page.title else src.title
            src.status = "ingesting"
            src.last_crawled_at = datetime.now(timezone.utc)
            await db.flush()

        # Chunk + embed
        chunks = chunk_text(page.text)
        if not chunks:
            src.status = "empty"
            src.chunks_count = 0
            await db.commit()
            continue

        vectors = await embed_many(chunks)

        for i, (content, vec) in enumerate(zip(chunks, vectors)):
            row = KnowledgeChunk(
                tenant_id=tenant_id,
                source_id=src.id,
                source=page.url,
                chunk_index=i,
                content=content,
                token_count=max(1, len(content) // 4),
                embedding=vec,
                extra={"title": page.title},
            )
            db.add(row)

        src.chunks_count = len(chunks)
        src.status = "ready"
        stats["pages_inserted"] += 1
        stats["chunks_inserted"] += len(chunks)
        await db.commit()
        log.info("ingested %s -> %d chunks", page.url, len(chunks))

    return stats


async def ingest_url(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    start_url: str,
    max_pages: int = 30,
) -> dict:
    """Crawl + ingest un site complet à partir d'une URL racine."""
    pages = await crawl_site(start_url, max_pages=max_pages)
    log.info("scraped %d pages from %s", len(pages), start_url)
    return await ingest_pages(db, tenant_id=tenant_id, pages=pages)
