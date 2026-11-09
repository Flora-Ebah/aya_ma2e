"""Crée la table reference_lists (one-shot, en attendant Alembic)."""
import asyncio
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import load_dotenv
load_dotenv(BACKEND_ROOT / ".env")

from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.core.database import Base
from app.models.reference_list import ReferenceList  # noqa: F401


async def main() -> None:
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: ReferenceList.__table__.create(sync_conn, checkfirst=True)
        )
    await engine.dispose()
    print("Table reference_lists prête.")


if __name__ == "__main__":
    asyncio.run(main())
