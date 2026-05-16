"""API base de connaissances : gestion des sources, scraping live via SSE."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import AsyncGenerator, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import get_db
from app.core.tenancy import AuthContext, get_auth_context, tenant_filter
from app.models import KnowledgeChunk, KnowledgeSource
from app.services.embeddings import embed_many
from app.services.knowledge_ingest import chunk_text
from app.services.scraper import crawl_site

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


class IngestRequest(BaseModel):
    url: str
    max_pages: int = 30


class SourceOut(BaseModel):
    id: UUID
    type: str
    source_url: str
    title: Optional[str]
    chunks_count: int
    status: str
    last_crawled_at: Optional[datetime]


@router.get("/sources", response_model=list[SourceOut])
async def list_sources(
    tenant_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    target = tenant_filter(ctx, tenant_id)
    rows = (
        await db.execute(
            select(KnowledgeSource)
            .where(KnowledgeSource.tenant_id == target)
            .order_by(KnowledgeSource.last_crawled_at.desc().nullslast())
        )
    ).scalars().all()
    return [
        SourceOut(
            id=s.id,
            type=s.type,
            source_url=s.source_url,
            title=s.title,
            chunks_count=s.chunks_count,
            status=s.status,
            last_crawled_at=s.last_crawled_at,
        )
        for s in rows
    ]


@router.get("/stats")
async def stats(
    tenant_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    target = tenant_filter(ctx, tenant_id)
    nb_sources = (
        await db.execute(
            select(func.count(KnowledgeSource.id)).where(
                KnowledgeSource.tenant_id == target
            )
        )
    ).scalar() or 0
    nb_chunks = (
        await db.execute(
            select(func.count(KnowledgeChunk.id)).where(
                KnowledgeChunk.tenant_id == target
            )
        )
    ).scalar() or 0
    return {"sources": nb_sources, "chunks": nb_chunks}


@router.delete("/sources/{source_id}")
async def delete_source(
    source_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    src = (
        await db.execute(select(KnowledgeSource).where(KnowledgeSource.id == source_id))
    ).scalar_one_or_none()
    if not src:
        raise HTTPException(404, "source not found")
    if not ctx.is_super_admin and src.tenant_id != ctx.tenant_id:
        raise HTTPException(403, "forbidden")
    await db.delete(src)
    await db.commit()
    return {"ok": True}


@router.get("/ingest/stream")
async def stream_ingest(
    url: str = Query(...),
    max_pages: int = Query(30, ge=1, le=100),
    tenant_id: Optional[UUID] = Query(None),
    token: Optional[str] = Query(None),  # auth en query string pour EventSource
):
    """Streame en SSE les événements du scraping + ingestion en direct.

    EventSource ne permet pas d'envoyer le header Authorization, donc le token
    JWT passe en query string.
    """
    # Authentification manuelle via le token query
    from app.core.security import decode_token
    from app.models.user import UserRole

    if not token:
        raise HTTPException(401, "missing token")
    try:
        payload = decode_token(token)
        ctx = AuthContext(
            user_id=UUID(payload["sub"]),
            tenant_id=UUID(payload["tenant_id"]) if payload.get("tenant_id") else None,
            role=UserRole(payload["role"]),
        )
    except Exception:
        raise HTTPException(401, "invalid token")

    target_tenant = tenant_filter(ctx, tenant_id)

    async def event_stream() -> AsyncGenerator[bytes, None]:
        def evt(stage: str, **data) -> bytes:
            payload = {"stage": stage, **data}
            return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode("utf-8")

        # Nouvelle session DB pour ce stream (la session de la requête est trop courte)
        engine = create_async_engine(settings.database_url, echo=False)
        Session = async_sessionmaker(engine, expire_on_commit=False)

        try:
            yield evt("start", url=url, max_pages=max_pages, tenant_id=str(target_tenant))

            # 1. Scraping
            yield evt("scrape_start", message=f"Crawl de {url}…")
            pages = await crawl_site(url, max_pages=max_pages)
            yield evt(
                "scrape_done",
                count=len(pages),
                pages=[{"url": p.url, "title": p.title, "chars": len(p.text)} for p in pages],
            )

            if not pages:
                yield evt("done", message="Aucune page récupérée", inserted=0)
                return

            # 2. Ingestion page par page
            inserted = 0
            chunks_total = 0
            async with Session() as db:
                for i, page in enumerate(pages, 1):
                    yield evt(
                        "ingest_page",
                        index=i,
                        total=len(pages),
                        url=page.url,
                        title=page.title,
                    )
                    # Upsert source
                    existing = (
                        await db.execute(
                            select(KnowledgeSource).where(
                                KnowledgeSource.tenant_id == target_tenant,
                                KnowledgeSource.source_url == page.url,
                            )
                        )
                    ).scalar_one_or_none()
                    if existing and existing.content_hash == page.content_hash:
                        yield evt("page_unchanged", url=page.url)
                        continue
                    if existing is None:
                        src = KnowledgeSource(
                            tenant_id=target_tenant,
                            type="url",
                            source_url=page.url,
                            title=page.title[:512] if page.title else None,
                            content_hash=page.content_hash,
                            status="ingesting",
                            last_crawled_at=datetime.utcnow(),
                        )
                        db.add(src)
                        await db.flush()
                    else:
                        await db.execute(
                            delete(KnowledgeChunk).where(KnowledgeChunk.source_id == existing.id)
                        )
                        existing.content_hash = page.content_hash
                        existing.title = page.title[:512] if page.title else existing.title
                        existing.status = "ingesting"
                        existing.last_crawled_at = datetime.utcnow()
                        src = existing
                        await db.flush()

                    chunks = chunk_text(page.text)
                    if not chunks:
                        src.status = "empty"
                        src.chunks_count = 0
                        await db.commit()
                        yield evt("page_empty", url=page.url)
                        continue

                    yield evt("embed", url=page.url, chunks=len(chunks))
                    vectors = await embed_many(chunks)
                    for idx, (content, vec) in enumerate(zip(chunks, vectors)):
                        db.add(
                            KnowledgeChunk(
                                tenant_id=target_tenant,
                                source_id=src.id,
                                source=page.url,
                                chunk_index=idx,
                                content=content,
                                token_count=max(1, len(content) // 4),
                                embedding=vec,
                                extra={"title": page.title},
                            )
                        )
                    src.chunks_count = len(chunks)
                    src.status = "ready"
                    inserted += 1
                    chunks_total += len(chunks)
                    await db.commit()
                    yield evt("page_done", url=page.url, chunks=len(chunks))
                    await asyncio.sleep(0.05)

            yield evt("done", inserted=inserted, chunks_total=chunks_total)
        except Exception as e:
            log.exception("ingest stream failed")
            yield evt("error", message=str(e))
        finally:
            await engine.dispose()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
