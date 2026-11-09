"""API base de connaissances : gestion des sources, upload de fichiers,
scraping URL en direct (SSE)."""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from datetime import datetime
from typing import AsyncGenerator, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import get_db
from app.core.tenancy import AuthContext, get_auth_context, tenant_filter
from app.models import KnowledgeChunk, KnowledgeSource
from app.services.embeddings import embed_many
from app.services.file_text_extractor import (
    SUPPORTED_EXTENSIONS,
    ExtractionError,
    extract_text,
)
from app.services.knowledge_ingest import chunk_text
from app.services.scraper import crawl_site, crawl_site_iter
from app.services.scraper_spa import crawl_site_spa_iter

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


class UploadOut(BaseModel):
    source_id: UUID
    title: str
    chunks_count: int
    chars: int


MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 Mo


@router.post("/upload", response_model=UploadOut)
async def upload_file(
    file: UploadFile = File(...),
    tenant_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Upload d'un document (PDF, DOCX, XLSX, TXT, MD, CSV) : extraction du
    texte, chunking, embedding, insertion dans ``knowledge_chunks``.

    Déduplication par hash du contenu : un fichier identique déjà ingéré renvoie
    la source existante sans recalculer les embeddings."""
    target = tenant_filter(ctx, tenant_id)
    if not file.filename:
        raise HTTPException(400, "Nom de fichier manquant.")

    data = await file.read()
    if len(data) == 0:
        raise HTTPException(400, "Fichier vide.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            400,
            f"Fichier trop volumineux (max {MAX_UPLOAD_BYTES // (1024 * 1024)} Mo).",
        )

    try:
        text = extract_text(file.filename, data)
    except ExtractionError as exc:
        raise HTTPException(400, str(exc)) from exc

    if not text.strip():
        raise HTTPException(400, "Aucun texte extractible du fichier.")

    content_hash = hashlib.sha256(data).hexdigest()
    pseudo_url = f"file://{file.filename}"

    # Déduplication : même tenant + même hash → on retourne la source existante.
    existing = (
        await db.execute(
            select(KnowledgeSource).where(
                KnowledgeSource.tenant_id == target,
                KnowledgeSource.content_hash == content_hash,
            )
        )
    ).scalar_one_or_none()
    if existing:
        return UploadOut(
            source_id=existing.id,
            title=existing.title or file.filename,
            chunks_count=existing.chunks_count,
            chars=len(text),
        )

    # Même nom mais contenu différent → on remplace les chunks de l'ancienne.
    old = (
        await db.execute(
            select(KnowledgeSource).where(
                KnowledgeSource.tenant_id == target,
                KnowledgeSource.source_url == pseudo_url,
            )
        )
    ).scalar_one_or_none()
    if old:
        await db.execute(
            delete(KnowledgeChunk).where(KnowledgeChunk.source_id == old.id)
        )
        src = old
        src.content_hash = content_hash
        src.title = file.filename[:512]
        src.status = "ingesting"
        src.last_crawled_at = datetime.utcnow()
    else:
        src = KnowledgeSource(
            tenant_id=target,
            type="file",
            source_url=pseudo_url,
            title=file.filename[:512],
            content_hash=content_hash,
            status="ingesting",
            last_crawled_at=datetime.utcnow(),
        )
        db.add(src)
    await db.flush()

    chunks = chunk_text(text)
    if not chunks:
        src.status = "empty"
        src.chunks_count = 0
        await db.commit()
        return UploadOut(source_id=src.id, title=src.title or file.filename, chunks_count=0, chars=len(text))

    vectors = await embed_many(chunks)
    for idx, (content, vec) in enumerate(zip(chunks, vectors)):
        db.add(
            KnowledgeChunk(
                tenant_id=target,
                source_id=src.id,
                source=pseudo_url,
                chunk_index=idx,
                content=content,
                token_count=max(1, len(content) // 4),
                embedding=vec,
                extra={"title": file.filename, "upload": True},
            )
        )
    src.chunks_count = len(chunks)
    src.status = "ready"
    await db.commit()
    log.info(
        "Knowledge upload : %s (%d chars → %d chunks) tenant=%s",
        file.filename,
        len(text),
        len(chunks),
        target,
    )
    return UploadOut(
        source_id=src.id,
        title=file.filename,
        chunks_count=len(chunks),
        chars=len(text),
    )


@router.get("/supported-extensions")
async def supported_extensions():
    """Liste les extensions acceptées par /upload — utile pour le filter côté UI."""
    return {"extensions": sorted(SUPPORTED_EXTENSIONS)}


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
    ctx: AuthContext = Depends(get_auth_context),
):
    """Streame en SSE les événements du scraping + ingestion en direct.

    L'authentification se fait via le cookie httpOnly `ma2e_token`
    (envoyé par EventSource avec `withCredentials: true`).
    """
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

            # 1+2. Scraping streaming + ingestion au fil de l'eau (évite les
            # longues plages silencieuses qui font tomber EventSource/ngrok).
            # On tente Playwright (rend le JS → SPA React/Vue) ; si Playwright
            # ne ramène rien (indisponible, timeout, etc.), on retombe sur
            # httpx (rapide pour les sites statiques / SSR).
            yield evt("scrape_start", message=f"Crawl de {url} (rendu JS)…")
            pages: list = []
            try:
                async for page in crawl_site_spa_iter(url, max_pages=max_pages):
                    pages.append(page)
                    yield evt(
                        "scrape_page",
                        index=len(pages),
                        url=page.url,
                        title=page.title,
                        chars=len(page.text),
                    )
            except Exception as e:
                log.warning("playwright crawl failed, fallback httpx: %s", e)

            if not pages:
                yield evt("scrape_start", message=f"Fallback httpx sur {url}…")
                async for page in crawl_site_iter(url, max_pages=max_pages):
                    pages.append(page)
                    yield evt(
                        "scrape_page",
                        index=len(pages),
                        url=page.url,
                        title=page.title,
                        chars=len(page.text),
                    )

            yield evt(
                "scrape_done",
                count=len(pages),
                pages=[{"url": p.url, "title": p.title, "chars": len(p.text)} for p in pages],
            )

            if not pages:
                yield evt("done", message="Aucune page récupérée", inserted=0)
                return

            # 3. Ingestion page par page
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
