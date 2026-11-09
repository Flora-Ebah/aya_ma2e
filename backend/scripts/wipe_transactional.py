"""Vide les tables transactionnelles.

Conservé : users, custom_roles, user_custom_roles, tenants, tenant_channels,
collaborateurs, employeurs, textes_consentement, tenant_settings.

Vidé : parcours (workflows + steps), templates de messages, conversations,
messages, dossiers (+ pieces + donnees_pro), consentements, demandes_droits,
knowledge sources/chunks, audit, webhook_deliveries, end_users,
reference_lists (l'admin les re-crée via l'UI ou import CSV).
"""
from __future__ import annotations

import asyncio

from sqlalchemy import text

from app.core.database import AsyncSessionLocal as async_session_maker


TABLES_TO_WIPE = [
    # Enfants d'abord
    "messages",
    "conversations",
    "end_users",
    "pieces_identite",
    "donnees_pro",
    "dossiers",
    "workflow_steps",
    "workflows",
    "message_template_history",
    "message_templates",
    "knowledge_chunks",
    "knowledge_sources",
    "audit_logs",
    "webhook_deliveries",
    "consentements",
    "demandes_droits",
    "tenant_setting_history",
    "reference_lists",
]


async def main():
    async with async_session_maker() as db:
        # TRUNCATE CASCADE pour balayer les FK
        joined = ", ".join(TABLES_TO_WIPE)
        await db.execute(text(f"TRUNCATE {joined} RESTART IDENTITY CASCADE"))
        await db.commit()
        print(f"OK : {len(TABLES_TO_WIPE)} tables vidées.")
        for t in TABLES_TO_WIPE:
            res = await db.execute(text(f"SELECT COUNT(*) FROM {t}"))
            print(f"  - {t}: {res.scalar()} lignes")


if __name__ == "__main__":
    asyncio.run(main())
