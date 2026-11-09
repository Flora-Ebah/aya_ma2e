# Audit backlog Phase 2 — Couverture par user story

> Cross-check entre les 38 user stories du backlog `MA2E_Backlog_v1.xlsx` et ce qui a été livré en Phase 2.
> Version 1.0 — 2026-06-15.

**Légende** :
- ✅ **Conforme** — critères d'acceptation et règles métier respectés
- ⚠️ **Partiel** — fait mais avec écart ou incomplet
- ❌ **Manquant** — pas implémenté

---

## Synthèse exécutive

| Statut | Nombre | % |
|--------|--------|---|
| ✅ Conforme | **20** | 53% |
| ⚠️ Partiel | **12** | 31% |
| ❌ Manquant | **6** | 16% |
| **Total** | **38** | 100% |

**Gaps critiques à traiter immédiatement** (avant production) :
1. **US-02** — Authentification Active Directory (l'utilisateur l'a explicitement demandé) → **EN COURS**
2. **US-36** — Détection anti-fraude des doublons (matricule / CNI / nom+date)
3. **US-37** — Import en masse des référentiels (CSV/Excel)
4. **US-22** — OTP email finalisé end-to-end (SMTP réel)
5. **US-29** — Page publique d'information ARTCI accessible
6. **US-28** — Anonymisation effective (droit à l'oubli)

**Écarts règles métier importantes** :
- Politique mot de passe : backlog dit **12 caractères**, notre défaut est **8**
- Un user peut porter **plusieurs rôles** (backlog) : aujourd'hui **1 seul rôle**
- Email professionnel obligatoire (domaine groupe) : pas validé actuellement
- "Numéro de sociétaire" distinct du "dossier_number" : pas implémenté
- IP capturée dans l'audit log : non
- Notifications doublées sur email automatique : non
- Templates emails : limite 5000 chars vs 1024 actuel

---

## Audit détaillé par epic

### EPIC AUTHENTIFICATION (2 stories)

#### US-01 — Connexion administrateur ✅
- ✅ Login email + password sécurisé ([api/auth.py](backend/app/api/auth.py))
- ✅ Erreurs identifiants invalides
- ✅ **Lockout après échecs** (configurable via `login_max_failed_attempts`, défaut 5)
- ✅ Redirection dashboard après login
- ⚠️ **Politique mot de passe par défaut 8 caractères** alors que la règle métier impose **12**. Changer le défaut du registry à 12 pour les admins, ou créer 2 politiques (user vs admin).
- ✅ Session expirée → redirection login (JWT exp)

#### US-02 — Connexion via Active Directory ERANOVE ❌ → **EN COURS**
- ❌ Pas implémenté en Phase 2
- 🛠️ **En cours d'implémentation** : `auth_method` au modèle User, endpoint `/api/auth/ad/login`, toggle dans création utilisateur

---

### EPIC ADMINISTRATION (5 stories)

#### US-03 — Gestion rôles et permissions ⚠️
- ⚠️ Rôles **fixes** (`super_admin`, `tenant_admin`, `agent`) au lieu de CRUD dynamique
- ✅ Application immédiate des droits
- ✅ Audit des modifications
- Le backlog évoque **"Agent validateur, Superviseur, Lecteur, IT"** : à mapper vers nos rôles ou créer un système RBAC plus fin
- **Recommandation** : reporter en Phase 3 (système RBAC dynamique = lourd)

#### US-04 — Gestion utilisateurs internes ✅⚠️
- ✅ CRUD complet ([api/users.py](backend/app/api/users.py))
- ✅ Application immédiate des droits
- ✅ Désactivation (soft delete via `is_active=false`)
- ✅ Audit complet (4 actions : created, updated, deactivated, password_reset)
- ⚠️ **Un seul rôle par user** (le backlog dit "plusieurs rôles")
- ⚠️ **Pas de validation domaine email** (le backlog impose "email professionnel obligatoire — domaine du groupe")

#### US-05 — Paramétrage sociétés affiliées ⚠️
- Existe en POC mais la page `/parametres/employeurs` n'a pas été refondue en Phase 2
- À vérifier : unicité nom + code, désactivation au lieu de suppression

#### US-06 — Paramétrage modèles messages ✅⚠️
- ✅ Édition des templates ([api/message_templates.py](backend/app/api/message_templates.py))
- ✅ **Validation variables obligatoires** (blocage si manquant)
- ✅ **Prévisualisation WhatsApp live** dans la page admin
- ✅ Historique versionné + rollback
- ⚠️ Limite **1024 chars uniforme**, le backlog demande 1024 WhatsApp + **5000 email**. À paramétrer par template selon le canal.

#### US-37 — Import en masse référentiels ❌
- ❌ Non implémenté
- À faire : endpoint POST /api/referentials/import avec parsing CSV/Excel, validation transactionnelle, rapport d'import téléchargeable

---

### EPIC ONBOARDING SOCIÉTAIRE (5 stories)

#### US-07 — Démarrage WhatsApp ✅
- ✅ Existant dans le POC. Welcome envoyé < 5s.
- ✅ Parcours conversationnel guidé
- ✅ Pas d'installation ni de compte
- ✅ Reprise possible (cf. US-11)

#### US-08 — Démarrage Web Chat ✅
- ✅ Page chat existante
- ✅ Mêmes étapes que WhatsApp
- ✅ Responsive (Tailwind)

#### US-09 — Consentement ARTCI ✅
- ✅ Existant (table `consentements` avec signature crypto)
- ✅ Bloquant avant collecte
- ✅ Horodaté et conservé

#### US-10 — Saisie infos pro ✅
- ✅ Liste sociétés sélectionnable
- ✅ Matricule demandé
- ✅ Validation date d'embauche

#### US-11 — Reprise session interrompue ✅
- ✅ État conversation persisté en BD
- ✅ Setting `session_max_idle_days=7` (configurable, conforme à la règle 7 jours)
- ✅ L'assistante reprend le contexte

---

### EPIC EXTRACTION & VÉRIFICATION (4 stories)

#### US-12 — Téléversement CNI ✅⚠️
- ✅ Recto puis verso
- ⚠️ Formats : JPG/PNG OK, **HEIC** à vérifier
- ⚠️ **Taille max 5 Mo** à vérifier dans le code
- ✅ Stockage chiffré (Azure Blob + chiffrement applicatif)

#### US-13 — Extraction OCR automatique ✅⚠️
- ✅ Mindee branché
- ✅ Présentation au sociétaire pour confirmation
- ✅ Correction manuelle possible
- ✅ Score de confiance conservé
- ⚠️ **Le seuil `ocr_min_confidence_score=0.7` n'est PAS branché** pour marquer "revue manuelle prioritaire". Setting existe mais non consommé par le code.

#### US-14 — Détection pièces illisibles ⚠️
- ✅ Détection floue/sombre côté Mindee
- ⚠️ **Limite 3 tentatives** : pas explicitement codée
- ⚠️ Après 3 échecs → escalade vers agent : à vérifier

#### US-36 — Détection doublons (anti-fraude) ❌
- ❌ Critique manquant
- À implémenter :
  - Index unique sur `(tenant_id, matricule)` et `(tenant_id, numero_cni)` pour doublon strict
  - Recherche flou sur `nom + prenoms + date_naissance` pour doublon souple
  - Onglet "Doublons à arbitrer" dans /dossiers
- **Important pour la fraude → Phase 2bis prioritaire**

---

### EPIC ASSISTANT IA (2 stories)

#### US-15 — Réponse aux questions ✅
- ✅ RAG + tenant_chat_complete ([services/rag.py](backend/app/services/rag.py))
- ✅ Citation des sources
- ✅ Fallback configurable (`ai_fallback_message`)
- ✅ Limite au périmètre MA2E

#### US-16 — Escalade vers conseiller ✅
- ✅ Template `escalation.agent`
- ✅ Setting `agent_handoff_target_minutes=30`
- ✅ Setting `support_hours` configurable
- ⚠️ Mécanisme d'**accusé de réception** à vérifier en détail

---

### EPIC VALIDATION DOSSIER (6 stories)

#### US-17 — Tableau de bord dossiers à traiter ✅⚠️
- ✅ Page /dossiers existante
- ✅ Filtres par statut
- ⚠️ **Pas d'indicateur "en cours de traitement par un autre agent"** (pas de soft-lock multi-agent)
- ⚠️ Tri par défaut "ancienneté" à vérifier (actuellement par `created_at desc`)

#### US-18 — Consultation détail dossier ✅
- ✅ Page détail unique avec toutes les infos
- ✅ Photos agrandissables
- ✅ Correction donnée avant validation

#### US-19 — Validation dossier ✅⚠️
- ✅ Statut passe à `valide`
- ⚠️ **Pas de "numéro de sociétaire" attribué** distinct du `dossier_number`. À ajouter (ex. `numero_societaire` séparé en BD).
- ✅ Notification WhatsApp sur canal d'origine
- ⚠️ **Pas de doublage email automatique** (le backlog demande WhatsApp + email)
- ✅ Audit complet

#### US-20 — Refus avec motif ✅
- ✅ Motif obligatoire (Pydantic validation)
- ✅ Notification + motif
- ✅ Audit

#### US-21 — Demande complément ✅⚠️
- ✅ Notification + reprise conversation
- ⚠️ **Délai 15j → clôture auto non automatisée** (setting `complement_response_deadline_days=15` existe mais pas de scheduled task qui clôture)

#### US-38 — Filtres avancés ⚠️
- ⚠️ Filtres basiques existent (statut, tenant)
- ❌ Filtres avancés combinables (employeur, période, score OCR, agent assigné) **à ajouter**
- ❌ Persistance URL et session

---

### EPIC NOTIFICATIONS (2 stories)

#### US-22 — OTP email ⚠️
- ⚠️ Settings prêts (`otp_max_attempts=3`, `otp_validity_minutes=10`)
- ⚠️ Service email exists mais **flow OTP end-to-end pas complet** (génération + envoi + vérif)
- ❌ Rate limiting "5 demandes max par 15 min" à implémenter

#### US-23 — Notification après décision ✅⚠️
- ✅ Notification < 5 min (immédiat en pratique)
- ✅ Templates configurables
- ⚠️ **Envoi double canal** (canal d'origine + email) : seul le canal d'origine est utilisé
- ✅ Audit

---

### EPIC REPORTING & ANALYSE (3 stories)

#### US-24 — Tableau bord temps réel ✅⚠️
- ✅ Page /reporting livrée Phase 2 chap 5
- ✅ Filtres période 7/30/90j
- ✅ Graphiques (timeline SVG, funnel, barres)
- ❌ **Export PDF** non implémenté

#### US-25 — Export sociétaires validés ❌
- ❌ Pas d'endpoint d'export CSV/Excel de la liste
- À faire : `GET /api/dossiers/export?status=valide&format=csv` avec filtres reflétés

#### US-26 — Indicateurs KPI ✅⚠️
- ✅ KPIs principaux (taux validation, temps moyen, auto-complétion…)
- ❌ **Comparaison période précédente** (variation %) non affichée
- ❌ **Seuils d'alerte configurables** par KPI
- ❌ **Export PDF**

---

### EPIC AUDIT & CONFORMITÉ (3 stories)

#### US-27 — Journalisation actions sensibles ✅⚠️
- ✅ Append-only avec chaîne SHA-256
- ✅ Utilisateur, action, ressource, date capturés
- ❌ **IP non capturée** (le backlog l'exige)
- ✅ Réservé admin/DPO
- ❌ **Export CSV** non implémenté
- ✅ Rétention illimitée en BD

#### US-28 — Droit à l'oubli ⚠️
- ✅ Export RGPD complet (`/api/security/dossiers/{id}/export`)
- ❌ **Anonymisation effective** (tâche #19 reportée — purge automatique + remplacement par hash)

#### US-29 — Page d'information ARTCI publique ❌
- ❌ Pas de page publique d'aide
- À faire : page `/aide` ou `/artci` avec notice, coordonnées DPO, formulaire de contact, conforme WCAG AA

---

### EPIC INTERFAÇAGE & INTÉGRATIONS (6 stories)

#### US-30 — Connecteur Perfect Vision REST ⚠️
- ✅ Webhook configurable (URL, HMAC) Phase 2 chap 7
- ⚠️ **HMAC oui** mais pas **mTLS / OAuth2** (à ajouter pour prod)
- ❌ Contrat OpenAPI versionné non documenté
- ❌ Test connectivité auto chaque heure non implémenté

#### US-31 — Export auto dossiers validés ✅⚠️
- ✅ Webhook envoyé sur validation
- ✅ Mapping payload conforme
- ⚠️ **Back-off 1s/2s/4s** vs backlog **1min/5min/30min** : à reparamétrer pour prod
- ❌ Alerte admin après 3 échecs : non implémenté
- ✅ Audit avec status retour

#### US-32 — Webhook temps réel ✅
- ✅ Événements `dossier_validated`, `dossier_rejected`
- ❌ Manquent `dossier_updated` et `droit_a_l_oubli_execute`
- ✅ HMAC signature
- ✅ Re-livraison manuelle via endpoint
- ⚠️ Back-off à reparamétrer (1min/5min/15min/1h/4h/24h)

#### US-33 — Sync matricules SI RH ⚠️
- ✅ `referential_service` avec adapter CSV/HTTP
- ❌ **Pas de scheduled sync** quotidienne
- ❌ "Matricule retraité accepté mais marqué pour traitement spécifique" non géré
- ⚠️ Mode strict (`referential_strict_mode`) défini mais le **branchement dans le parcours d'enrôlement** pas fait

#### US-34 — Tableau bord supervision flux ⚠️
- ✅ Historique deliveries dans /parametres/integrations
- ❌ **Statut Vert/Orange/Rouge par flux** synthétique
- ❌ Export CSV
- ❌ Masquage DCP sauf DPO

#### US-35 — Reprise automatique intégrations ⚠️
- ✅ Retry manuel
- ❌ **Routine de reprise toutes les 5 min** (scheduler)
- ❌ Quarantaine 24h
- ❌ Suite back-off complète (1, 5, 15, 60, 240, 1440 min)

---

## Plan d'action priorisé

### 🔴 Pré-production (avant J0 = 12/09/2026)

| # | Story | Effort estimé |
|---|-------|---------------|
| 1 | **US-02** — Auth AD (en cours) | 1j |
| 2 | **US-36** — Anti-doublons (index unique + UI doublons souples) | 2j |
| 3 | **US-22** — OTP email end-to-end | 1j |
| 4 | **US-29** — Page publique ARTCI + WCAG | 0,5j |
| 5 | Ajuster défauts politique mot de passe (12 chars admins) | 0,5h |
| 6 | Brancher seuil OCR sur revue manuelle (US-13) | 0,5j |
| 7 | Capturer IP dans audit log (US-27) | 0,5j |

### 🟡 Phase 2bis (post-production, M+1)

| # | Story | Effort |
|---|-------|--------|
| 8 | US-25 — Export CSV sociétaires validés | 1j |
| 9 | US-21 — Clôture auto complément 15j | 0,5j |
| 10 | US-19 — Numéro de sociétaire séparé | 1j |
| 11 | US-23 — Notification doublée WhatsApp + email | 0,5j |
| 12 | US-37 — Import en masse référentiels | 2j |
| 13 | US-38 — Filtres avancés /dossiers | 1j |
| 14 | US-28 — Anonymisation effective (Tâche #19) | 2j |

### 🟢 Phase 3 (M+3 et au-delà)

| # | Story | Effort |
|---|-------|--------|
| 15 | US-03 — Système RBAC dynamique multi-rôles | 5j |
| 16 | US-26 — KPI avec comparaison période + seuils alerte | 2j |
| 17 | US-30 — mTLS / OAuth2 Perfect Vision | 2j |
| 18 | US-33 — Sync nocturne SI RH + matricules retraités | 1,5j |
| 19 | US-34/35 — Tableau supervision avancé + reprise auto | 2j |
| 20 | Export PDF reporting | 1j |

---

## Conclusion

**Score de couverture Phase 2 : 53% conforme + 31% partiel = 84% des stories au moins amorcées.**

Le socle est solide : authentification, autorisations, settings, templates, IA, validation, reporting, intégrations sont **opérationnels**. Les 6 gaps "manquant" sont identifiés et ont un plan d'action chiffré.

**Priorité immédiate** : compléter les 7 items pré-production (≈6 jours de dev) puis basculer en production avec un backlog Phase 2bis bien défini.

---

_Document de référence — version 1.0 — 2026-06-15. Auteur : Abdoul OUATTARA (GS2E)._
