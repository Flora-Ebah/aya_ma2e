# MA2E — Point d'avancement backlog v5 (09/11/2026)

Les tâches 01 à 06 du backlog v5 sont livrées dans `aya_ma2e-main` et testées ; 07 reste à faire.
**Rien n'est encore commité** (le dossier n'est pas un dépôt git).

## Fait

| # | Tâche | Ce qui a été livré | Fichiers principaux |
|---|---|---|---|
| 01 | Import du fichier Excel source | `POST /api/imports/societaires` (admin) : .xlsx/.csv, mode simulation `?dry_run=true`, upsert sur `id_client` (ré-import sans doublon), une ligne invalide est rejetée sans bloquer les autres, rapport créés / mis à jour / rejetés, limite 50 Mo | `services/societaire_import.py`, `services/importer_service.py`, `api/imports.py` |
| 02 | Table sociétaires indexée | Table `societaires` : index matricule, ID client, code client, CNI, téléphone, nom ; colonnes normalisées pour la recherche ; les 56 colonnes source conservées dans `extra` | `models/societaire.py` |
| 03 | Vérification de statut | Parcours « Consulter mon dossier » branché sur la base importée : recherche par matricule, ID client, code client ou CNI ; affiche prénom + initiale, statut, employeur, date d'adhésion (pas de données sensibles) | `conversation/societaire_actions.py` |
| 04 | Mise à jour de compte | Parcours « Modifier mes informations » : vérification d'identité par date de naissance, puis 12 champs du formulaire papier (email, téléphone, domicile, BP, situation, conjoint, nom de la mère, fonction, catégorie, employeur, personne à prévenir, consentement) ; historique de l'ancienne valeur + audit | `conversation/societaire_actions.py` |
| 05 | Fiche sociétaire PDF | Correction d'un crash (HTTP 500 avec pypdf 7) ; mise en page alignée sur la fiche Perfect Vision de référence ; nom / date / n° pièce repris de l'OCR si non saisis ; photo et signature recadrées | `services/fiche_pdf.py` |

Corrections au passage : catégorie professionnelle lue uniquement dans `CATEGORIE(1)` (et non « Individu ») ;
réglage optionnel `MINIO_REGION` (évite ~18 s d'attente par fiche quand MinIO est injoignable).

## Tests automatiques

- Nouveau : `tests/test_societaire_import.py` — 75 vérifications (normalisation, mapping des 56 colonnes,
  rejets / doublons / créés vs mis à jour, simulation sans écriture, lots de 500, .xlsx réel, limites de taille, accès admin).
- Vérifié qu'ils détectent bien les erreurs : 3 bugs introduits volontairement, tous détectés.
- Les 12 fichiers de tests du projet passent (les 11 existants + le nouveau).
- Lancer : `cd backend` puis `python -m tests.test_societaire_import`

## Appliquer sur une base existante

1. `python -m app.bootstrap` (crée la table `societaires` et ses nouvelles colonnes)
2. `python seeds/patch_consultation_societaires.py --activate` (tâche 03)
3. `python seeds/patch_update_societaires.py --activate` (tâche 04)

Les scripts sont rejouables et n'écrasent pas un message personnalisé dans le back-office.
`--activate` active le parcours (inactif par défaut).

## À valider ensemble

- **Employeur** : pris dans `type_client` quand `EMPLOYEUR(2)` est vide — à confirmer avec MA2E.
- **Données source** : n° de pièce parfois égal au matricule ou au code client ; seul le 1er téléphone d'une cellule est cherchable.
- **Sécurité mise à jour** : la date de naissance peut se deviner, pas de blocage après plusieurs échecs (limite globale 60 requêtes / 5 min). Un code SMS/WhatsApp serait plus sûr.
- **RIB** retiré du menu de mise à jour (stockage en clair non souhaitable).
- **Consentement** (choix 12) : OUI/NON + audit, pas le texte ARTCI versionné de l'inscription.
- **Parcours d'inscription** : non modifié. Le seed local est une version réduite ; la version complète (Q1–Q23) n'existe qu'en base, pas dans le dépôt.

## Tâche 06 — matricule à format variable

- Chaque employeur peut avoir un **format de matricule** (expression régulière + exemple), géré dans *Listes de valeurs → Employeurs du groupe → Éditer* (sous chaque employeur : format, exemple et champ de test). Colonnes `employeurs.matricule_format` / `matricule_exemple`, créées au démarrage (`bootstrap`).
- Le format s'applique au matricule **normalisé** (majuscules, sans espace/tiret) et doit correspondre en entier. Sans format : aucun contrôle (comportement d'avant).
- Appliqué : ajout unitaire au référentiel (422), import CSV/XLSX du référentiel (ligne rejetée avec message), chat d'inscription (matricule absent du référentiel et ne respectant aucun format → on redemande, avec des exemples).
- Consultation / mise à jour : un matricule numérique est retrouvé malgré les zéros de tête (`6` = `06` = `00006`) ; en cas de doublon la réponse « ambigu » est conservée.
- Format refusé à l'enregistrement s'il est invalide, trop long ou à risque (quantificateurs imbriqués) ; l'exemple doit respecter le format.
- Non fait : la règle n'est pas appliquée à l'import de la base MA2E (Perfect Vision) ni à la modification d'un matricule existant.

## Reste à faire

- **07** — WhatsApp sur le nouveau numéro (+225 07 87 84 14 07) ; nécessite MinIO pour les photos.
- MinIO non installé en local : photo / signature de la fiche et téléversement des pièces non testés.
- Ayants droit (jusqu'à 4 avec contacts) : nécessite une table dédiée.
- Pas d'écran d'import dans le frontend (import via l'API / Swagger).
