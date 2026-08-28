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


# F-12 — Trigger PostgreSQL append-only sur audit_logs.
# La reco pentest v1.0 exige : "Traiter la piste d'audit comme strictement
# immuable, sans exception de rôle."
# Bloquer côté application ne suffit pas — un DBA ou un compte compromis
# avec accès psql direct pourrait DELETE FROM audit_logs. On installe donc
# une défense au niveau BDD qui RAISE EXCEPTION sur tout UPDATE, DELETE
# ou TRUNCATE.
AUDIT_APPEND_ONLY_SQL = """
CREATE OR REPLACE FUNCTION ma2e_audit_append_only() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'audit_logs is append-only: % operation is forbidden (F-12)',
        TG_OP USING ERRCODE = 'insufficient_privilege';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS ma2e_audit_no_update ON audit_logs;
DROP TRIGGER IF EXISTS ma2e_audit_no_delete ON audit_logs;
DROP TRIGGER IF EXISTS ma2e_audit_no_truncate ON audit_logs;

CREATE TRIGGER ma2e_audit_no_update
    BEFORE UPDATE ON audit_logs
    FOR EACH ROW EXECUTE FUNCTION ma2e_audit_append_only();

CREATE TRIGGER ma2e_audit_no_delete
    BEFORE DELETE ON audit_logs
    FOR EACH ROW EXECUTE FUNCTION ma2e_audit_append_only();

CREATE TRIGGER ma2e_audit_no_truncate
    BEFORE TRUNCATE ON audit_logs
    FOR EACH STATEMENT EXECUTE FUNCTION ma2e_audit_append_only();
"""


async def bootstrap_db() -> None:
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
        # F-12 — pose le trigger append-only sur audit_logs
        await conn.execute(text(AUDIT_APPEND_ONLY_SQL))
        log.info("✅ audit_logs append-only trigger installé (F-12)")
    await engine.dispose()
    log.info("✅ Database bootstrap complete.")


if __name__ == "__main__":
    asyncio.run(bootstrap_db())
