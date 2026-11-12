"""Rattrapage : crée les dossiers (page « Dossiers ») des sociétaires DÉJÀ importés.

À lancer une fois sur une base où la table `societaires` a été remplie avant l'ajout du lien
dossier <-> sociétaire. Idempotent : rejouable sans doublon (un dossier par sociétaire).
Les imports suivants créent les dossiers automatiquement.

Usage :  python seeds/sync_societaires_dossiers.py
"""
import asyncio
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import load_dotenv
load_dotenv(BACKEND_ROOT / ".env")

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models import Societaire
from app.services.societaire_dossiers import sync_dossiers


async def main() -> None:
    engine = create_async_engine(settings.database_url)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as db:
        tenants = (await db.execute(select(Societaire.tenant_id).distinct())).scalars().all()
        total_c = total_u = 0
        for tid in tenants:
            rows = (await db.execute(select(Societaire).where(Societaire.tenant_id == tid))).scalars().all()
            c, u = await sync_dossiers(db, tid, rows)
            total_c += c
            total_u += u
        await db.commit()
    await engine.dispose()
    print(f"✅ {total_c} dossier(s) créé(s), {total_u} mis à jour")


if __name__ == "__main__":
    asyncio.run(main())
