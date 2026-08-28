-- =========================================================================
--  Patch prod F-06 — Ajoute le step verify_data_vs_ocr entre ocr_extract et
--  confirm_ocr dans le workflow "Inscription sociétaire MA2E".
--
--  À jouer une fois par tenant qui a le workflow déployé.
--
--  Idempotent : le INSERT utilise ON CONFLICT DO NOTHING sur (workflow_id, code).
--  Le UPDATE ocr_extract.next_step_code est répétable sans effet secondaire.
-- =========================================================================

DO $$
DECLARE
    v_wf_id           uuid;
    v_step_exists     boolean;
    v_next_updated    integer := 0;
BEGIN
    -- 1) Trouver TOUS les workflows Inscription MA2E (un par tenant).
    FOR v_wf_id IN
        SELECT id
        FROM workflows
        WHERE name = 'Inscription sociétaire MA2E'
    LOOP
        -- 2) Vérifier si le step existe déjà
        SELECT EXISTS (
            SELECT 1 FROM workflow_steps
            WHERE workflow_id = v_wf_id AND code = 'verify_data_vs_ocr'
        ) INTO v_step_exists;

        IF NOT v_step_exists THEN
            INSERT INTO workflow_steps (
                id, workflow_id, code, label, type, template_code,
                action_name, next_step_code, branches, position,
                validation_rules, prompt_variables
            ) VALUES (
                gen_random_uuid(),
                v_wf_id,
                'verify_data_vs_ocr',
                'Comparaison saisie ↔ OCR (F-06)',
                'action',              -- WorkflowStepType.action
                NULL,                  -- action pure, pas de template
                'verify_user_data_vs_ocr',
                'confirm_ocr',         -- next par défaut si aucune branche ne matche
                jsonb_build_object(
                    'match',         'confirm_ocr',
                    'partial_match', 'confirm_ocr',
                    'mismatch',      'manual_review'
                ),
                105,                   -- entre ocr_extract (100) et confirm_ocr (110)
                '{}'::jsonb,
                '{}'::jsonb
            );
            RAISE NOTICE 'Step verify_data_vs_ocr inséré pour workflow %', v_wf_id;
        ELSE
            RAISE NOTICE 'Step verify_data_vs_ocr déjà présent pour workflow % — skip', v_wf_id;
        END IF;

        -- 3) Rebrancher ocr_extract → verify_data_vs_ocr
        UPDATE workflow_steps
        SET next_step_code = 'verify_data_vs_ocr'
        WHERE workflow_id = v_wf_id
          AND code = 'ocr_extract'
          AND next_step_code <> 'verify_data_vs_ocr';

        GET DIAGNOSTICS v_next_updated = ROW_COUNT;
        IF v_next_updated > 0 THEN
            RAISE NOTICE 'ocr_extract.next_step_code mis à jour pour workflow %', v_wf_id;
        END IF;
    END LOOP;
END $$;

-- =========================================================================
--  Vérifications post-patch
-- =========================================================================

-- 1) Le nouveau step est bien câblé (attendu : 1 ligne par tenant)
SELECT w.name AS workflow, s.code, s.type, s.action_name,
       s.next_step_code, s.branches, s.position
FROM workflow_steps s
JOIN workflows w ON w.id = s.workflow_id
WHERE s.code = 'verify_data_vs_ocr'
ORDER BY w.name;

-- 2) ocr_extract pointe désormais vers verify_data_vs_ocr
SELECT w.name AS workflow, s.code, s.next_step_code
FROM workflow_steps s
JOIN workflows w ON w.id = s.workflow_id
WHERE s.code = 'ocr_extract'
ORDER BY w.name;
