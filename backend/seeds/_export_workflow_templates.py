"""Exporte les 191 templates workflow.* depuis la BD locale vers un fichier
SQL idempotent (INSERT ... ON CONFLICT DO UPDATE), à jouer sur la BD de prod.

Usage :
    python backend/seeds/_export_workflow_templates.py > backend/seeds/patch_prod_all_templates.sql
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(BACKEND_ROOT / ".env")

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from app.core.config import settings  # noqa: E402


def _sql_quote(s: str) -> str:
    """Échappe une chaîne pour l'inclure entre `E'…'` (mode escape SQL)."""
    return s.replace("\\", "\\\\").replace("'", "''").replace("\n", "\\n").replace("\r", "\\r")


HEADER = """-- ============================================================================
-- Patch — synchronise TOUS les templates workflow.* (Inscription + Consultation
-- + Mise à jour + Chat libre) sur la BD de prod.
--
-- Idempotent : INSERT ... ON CONFLICT DO UPDATE.
-- Usage :
--   docker cp patch_prod_all_templates.sql ma2e_postgres:/tmp/
--   docker exec -i ma2e_postgres psql -U vai -d virtual_ai -f /tmp/patch_prod_all_templates.sql
-- ============================================================================

BEGIN;

DO $$
DECLARE
    v_tenant_id UUID;
BEGIN
    SELECT id INTO v_tenant_id FROM tenants WHERE slug = 'ma2e' LIMIT 1;
    IF v_tenant_id IS NULL THEN
        RAISE EXCEPTION 'Tenant MA2E introuvable (slug=ma2e)';
    END IF;

"""

FOOTER = """
    -- Correction menu welcome (hint dynamique)
    UPDATE message_templates
       SET content = REPLACE(content, 'Répondez par 1, 2, 3 ou 4.',
                             'Tapez le *numéro* correspondant à votre choix.'),
           updated_at = now()
     WHERE tenant_id = v_tenant_id AND code = 'workflow.welcome';

    -- Meta switch sur redirect_modify
    UPDATE workflow_steps
       SET meta = jsonb_set(COALESCE(meta, '{}'::jsonb),
                            '{switch_to_step}',
                            '"update_ask_matricule"'::jsonb),
           updated_at = now()
     WHERE code = 'redirect_modify';

    -- Positions des workflows
    UPDATE workflows SET position = 10 WHERE name = 'Inscription sociétaire MA2E';
    UPDATE workflows SET position = 20 WHERE name = 'Consultation de dossier';
    UPDATE workflows SET position = 30 WHERE name = 'Mise à jour de dossier';
    UPDATE workflows SET position = 40 WHERE name = 'Chat libre — Questions / FAQ';

    RAISE NOTICE 'Patch complet appliqué pour tenant % (MA2E)', v_tenant_id;
END $$;

-- Vérif finale (workflows n'a pas de tenant_id, mono-tenant à ce niveau)
SELECT w.name, w.position,
       COUNT(DISTINCT s.id) AS steps,
       COUNT(DISTINCT mt.id) AS templates_ok
  FROM workflows w
  LEFT JOIN workflow_steps s ON s.workflow_id = w.id
  LEFT JOIN message_templates mt
         ON mt.code = COALESCE(s.template_code, 'workflow.' || s.code)
 GROUP BY w.name, w.position
 ORDER BY w.position;

COMMIT;
"""


async def main() -> None:
    engine = create_async_engine(settings.database_url, echo=False)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as db:
        # DISTINCT ON pour dédupliquer par (code, language) — garde la plus récente.
        # La BD locale a accumulé des copies au fil des re-seeds ; en prod on ne
        # veut qu'une seule entrée par (tenant, code, language) (unique constraint).
        rows = (await db.execute(text(
            "SELECT DISTINCT ON (code, language) "
            "       code, language, content, channel::text "
            "FROM message_templates "
            "WHERE code LIKE 'workflow.%' AND is_active = true "
            "ORDER BY code, language, updated_at DESC"
        ))).all()
    await engine.dispose()

    out = [HEADER]
    out.append("    INSERT INTO message_templates")
    out.append("        (id, tenant_id, code, language, content, channel, "
               "version, is_active)")
    out.append("    VALUES")
    values = []
    for code, lang, content, channel in rows:
        values.append(
            f"        (gen_random_uuid(), v_tenant_id, '{code}', '{lang}', "
            f"E'{_sql_quote(content)}', '{channel}', 1, true)"
        )
    out.append(",\n".join(values))
    out.append("    ON CONFLICT (tenant_id, code, language) DO UPDATE")
    out.append("        SET content = EXCLUDED.content, updated_at = now();")
    out.append(FOOTER)

    out_path = BACKEND_ROOT / "seeds" / "patch_prod_all_templates.sql"
    out_path.write_text("\n".join(out), encoding="utf-8")
    print(f"[ok] {out_path}  ({len(rows)} templates)")


if __name__ == "__main__":
    asyncio.run(main())
