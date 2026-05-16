"""Migration manuelle pour les tables knowledge.

Drop l'ancienne table knowledge_chunks (Vector 384) et recrée tout avec
Vector(1536) + nouvelle table knowledge_sources.

Usage :
    python -m backend.scripts.migrate_knowledge_tables
"""
import asyncio
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from dotenv import load_dotenv
load_dotenv(ROOT / "backend" / ".env")

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app import models  # noqa: F401
from app.core.config import settings
from app.core.database import Base

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)


async def main() -> None:
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        # Drop ancien knowledge_chunks (Vector 384) — pas de données utiles dedans
        await conn.execute(text("DROP TABLE IF EXISTS knowledge_chunks CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS knowledge_sources CASCADE"))
        await conn.run_sync(Base.metadata.create_all)
        log.info("OK  knowledge_sources + knowledge_chunks (Vector 1536) crees")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
