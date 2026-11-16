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

- **Longueur des matricules commune à toutes les entités du groupe** : nombre de caractères **minimum / maximum** (ex. entre 3 et 5), réglé par l'admin au-dessus de la liste dans *Listes de valeurs → Employeurs du groupe → Éditer*. Matricules alphanumériques ou entièrement numériques, sans distinction. Stocké dans `reference_lists.config` de cette liste (bootstrap) ; changement journalisé dans l'audit. Les anciennes règles par employeur (expression régulière, exemple) ne sont plus utilisées.
- Contrôle sur le matricule **normalisé** (majuscules, sans espace/tiret), zéros de tête comptés. Sans intervalle : aucun contrôle.
- Appliqué : ajout unitaire au référentiel (422), import du référentiel (ligne rejetée avec message), chat d'inscription (matricule hors référentiel de mauvaise longueur → on redemande), import de la base MA2E (**avertissement** dans le rapport, le sociétaire est importé quand même).
- Intervalle refusé à l'enregistrement si min > max ou hors 1–64.
- Liste « Employeurs du groupe » : du **plus récent (en haut) au plus ancien (en bas)** (date d'ajout par employeur) ; CIPREL ajouté. Ajouter un employeur à la liste le crée dans la table des employeurs ; le retirer le **désactive** (jamais supprimé).
- Consultation / mise à jour : un matricule numérique est retrouvé malgré les zéros de tête (`6` = `06` = `00006`).
- Le matricule d'un collaborateur existant n'est pas modifiable dans l'application (pas de contrôle à ajouter).

## Reste à faire

- **07** — WhatsApp sur le nouveau numéro (+225 07 87 84 14 07) ; nécessite MinIO pour les photos.
- MinIO non installé en local : photo / signature de la fiche et téléversement des pièces non testés.
- Ayants droit (jusqu'à 4 avec contacts) : nécessite une table dédiée.
- Pas d'écran d'import dans le frontend (import via l'API / Swagger).
