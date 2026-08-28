-- ============================================================================
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


    INSERT INTO message_templates
        (id, tenant_id, code, language, content, channel, version, is_active)
    VALUES
        (gen_random_uuid(), v_tenant_id, 'workflow.anonyme_flow', 'fr', E'Votre matricule n''a pas été reconnu dans notre référentiel.\n\nMerci de contacter le support MA2E ({support_phone} · {support_email}) pour finaliser votre inscription manuellement.', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.ask_ayant_droit', 'fr', E'👪 *Q21 — Indiquez votre/vos ayant(s) droit*\n_(séparez par des virgules s''il y en a plusieurs)_', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.ask_boite_postale', 'fr', E'📮 *Q12 — Sélectionnez la boîte postale de votre société :*\n\n{boites_postales_list}', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.ask_categorie', 'fr', E'🏷️ *Q22 — Votre catégorie ?*\n\n1️⃣ CADRE SUPÉRIEUR\n2️⃣ CADRE\n3️⃣ MAÎTRISE SUPÉRIEURE\n4️⃣ M1-M2\n5️⃣ EO', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.ask_civilite', 'fr', E'👤 *Q1 — Votre civilité ?*\n\n1️⃣ M.\n2️⃣ Mme\n3️⃣ Mlle', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.ask_cni_recto', 'fr', E'📷 *Q10 — Copie de votre pièce d''identité*\n\nEnvoyez d''abord une *photo nette du recto*.\n\n_Formats acceptés : JPG, PNG, PDF, Word._\n_Taille max : 100 Mo._', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.ask_cni_verso', 'fr', E'📷 À présent, le *verso* de votre pièce d''identité.\n_La zone MRZ (lignes en bas) doit être bien nette._', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.ask_consent_artci', 'fr', E'🛑 *PORTE 1/3 — Protection de vos données*\n_(Loi 2013-450 ARTCI)_\n\nMA2E collecte vos données d''identité, professionnelles et votre pièce d''identité pour gérer votre adhésion.\n\n• Données chiffrées · Conservation : adhésion + 5 ans\n• Vos droits : tapez *DROITS*\n• Recours ARTCI : www.artci.ci\n\n*Acceptez-vous ?*\n\n1️⃣ Oui, j''accepte\n2️⃣ Non, je refuse', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.ask_contact1_prev', 'fr', E'📞 *Q19 — 1er contact (téléphone) de la personne à prévenir ?*', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.ask_contact2_prev', 'fr', E'📞 *Q20 — 2e contact de la personne à prévenir ?*\n_(optionnel — tapez * pour passer)_', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.ask_date_naissance', 'fr', E'📅 *Q6 — Votre date de naissance ?*\n_(format JJ/MM/AAAA, ex. 12/04/1985)_', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.ask_direction_service', 'fr', E'🏗️ *Q11 — Votre Direction / Service / Exploitation ?*', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.ask_email', 'fr', E'📧 *Q15 — Votre adresse email ?*\n_Un code à 6 chiffres y sera envoyé pour vérification._', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.ask_employeur', 'fr', E'🏢 *Q2 — Quelle est votre société ?*\n\n{employeurs_list}', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.ask_fonction', 'fr', E'Quelle est votre *fonction* au sein de l''entreprise ?', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.ask_lieu_naissance', 'fr', E'🏙️ *Q7 — Votre lieu de naissance ?*', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.ask_matricule', 'fr', E'Merci ! Pour vous identifier, saisissez votre *matricule employeur* (6 à 10 caractères alphanumériques).', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.ask_nom', 'fr', E'*Q3 — Votre nom de famille ?*', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.ask_nom_conjoint', 'fr', E'👨‍👩 *Q17 — Nom de votre conjoint(e) ?*\n_(laissez vide ou tapez * si non applicable)_', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.ask_nom_mere', 'fr', E'🔐 *Q23 — Nom de jeune fille de votre mère ?*\n_(question de sécurité — KYC)_', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.ask_nom_personne_prev', 'fr', E'🚨 *Q18 — Nom de la personne à prévenir en cas d''urgence ?*', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.ask_numero_piece', 'fr', E'*Q9 — Quel est le numéro inscrit sur votre pièce d''identité ?*', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.ask_otp_code', 'fr', E'🔐 Saisissez le *code à 6 chiffres* reçu par email.', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.ask_prenoms', 'fr', E'*Q4 — Vos prénoms ?*', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.ask_profession', 'fr', E'💼 *Q16 — Quelle est votre profession ?*', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.ask_situation_matri', 'fr', E'*Q5 — Votre situation matrimoniale ?*\n\n1️⃣ Célibataire\n2️⃣ Marié(e)\n3️⃣ Divorcé(e)\n4️⃣ Veuf / Veuve', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.ask_telephone1', 'fr', E'📞 *Q13 — Votre téléphone principal ?*\n_(avec indicatif, ex. +225 07 00 00 00 00)_', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.ask_telephone2', 'fr', E'📞 *Q14 — Un second téléphone ?* _(optionnel — tapez * pour passer)_', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.ask_type_piece', 'fr', E'*Q8 — Quel type de pièce d''identité avez-vous ?*\n\n1️⃣ Carte Nationale d''Identité (CNI)\n2️⃣ Passeport\n3️⃣ Attestation d''identité', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.ask_what_to_correct', 'fr', E'✏️ *Que souhaitez-vous corriger ?*\n\n1️⃣ Mon *nom*\n2️⃣ Mes *prénoms*\n3️⃣ Mon *numéro de pièce*\n4️⃣ Ma *date de naissance*\n5️⃣ Reprendre les *photos* (recto + verso)\n6️⃣ Annuler — revenir à la vérification', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.chat_ask_more', 'fr', E'Souhaitez-vous poser une autre question ?\n1️⃣ *Oui*  2️⃣ *Non, terminer*', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.chat_ask_question', 'fr', E'Quelle est votre question ? (tapez *FIN* pour terminer)', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.chat_end', 'fr', E'Merci d''avoir utilisé l''assistante MA2E. À bientôt ! Pour toute urgence, contactez {support_phone}.', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.chat_welcome', 'fr', E'💬 *Espace questions libres*\n\nPosez-moi vos questions sur MA2E : adhésion, prestations, garanties, contact… Je puise dans la base de connaissances officielle.', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.completion', 'fr', E'🎉 *Inscription validée !*\n\n📋 Référence de votre dossier : *{dossier_number}*\n\nVous recevrez un email de confirmation avec votre numéro de sociétaire dès la validation finale par un agent MA2E.\n\n🙏 *Merci de votre confiance et bienvenue chez MA2E !*', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.confirm_ocr', 'fr', E'🛑 *PORTE 2/3 — Confrontation saisie ↔ pièce d''identité*\n\n{data_match_summary}\n\n*Vos informations saisies sont-elles correctes ?*\n\n1️⃣ Oui, je confirme ma saisie\n2️⃣ Non, je veux corriger', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.consent_refused', 'fr', E'Sans votre consentement, l''inscription ne peut pas se poursuivre.\n\nPour toute question : {support_email} · {support_phone}\nVos droits : tapez *DROITS*.', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.consult_ask_action', 'fr', E'Que souhaitez-vous faire ?\n\n1️⃣ *Terminer*\n2️⃣ *Modifier mes informations*', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.consult_ask_matricule', 'fr', E'Saisissez votre *matricule employeur* (6 à 10 caractères alphanumériques).', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.consult_end', 'fr', E'Merci ! N''hésitez pas à me solliciter si besoin. Tapez *MENU* pour revenir au point de départ.', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.consult_not_found', 'fr', E'❌ Aucun dossier trouvé pour ce matricule.\n\nSi vous n''êtes pas encore inscrit, tapez *INSCRIPTION* pour démarrer.', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.consult_show_status', 'fr', E'📋 *Votre dossier MA2E*\n\n• N° dossier : {dossier_number}\n• Statut : *{status_label}*\n• Soumis le : {submitted_date}\n• Dernière mise à jour : {updated_date}', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.consult_welcome', 'fr', E'🔍 *Consultation de votre dossier*\n\nJe vais vous donner l''état actuel de votre adhésion MA2E.', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.correct_date_naissance', 'fr', E'✏️ Tapez votre *date de naissance corrigée* (format JJ/MM/AAAA) :', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.correct_nom', 'fr', E'✏️ Tapez votre *nom corrigé* :', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.correct_numero_piece', 'fr', E'✏️ Tapez le *numéro corrigé* de votre pièce d''identité :', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.correct_prenoms', 'fr', E'✏️ Tapez vos *prénoms corrigés* :', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.duplicate_detected', 'fr', E'⚠️ *Un dossier existe déjà pour votre matricule.*\n\nInutile de saisir à nouveau toutes vos informations — votre dossier est déjà dans notre système.\n\n👉 Pour le *consulter*, tapez *MENU* puis choisissez l''option *2*.\n👉 Pour le *mettre à jour*, tapez *MENU* puis choisissez l''option *3*.\n👉 Pour toute autre question : {support_email} · {support_phone}', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.final_certification', 'fr', E'🛑 *PORTE 3/3 — Certification sur l''honneur*\n\nAvant la création de votre dossier, je certifie sur l''honneur l''exactitude de l''ensemble des informations fournies.\n\n_Toute fausse déclaration peut entraîner le rejet de l''adhésion (loi 2013-546)._\n\n*Confirmez-vous ?*\n\n1️⃣ Oui, je certifie\n2️⃣ Non, annuler', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.handoff_chat', 'fr', E'💬 *Espace questions libres*\n\nPosez-moi votre question sur MA2E (adhésion, prestations, garanties…).\n\n_Tapez *MENU* à tout moment pour revenir au choix initial._', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.handoff_consultation', 'fr', E'🔍 *Consultation de votre dossier*\n\nSaisissez votre *matricule employeur* pour que je retrouve votre dossier.', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.handoff_modification', 'fr', E'✏️ *Mise à jour de vos informations*\n\nSaisissez d''abord votre *matricule employeur*.', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.manual_review', 'fr', E'📋 *Vos informations ont bien été reçues.*\n\nUn agent MA2E va examiner manuellement votre dossier et vous recontactera sous 48h pour finaliser votre inscription.\n\n_Merci de votre patience et de votre compréhension._', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.redirect_modify', 'fr', E'Très bien — je vous bascule vers le parcours de mise à jour. Tapez votre matricule à nouveau.', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.update_ask_matricule', 'fr', E'Pour retrouver votre dossier, saisissez votre *matricule employeur*.', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.update_ask_new_value', 'fr', E'Saisissez la *nouvelle valeur* pour ce champ.', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.update_choose_field', 'fr', E'Quel champ souhaitez-vous modifier ?\n\n1️⃣ Email\n2️⃣ Téléphone\n3️⃣ Adresse postale\n4️⃣ Situation familiale\n5️⃣ Coordonnées bancaires', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.update_confirm', 'fr', E'✅ Modification enregistrée.\n\nUne autre modification ?\n1️⃣ *Oui*  2️⃣ *Non, terminer*', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.update_end', 'fr', E'Merci ! Vos modifications ont été transmises. Un agent revalidera votre dossier si nécessaire.', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.update_not_found', 'fr', E'❌ Aucun dossier trouvé pour ce matricule. Veuillez d''abord vous inscrire (tapez *INSCRIPTION*).', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.update_welcome', 'fr', E'✏️ *Mise à jour de votre dossier MA2E*\n\nJe vais vous aider à modifier vos informations personnelles.', 'any_', 1, true),
        (gen_random_uuid(), v_tenant_id, 'workflow.welcome', 'fr', E'👋 *Bienvenue chez MA2E !*\n\nJe suis {assistant_name}, votre assistante d''identification.\n\n*Que souhaitez-vous faire ?*\n\n{parcours_list}\n\n_Tapez le *numéro* correspondant à votre choix._', 'any_', 1, true)
    ON CONFLICT (tenant_id, code, language) DO UPDATE
        SET content = EXCLUDED.content, updated_at = now();

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
