# MA2E — Roadmap Phase 2 (Industrialisation Production)

> **Document de mémoire** : ce qui reste à faire après le POC pour passer en production réelle.
> Cohérent avec l'**architecture logicielle** et l'**architecture technique** validées au CVATL.
>
> Date : 15/06/2026 — Cible production : début juillet 2026.

---

## 🎯 Objectif Phase 2

Passer le POC fonctionnel (qui valide le cœur applicatif : FastAPI + Next.js + PostgreSQL + IA) à une **plateforme industrielle prête pour la production** :
- Configurable sans toucher au code (paramètres, référentiels, instructions IA)
- Sécurisée et conforme ARTCI
- Scalable (HA, monitoring, backups)
- Maintenable par l'équipe MA2E sans dépendance permanente à GS2E

---

## ✅ Ce qui est DÉJÀ implémenté (POC actuel — à conserver)

| Domaine | État | Détail |
|---|---|---|
| API FastAPI | ✅ | `app/main.py` + routes `api/auth, dossiers, knowledge, tenants, audit, me` |
| Frontend Next.js 14 | ✅ | `app/login, chat, dossiers, conformite, parametres, qr-code, acces` |
| Multi-tenant | ✅ | Modèle `Tenant`, isolation logique par `tenant_id` |
| Authentification | ✅ | JWT HS256, login `admin@gs2e.ci`, `admin@ma2e.ci`, `agent@ma2e.ci` |
| Machine à états onboarding | ✅ | `conversation/state_machine.py` — 14 étapes + 3 Gates ARTCI |
| OCR CNI | ✅ | `services/ocr_mindee.py` (Mindee) + fallback `ocr_mock.py` |
| LLM assistant | ✅ | Groq `llama-3.3-70b-versatile` via `conversation/llm.py` |
| RAG (base de connaissances) | ✅ | `services/rag.py` + `services/embeddings.py` (Azure OpenAI 1536d) |
| Stockage CNI | ✅ | MinIO local (à basculer sur Azure Blob en prod) |
| Webhooks canaux | ✅ | `webhooks/whatsapp.py`, `webhooks/web.py`, `webhooks/telegram.py` |
| Modèle de données | ✅ | sociétaires, dossiers, conversations, utilisateurs, employeurs, audit_log, pieces_identite |
| Journal d'audit | ✅ | `services/audit_service.py` + hash chaîné SHA-256 |
| Consentements | ✅ | 3 Gates HMAC-SHA256 horodatés (ARTCI v1.0, OCR v1.0, Certification v1.0) |
| Migrations | ✅ | Alembic configuré |
| Conteneurisation | ✅ | `docker-compose.yml` (postgres+pgvector, redis, minio, mailhog) |
| Seeds | ✅ | `seeds/seed.py` (tenants, employeurs, comptes, textes consentement) |

---

## 🔴 Ce qui reste à FAIRE (Phase 2 — production)

### 1. ⚙️ PARAMÉTRAGE PLATEFORME (priorité 🔴 HAUTE)

#### 1.1 — Paramètres globaux MA2E
Page d'administration pour modifier **sans toucher au code** :

| Paramètre | Valeur actuelle (hardcodée) | À paramétrer |
|---|---|---|
| Nom commercial assistante virtuelle | "AYA" (legacy) → à supprimer | À définir par MA2E, paramétrable |
| Limite tentatives OTP | 3 | Paramétrable (1-10) |
| Durée validité OTP | 10 min | Paramétrable (5-30 min) |
| Délai max session conversation | 7 jours | Paramétrable |
| Délai clôture auto si pas de retour | 15 jours | Paramétrable |
| Seuil score OCR pour escalade manuelle | 70 % | Paramétrable (50-95 %) |
| Heures d'ouverture support | Lun-Ven 8h-17h | Paramétrable par MA2E |
| Délai cible prise en charge agent | 30 min | Paramétrable |

**Action** : créer page `/parametres/general` côté frontend + table `tenant_settings` + endpoint `PUT /api/tenants/{id}/settings`.

#### 1.2 — Modèles de messages (templates)
Aujourd'hui les messages sont **hardcodés** dans `conversation/state_machine.py`. À externaliser :

- **Accueil** (premier message du sociétaire)
- **Notice ARTCI Gate 1** (déjà en BD `texte_consentement`, à étendre)
- **Demande matricule + société**
- **Demande OTP email**
- **Demande photos CNI**
- **Confirmation données extraites**
- **Notification validation dossier**
- **Notification refus avec motifs prédéfinis**
- **Notification demande de complément**
- **Message d'erreur générique**
- **Message d'escalade vers agent**

**Action** : table `message_templates` (tenant_id, code, langue, contenu, variables_obligatoires) + page `/parametres/messages` avec preview + validation des variables `{prenom}, {nom}, {motif}, {lien_otp}`.

#### 1.3 — Paramétrage des employeurs (référentiel)
Actuellement seeds 8 employeurs (CIE, SODECI, GS2E, SMB, etc.). À industrialiser :

- ✅ Liste affichée à `/parametres/employeurs` (existe)
- ❌ **Import CSV** pour bulk update (US-37 du backlog)
- ❌ Activation/désactivation sans suppression (toggle statut)
- ❌ Validation : pas de doublon code/nom, pas de suppression si sociétaires liés

#### 1.4 — Paramétrage des matricules valides (référentiel)
**Le plus critique pour la conformité MA2E** :

- ❌ Table `matricules_valides` (tenant_id, matricule, employeur_id, statut, source, imported_at)
- ❌ **Import CSV mensuel** par admin MA2E (mode dégradé voir archi technique)
- ❌ Vérification au moment de l'enrôlement (blocage si matricule inconnu)
- ❌ Statut "retraité" géré différemment (accepté mais marqué)
- ❌ Rapport d'import : lignes acceptées / rejetées avec motif

**Action** : page `/parametres/matricules` + endpoint import CSV + validation dans la machine à états.

---

### 2. 🤖 INSTRUCTIONS CONVERSATIONNELLES DE L'IA (priorité 🔴 HAUTE)

#### 2.1 — Prompts système paramétrables
Aujourd'hui les prompts sont **hardcodés** dans `conversation/llm.py` et `services/rag.py`. À externaliser :

| Prompt | Usage | Paramétrable par |
|---|---|---|
| **System prompt principal** | Personnalité, ton, périmètre de l'assistante | Admin MA2E |
| **Prompt RAG** | "Tu réponds uniquement avec les sources fournies..." | Admin MA2E |
| **Prompt refus** | "Si tu ne sais pas, dis-le et propose l'escalade humaine" | Admin MA2E |
| **Prompt onboarding** | Instructions pour guider le sociétaire étape par étape | Admin MA2E |
| **Mots-clés escalade humaine** | "conseiller, agent, humain, je veux parler à..." | Admin MA2E |
| **Disclaimer obligatoire** | Mention en fin de chaque réponse | Admin MA2E |

**Action** : table `llm_prompts` (tenant_id, code, version, contenu_prompt, active) + page `/parametres/ia/prompts` avec :
- Édition par sections (system, RAG, refus, etc.)
- Versioning (historique des changements + rollback)
- Test "playground" pour essayer le prompt avant publication
- Validation par DPO avant activation (workflow d'approbation)

#### 2.2 — Configuration RAG (Retrieval Augmented Generation)
Paramètres qui doivent être ajustables sans redéploiement :

- **Seuil de confiance** (currently fixed à 0.7) → paramétrable 0.5-0.95
- **Nombre de chunks récupérés** (top_k) → paramétrable 3-10
- **Taille des chunks** lors de l'ingestion → paramétrable 256-1024 tokens
- **Modèle d'embeddings** → admin choisit Azure OpenAI vs autre
- **Modèle LLM** → admin choisit Groq Llama 3.3 / GPT-4 / Mistral
- **Température** du LLM → paramétrable 0.0-1.0

**Action** : page `/parametres/ia/rag` + endpoint configuration.

#### 2.3 — Base de connaissances (déjà partiellement fait)
État actuel : ingestion via `services/knowledge_ingest.py` + `services/scraper.py`.

À compléter pour la prod :
- ✅ Page `/parametres/knowledge` (existe)
- ❌ Ré-ingestion programmée (cron) du site MA2E
- ❌ Validation des sources avant indexation (workflow DPO)
- ❌ Statistiques d'usage par source (quelles sources sont citées le plus ?)
- ❌ Supprimer/désactiver une source sans tout réindexer
- ❌ Multi-format : PDF, DOCX (actuellement seulement HTML/text)

---

### 3. 👥 GESTION DES UTILISATEURS ET RÔLES (priorité 🟠 MOYENNE)

#### 3.1 — Gestion fine des rôles (US-03 du backlog)
Aujourd'hui : 3 rôles hardcodés (super_admin, tenant_admin, agent). À étendre :

- **Agent validateur** : peut valider/refuser dossiers
- **Superviseur** : reporting + KPI, pas d'action sur dossiers
- **Lecteur** : consultation seule (audit, reporting)
- **IT** : administration technique uniquement
- **DPO** : accès au journal d'audit, droits sociétaires, anonymisation

**Action** : table `roles` + `permissions` + matrice rôle×permission + page `/parametres/roles`.

#### 3.2 — Authentification Active Directory ERANOVE
US-02 du backlog. Aujourd'hui : auth locale uniquement (email/password).

**Action** :
- Connecteur LDAPS vers AD ERANOVE
- Auto-provisioning du profil agent à la 1ère connexion
- Mapping rôles AD → rôles MA2E
- Fallback local pour les comptes non-AD (super_admin GS2E)

#### 3.3 — Import en masse des comptes (US-37)
- Import CSV utilisateurs MA2E (nom, prénoms, email, rôle, statut)
- Validation avant insertion (transaction atomique)
- Rapport d'import téléchargeable

---

### 4. 🛡️ SÉCURITÉ ET CONFORMITÉ ARTCI (priorité 🔴 HAUTE)

#### 4.1 — Anti-doublon strict (US-36 du backlog)
Aujourd'hui : pas de détection automatique de doublon à l'enrôlement.

**Action** :
- À la fin de l'enrôlement : vérification matricule + numéro CNI + (nom+prénoms+ddn)
- Doublon strict (matricule ou CNI déjà présent) → blocage automatique
- Doublon souple (nom+prénoms+ddn) → alerte agent
- Onglet "Doublons à arbitrer" pour les agents

#### 4.2 — Droit à l'oubli et anonymisation (US-28)
Backlog dit "fait" mais à compléter pour la prod :

- ❌ Procédure DPO depuis le backoffice (page dédiée `/conformite/droits`)
- ❌ Anonymisation des données nominatives (nom, prénoms, photos, email, téléphone)
- ❌ Conservation des données statistiques + audit (sans lien nominatif)
- ❌ Génération d'un accusé d'exécution daté + signé
- ❌ Workflow de double validation (DPO + admin)

#### 4.3 — Politique de rétention automatique
Conformité ARTCI loi 2013-450 :

- Conversations : 7 jours d'inactivité → purge
- Dossiers refusés : 1 an puis suppression (sauf opposition)
- Dossiers validés : durée affiliation + 5 ans après désaffiliation
- Journal d'audit : 12 mois minimum
- Photos CNI : durée affiliation + 5 ans

**Action** : worker cron qui exécute les purges + dashboard `/conformite/retention`.

#### 4.4 — Page d'information ARTCI permanente (US-29)
- Page publique accessible depuis chaque message
- Coordonnées du DPO MA2E
- Formulaire de contact (notifié au DPO en < 24h)
- Norme WCAG niveau AA (accessibilité)

#### 4.5 — Tests de pénétration et audit blanc
Avant mise en prod :
- Audit de code (SAST) — sonarqube ou équivalent
- Test d'intrusion (DAST) — OWASP ZAP
- Audit blanc DPO + équipe sécurité ERANOVE
- Validation préalable de la notice ARTCI par le DPO

---

### 5. 📊 REPORTING ET KPI (priorité 🟠 MOYENNE)

#### 5.1 — Dashboard temps réel (US-24)
- ❌ Page `/dossiers/dashboard` avec compteurs actualisés/min
- ❌ Filtres : période / société / agent
- ❌ Graphiques cercles, barres, courbes
- ❌ Export PDF du dashboard

#### 5.2 — KPI opérationnels (US-26)
- Délai moyen de traitement
- Taux de validation au premier passage
- Taux d'escalade vers conseiller
- Taux de complétude OCR
- Comparaison vs période précédente
- Seuils d'alerte par KPI

#### 5.3 — Export sociétaires validés (US-25)
- Export CSV/Excel avec colonnes paie
- Filtres période + société
- UTF-8 BOM pour Excel natif
- Limite 50 000 lignes par export
- Traçage dans audit log

#### 5.4 — Filtres avancés `/dossiers` (US-38)
- Combinaison filtres : employeur, statut, période, score, agent
- Persistance dans l'URL pour partage
- Indicateurs synthétiques en tête
- Tri multi-colonnes persistant

---

### 6. 🏗️ INFRASTRUCTURE PRODUCTION (priorité 🔴 HAUTE)

#### 6.1 — Migration MinIO → Azure Blob Storage
- Adapter `app/core/storage.py` pour parler à Azure Blob
- Chiffrement au repos KMS
- Versioning + soft-delete
- Lifecycle policy (archivage à 1 an, suppression à 5 ans)
- Backup cross-région

#### 6.2 — PostgreSQL production
- ❌ Réplica streaming (Master + Slave)
- ❌ Sauvegarde quotidienne + PITR 7 jours
- ❌ Test de restauration mensuel
- ❌ Monitoring (pg_stat, requêtes lentes)
- ❌ Tuning pgvector pour la prod (index HNSW dimensionné)

#### 6.3 — Haute disponibilité applicative
- ❌ 2 instances Web+API derrière LB (Azure App Gateway / NGINX)
- ❌ Health checks `/health` configurés
- ❌ Zero-downtime deploy (rolling update)
- ❌ Autoscaling sur CPU > 70 %

#### 6.4 — Monitoring & observabilité
- ❌ Logs centralisés (Azure Monitor / Loki / ELK)
- ❌ Métriques Prometheus
- ❌ Dashboard Grafana (déjà déployé en dev sur port 13000)
- ❌ Alerting : 5xx > seuil, latence P95, espace disque, échec backup
- ❌ APM / tracing (Application Insights ou Sentry)

#### 6.5 — CI/CD
- ❌ Pipeline build → test → push registry → déploiement
- ❌ 3 environnements isolés : dev / staging / prod
- ❌ Secrets dans Azure Key Vault (jamais en clair)
- ❌ Migrations Alembic exécutées au déploiement
- ❌ Rollback automatique sur échec health check

---

### 7. 🔗 INTÉGRATIONS GROUPE (priorité 🟡 BASSE — selon disponibilité DSI)

#### 7.1 — Sync avec Perfect Vision (groupe ERANOVE)
**Reporté Phase 3** si Perfect Vision n'a pas d'API. À discuter avec DSI ERANOVE.
- Si API disponible : connecteur REST mTLS + export auto dossiers validés
- Si pas d'API : export CSV manuel mensuel (mode dégradé)

#### 7.2 — Webhook bidirectionnel
- Notification temps réel à Perfect Vision lors d'une validation
- Signature HMAC-SHA256 du payload
- Mécanisme de retry + quarantaine après 24h

---

### 8. 📱 CONDUITE DU CHANGEMENT (priorité 🟠 MOYENNE)

#### 8.1 — Formation
- Manuel utilisateur sociétaire (PDF + vidéo 2 min)
- Manuel agent MA2E (validation, motifs de refus, demande complément)
- Manuel admin (paramétrage, import CSV, gestion utilisateurs)
- Session de formation par agence

#### 8.2 — Migration progressive du papier au digital
- Phase pilote : 1 agence Abidjan
- Élargissement progressif : autres agences Abidjan puis intérieur
- Maintien du canal papier en parallèle pendant 3 mois
- KPI d'adoption tracé

#### 8.3 — Communication
- Affichage QR code en agence
- Mention sur factures CIE/SODECI
- Communiqué groupe ERANOVE
- Réseaux sociaux MA2E

---

## 📅 Macro-planning Phase 2

| Sprint | Période | Focus principal |
|---|---|---|
| **Sprint 3** | 16/06 → 27/06 | Paramétrage (général + messages + matricules) + Instructions IA paramétrables |
| **Sprint 4** | 30/06 → 11/07 | Rôles fins + AD ERANOVE + Anti-doublon + Anonymisation |
| **Sprint 5** | 14/07 → 25/07 | Dashboard KPI + Filtres avancés + Migration Azure Blob |
| **Sprint 6** | 28/07 → 08/08 | HA + Monitoring + CI/CD + Pen-test |
| **Recette métier** | 11/08 → 22/08 | Test avec agents MA2E + corrections |
| **Conduite changement** | 25/08 → 05/09 | Formation + pilote agence |
| **Mise en production** | 08/09 → 12/09 | Déploiement prod + suivi rapproché |

---

## 🚨 Points de vigilance

1. **Le nom de l'assistante virtuelle n'est pas défini** — MA2E doit trancher avant la mise en production
2. **Référentiel matricules ERANOVE** — confirmer mode (API ou CSV) avec DSI ERANOVE
3. **Localisation des données** — datacenter CI ou cloud Azure West Europe ? Décision juridique pour ARTCI
4. **Provider SMTP** — choix entre AWS SES, Resend, Brevo
5. **Audit ARTCI préalable** — bloque la mise en prod, prévoir 15 jours minimum
6. **Domaine DNS** — `ma2e.ci` à réserver auprès du registrar ivoirien

---

## 🎯 Critères de succès Phase 2

À la fin de la Phase 2, la plateforme doit :

- ✅ Permettre à l'admin MA2E de **changer un paramètre sans redéploiement**
- ✅ Permettre au DPO de **modifier les instructions de l'IA** avec validation
- ✅ Avoir **réussi un audit blanc DPO** + un pen-test
- ✅ Supporter **200 sociétaires + 30 agents simultanés** avec P95 < 3s
- ✅ Avoir **2 instances HA** et un **réplica BD** opérationnels
- ✅ Avoir **3 environnements isolés** (dev, staging, prod)
- ✅ Avoir **traité au moins 100 dossiers réels** en pilote sans incident
- ✅ Avoir **formé au moins 20 agents** MA2E

---

*Document rédigé pour servir de référence après le passage du CVATL.*
*À mettre à jour à chaque livraison de sprint.*
