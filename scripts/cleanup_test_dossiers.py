"""Supprime les dossiers de test (sociétaires sans nom réel).

Usage (depuis la racine du projet) :
    python scripts/cleanup_test_dossiers.py
"""
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from dotenv import load_dotenv

load_dotenv(ROOT / "backend" / ".env")

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models import Dossier, EndUser


# Liste des dossiers à supprimer
DOSSIERS_TO_DELETE = [
    "MA2E-2026-000005",
]


async def main():
    engine = create_async_engine(settings.database_url, echo=False)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as db:
        stmt = select(Dossier).where(Dossier.dossier_number.in_(DOSSIERS_TO_DELETE))
        result = await db.execute(stmt)
        dossiers = result.scalars().all()

        if not dossiers:
            print("⚠️  Aucun dossier trouvé avec ces numéros.")
            return

        print(f"\n🗑️  {len(dossiers)} dossier(s) à supprimer :\n")
        for d in dossiers:
            user = (
                await db.execute(select(EndUser).where(EndUser.id == d.end_user_id))
            ).scalar_one_or_none()
            name = user.name if user else "?"
            print(f"   • {d.dossier_number}  |  {name or '—'}  |  statut: {d.status.value}")

        print()
        confirm = input("Confirmer la suppression ? (oui/non) > ").strip().lower()
        if confirm not in {"oui", "o", "yes", "y"}:
            print("❌ Suppression annulée.")
            return

        deleted = 0
        for d in dossiers:
            await db.delete(d)
            deleted += 1

        await db.commit()
        print(f"\n✅ {deleted} dossier(s) supprimé(s) avec leurs pièces et consentements (cascade).")
        print("   Les end_users associés sont conservés.")
        print("   Les entrées du journal d'audit sont conservées (chaîne d'intégrité).")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
