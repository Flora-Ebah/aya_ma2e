-- =========================================================================
--  Patch prod F-12 — Piste d'audit strictement immuable au niveau BDD.
--
--  Le rapport pentest v1.0 (rec. F-12) exige de traiter la piste d'audit
--  comme append-only, SANS EXCEPTION DE RÔLE. Le seal RBAC côté application
--  couvre déjà les rôles opérationnels, mais un accès psql direct (DBA,
--  compte compromis, backup restoré ailleurs) pouvait contourner cette
--  garantie. Ce patch pose une défense en profondeur au niveau du moteur
--  PostgreSQL : trois triggers refusent tout UPDATE, DELETE, TRUNCATE.
--
--  Idempotent : DROP TRIGGER IF EXISTS + CREATE OR REPLACE FUNCTION.
--  Rejouable sans effet secondaire.
--
--  ⚠️  L'utilisateur qui exécute ce script doit avoir le privilège
--      CREATE TRIGGER sur audit_logs (rôle propriétaire de la table
--      ou super-utilisateur PostgreSQL).
-- =========================================================================

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

-- =========================================================================
--  Vérifications post-patch
-- =========================================================================

-- 1) Les 3 triggers sont bien en place
SELECT tgname AS trigger_name, tgenabled AS enabled,
       CASE
           WHEN tgtype & 2 = 2 THEN 'BEFORE'
           ELSE 'AFTER'
       END AS timing,
       CASE
           WHEN tgtype & 4 = 4 THEN 'INSERT'
           WHEN tgtype & 8 = 8 THEN 'DELETE'
           WHEN tgtype & 16 = 16 THEN 'UPDATE'
           WHEN tgtype & 32 = 32 THEN 'TRUNCATE'
       END AS event
FROM pg_trigger
WHERE tgrelid = 'audit_logs'::regclass
  AND tgname LIKE 'ma2e_audit_no_%'
ORDER BY tgname;

-- 2) Test à ne PAS exécuter en prod (juste pour illustration) :
--    Ces deux commandes doivent lever une erreur ERRCODE 42501.
--
--    DELETE FROM audit_logs WHERE id = (SELECT id FROM audit_logs LIMIT 1);
--    → ERROR: audit_logs is append-only: DELETE operation is forbidden (F-12)
--
--    UPDATE audit_logs SET details = '{}' WHERE id = ...;
--    → ERROR: audit_logs is append-only: UPDATE operation is forbidden (F-12)
