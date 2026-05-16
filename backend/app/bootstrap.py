"""Quick DB bootstrap for POC. Creates all tables + pgvector extension.

For production, replace with proper Alembic migrations:
    alembic revision --autogenerate -m "init"
    alembic upgrade head
"""
import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app import models  # noqa: F401 (registers all models)
from app.core.config import settings
from app.core.database import Base

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


async def bootstrap_db() -> None:
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    log.info("✅ Database bootstrap complete.")


if __name__ == "__main__":
    asyncio.run(bootstrap_db())
