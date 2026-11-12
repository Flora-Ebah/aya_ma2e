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


SOCIETAIRES_LATE_COLUMNS = [
    ("boite_postale", "VARCHAR(128)"),
    ("nom_conjoint", "VARCHAR(255)"),
    ("personne_a_prevenir", "VARCHAR(255)"),
]


# Lien dossier <-> sociétaire importé (create_all ne modifie pas la table `dossiers` existante)
# Valeurs ajoutées à l'énumération d'audit APRÈS coup : create_all ne modifie pas un type PostgreSQL existant.
AUDIT_LATE_ENUM_VALUES = ["referentiel_added", "referentiel_updated", "referentiel_removed"]

DOSSIERS_LATE_DDL = [
    "ALTER TABLE employeurs ADD COLUMN IF NOT EXISTS matricule_format VARCHAR(120)",
    "ALTER TABLE employeurs ADD COLUMN IF NOT EXISTS matricule_exemple VARCHAR(64)",
    "ALTER TABLE dossiers ADD COLUMN IF NOT EXISTS societaire_id UUID REFERENCES societaires(id) ON DELETE SET NULL",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_dossiers_societaire_id ON dossiers (societaire_id)",
]


def _split_sql(sql: str) -> list[str]:
    """Découpe un bloc SQL en statements individuels — asyncpg refuse les
    multi-commandes dans un prepared statement. On respecte les corps
    PL/pgSQL encadrés par $$...$$."""
    out: list[str] = []
    buf: list[str] = []
    in_dollar = False
    for line in sql.splitlines():
        if "$$" in line:
            in_dollar = not in_dollar if line.count("$$") % 2 else in_dollar
        buf.append(line)
        if not in_dollar and line.rstrip().endswith(";"):
            stmt = "\n".join(buf).strip()
            if stmt:
                out.append(stmt)
            buf = []
    tail = "\n".join(buf).strip()
    if tail:
        out.append(tail)
    return out


async def bootstrap_db() -> None:
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
        # create_all ne modifie pas les tables existantes : colonnes ajoutées après coup (idempotent)
        for col, typ in SOCIETAIRES_LATE_COLUMNS:
            await conn.execute(text(f"ALTER TABLE societaires ADD COLUMN IF NOT EXISTS {col} {typ}"))
        for stmt in DOSSIERS_LATE_DDL:
            await conn.execute(text(stmt))
        for value in AUDIT_LATE_ENUM_VALUES:
            await conn.execute(text(f"ALTER TYPE audit_action ADD VALUE IF NOT EXISTS '{value}'"))
        # F-12 — pose le trigger append-only sur audit_logs
        for stmt in _split_sql(AUDIT_APPEND_ONLY_SQL):
            await conn.execute(text(stmt))
        log.info("✅ audit_logs append-only trigger installé (F-12)")
    await engine.dispose()
    log.info("✅ Database bootstrap complete.")


if __name__ == "__main__":
    asyncio.run(bootstrap_db())
