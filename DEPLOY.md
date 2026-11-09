# Déploiement MA2E — Backend & Frontend

## 1. Push initial vers Azure DevOps

Le code est aujourd'hui dans un monorepo local. Les 2 dépôts Azure attendent
chacun leur sous-dossier (`backend/` et `frontend/`) comme racine.

```bash
# --- Backend ---
cd backend
git init -b main
git add .
git commit -m "Initial commit — MA2E backend (FastAPI + workflow dynamique)"
git remote add origin https://DLSI@dev.azure.com/DLSI/MA2E/_git/backend
git push -u origin main

# --- Frontend ---
cd ../frontend
git init -b main
git add .
git commit -m "Initial commit — MA2E frontend (Next.js back-office)"
git remote add origin https://DLSI@dev.azure.com/DLSI/MA2E/_git/frontend
git push -u origin main
```

⚠️ **Avant chaque `git add .` :** vérifier qu'aucun `.env` n'est ajouté.
Le `.gitignore` racine couvre déjà `**/.env`, mais double-vérifier avec :

```bash
git status | grep -i env
# Ne doit lister QUE des fichiers .env.example (jamais .env tout court)
```

## 2. Variables d'environnement à configurer côté Azure App Service

### Backend
```env
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/ma2e
REDIS_URL=redis://host:6379/0
MINIO_ENDPOINT=storageaccount.blob.core.windows.net
MINIO_ACCESS_KEY=...
MINIO_SECRET_KEY=...

# Azure OpenAI (chat + structuration OCR)
AZURE_OPENAI_ENDPOINT=https://....cognitiveservices.azure.com/
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_DEPLOYMENT=gpt-5.4-mini
AZURE_OPENAI_API_VERSION=2025-04-01-preview

# Azure OpenAI Embeddings (RAG)
AZURE_OPENAI_EMBEDDING_ENDPOINT=https://....openai.azure.com/openai/deployments/text-embedding-3-small/embeddings?api-version=2023-05-15
AZURE_OPENAI_EMBEDDING_API_KEY=...

# OCR — choisir UN des deux
OCR_SPACE_API_KEY=K...                           # recettes (gratuit)
AZURE_AI_VISION_ENDPOINT=https://...             # production
AZURE_AI_VISION_API_KEY=...

# WhatsApp (production)
WHATSAPP_ACCESS_TOKEN_MA2E=EAA...
WHATSAPP_PHONE_ID_MA2E=...
WHATSAPP_VERIFY_TOKEN=...

# SMTP (notifications + OTP)
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=...
SMTP_USE_TLS=true
SMTP_FROM_EMAIL=no-reply@ma2e.ci
```

### Frontend
```env
NEXT_PUBLIC_API_URL=https://ma2e-backend.azurewebsites.net
```

## 3. Initialisation BD — UNE SEULE COMMANDE

Au premier déploiement (ou pour ré-initialiser une instance fraîche) :

```bash
cd backend
python -m scripts.seed_all
```

Le script enchaîne dans l'ordre :
1. Toutes les migrations BD (rôles, RBAC, audit, employeurs réels, etc.)
2. Le seed principal (tenants, workflows, comptes admin)
3. La restructure du workflow Inscription (23 champs, sous-flux de correction)
4. La création du compte démo viewer (lecture-seule)

Idempotent — peut être ré-exécuté sans danger.

## 4. Comptes par défaut après seed

| Rôle | Email | Mot de passe | Permissions |
|---|---|---|---|
| Super Admin GS2E | `admin@gs2e.ci` | `admin123` | Toutes — gestion multi-tenants |
| Admin MA2E | `admin@ma2e.ci` | `ma2e123` | Toutes sur le tenant MA2E |
| Agent MA2E | `agent@ma2e.ci` | `agent123` | Validation / rejet / complément |
| **Viewer MA2E** | `viewer@ma2e.ci` | `viewer123` | **Lecture-seule** — peut voir mais pas modifier |

⚠️ **Avant la mise en prod :** rotater tous ces mots de passe par défaut.

## 5. Rôle Viewer — détail des permissions

Le viewer peut :
- ✅ Lister et voir le détail de tous les dossiers (`/dossiers`)
- ✅ Voir les conversations WhatsApp/Web (`/conformite/conversations`)
- ✅ Voir les statistiques et tableaux de bord
- ✅ Voir le référentiel des employeurs
- ✅ Voir la configuration des workflows (sans pouvoir éditer)
- ✅ Voir l'audit log et les exports ARTCI
- ✅ Voir la base de connaissances RAG

Le viewer NE peut PAS :
- ❌ Valider / rejeter / demander un complément sur un dossier
- ❌ Créer / modifier / supprimer un workflow ou un step
- ❌ Modifier les settings (intégrations, services activables, etc.)
- ❌ Créer / modifier / supprimer des users ou des rôles
- ❌ Modifier les employeurs, collaborateurs, employeurs
- ❌ Ingérer du nouveau contenu dans la base de connaissances

Implémentation : aucune permission métier n'est attribuée au rôle `viewer`
dans `rbac_service.has_permission` → tous les endpoints protégés par
`require_permission(...)` répondent 403. Les endpoints GET publics restent
accessibles.

## 6. Maintenance — commandes utiles

```bash
# Vider les données de test (préserve workflows et users)
python -m scripts.wipe_test_data

# Vérifier l'état après un test
python -m scripts.check_user_test

# Auditer la structure du workflow
python -m scripts.audit_inscription_workflow

# Re-seeder le workflow Inscription depuis zéro
python -m scripts.reseed_inscription_workflow
```
