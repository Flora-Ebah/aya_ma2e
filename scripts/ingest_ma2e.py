"""Ingestion de la base de connaissances MA2E.

Scrape ma2e.ci, chunke, vectorise via Azure OpenAI et insère en pgvector.

Usage :
    python scripts/ingest_ma2e.py
    python scripts/ingest_ma2e.py --url https://www.ma2e.ci/ --max 30
"""
import argparse
import asyncio
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from dotenv import load_dotenv
load_dotenv(ROOT / "backend" / ".env")

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models import Tenant
from app.services.knowledge_ingest import ingest_url

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s | %(message)s",
)
log = logging.getLogger("ingest")


async def main(start_url: str, max_pages: int, tenant_slug: str) -> None:
    engine = create_async_engine(settings.database_url, echo=False)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as db:
        tenant = (
            await db.execute(select(Tenant).where(Tenant.slug == tenant_slug))
        ).scalar_one_or_none()
        if not tenant:
            log.error("Tenant slug='%s' introuvable. Lance le seed avant.", tenant_slug)
            return

        log.info("Ingestion vers tenant '%s' (id=%s)", tenant.name, tenant.id)
        log.info("URL de départ : %s (max %d pages)", start_url, max_pages)

        stats = await ingest_url(
            db, tenant_id=tenant.id, start_url=start_url, max_pages=max_pages
        )
        log.info("=" * 60)
        log.info("Recap : %s", stats)
        log.info("=" * 60)

    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="https://www.ma2e.ci/", help="URL racine à scraper")
    parser.add_argument("--max", type=int, default=30, help="Nombre max de pages")
    parser.add_argument("--tenant", default="ma2e", help="Slug du tenant cible")
    args = parser.parse_args()
    asyncio.run(main(args.url, args.max, args.tenant))
