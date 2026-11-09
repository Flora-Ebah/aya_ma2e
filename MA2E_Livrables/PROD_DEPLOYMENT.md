# Guide de déploiement production — MA2E Identification

> **Cible** : mise en production sur Azure (option A, recommandée) ou Railway (option B, plus rapide).
> **Date cible production** : 12/09/2026.
> **Auteur technique** : Abdoul OUATTARA (GS2E).

---

## 1. Architecture cible

```
            ┌─────────────────────────────────────────────────────┐
INTERNET ──→│ Cloudflare / Azure Front Door (TLS, WAF, CDN)       │
            └─────────────────┬───────────────────────────────────┘
                              │
                              ▼
            ┌────────────────────────────────────┐
            │ Container Apps (2 services)        │
            │  ├─ ma2e-backend  (FastAPI)        │
            │  └─ ma2e-frontend (Next.js SSR)    │
            └────┬────────────┬──────────────────┘
                 │            │
        ┌────────▼───┐ ┌──────▼─────────┐ ┌──────────────────┐
        │ Azure PG   │ │ Azure Cache    │ │ Azure Blob Storage│
        │ Flexible   │ │ for Redis      │ │ (DCP chiffrées)   │
        │ + pgvector │ │                │ │                   │
        └────────────┘ └────────────────┘ └──────────────────┘
                 │
        ┌────────▼─────────┐
        │ Backups quoti-   │
        │ diens (7j hot,   │
        │ 30j cold)        │
        └──────────────────┘

Services externes : Groq (LLM), Azure OpenAI (embeddings), Mindee (OCR),
                    WhatsApp Cloud API (Meta).
```

---

## 2. Composants Azure

| Composant | Référence | Justification |
|-----------|-----------|---------------|
| **Container Apps** | Consumption + Dedicated | Auto-scale, HTTPS managé, blue/green |
| **PostgreSQL Flexible Server** | B2s (2 vCPU / 4 Go) + extension `vector` | pgvector + sauvegardes auto + HA en option |
| **Cache for Redis** | Basic C0 | Cache settings, sessions MFA, lockout login |
| **Blob Storage** | Standard LRS, hot tier | DCP chiffrées au repos (CSE-256) |
| **Key Vault** | Standard | Secrets : JWT, Groq, Mindee, WhatsApp |
| **Application Insights** | Pay-as-you-go | Traces, métriques, alertes |
| **Front Door** | Standard | TLS, WAF (OWASP), routage géo CI |

Estimation budget : **~250 €/mois** en croisière (révision détaillée slide 15 CVATL).

---

## 3. Variables d'environnement requises

### Backend (`backend/.env`)

| Variable | Type | Exemple | Notes |
|----------|------|---------|-------|
| `APP_ENV` | str | `production` | Active JSON logs + cache long |
| `DATABASE_URL` | str | `postgresql+asyncpg://user:pwd@host:5432/db` | URL complète asyncpg |
| `REDIS_URL` | str | `redis://:pwd@host:6379/0` | Avec mot de passe |
| `JWT_SECRET` | secret | `<32+ chars random>` | **Key Vault** |
| `JWT_ALGORITHM` | str | `HS256` | |
| `JWT_EXPIRE_MINUTES` | int | `1440` | Override possible via setting `session_idle_minutes` |
| `GROQ_API_KEY` | secret | `gsk_…` | **Key Vault** |
| `GROQ_MODEL` | str | `llama-3.3-70b-versatile` | Override possible via setting `ai_model` |
| `AZURE_OPENAI_API_KEY` | secret | `…` | **Key Vault** |
| `AZURE_OPENAI_ENDPOINT` | str | `https://…openai.azure.com` | |
| `AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT` | str | `text-embedding-3-small` | 1536 dims |
| `MINDEE_API_KEY` | secret | `…` | **Key Vault** |
| `WHATSAPP_VERIFY_TOKEN` | secret | `…` | **Key Vault** |
| `BLOB_ACCOUNT_URL` | str | `https://…blob.core.windows.net` | |
| `BLOB_CONTAINER_DCP` | str | `ma2e-dcp` | |
| `BLOB_ENCRYPTION_KEY` | secret | base64 256-bit | **Key Vault** — chiffrement applicatif |
| `SMTP_HOST` | str | `smtp.sendgrid.net` | |
| `SMTP_PORT` | int | `587` | |
| `SMTP_USER` | secret | `apikey` | |
| `SMTP_PASSWORD` | secret | `SG.…` | **Key Vault** |
| `SMTP_FROM_EMAIL` | str | `noreply@ma2e.ci` | |

### Frontend (`frontend/.env.local`)

| Variable | Exemple |
|----------|---------|
| `NEXT_PUBLIC_API_URL` | `https://api.ma2e.ci` |
| `NEXT_PUBLIC_WHATSAPP_NUMBER` | `22587137512` |

---

## 4. Secrets Key Vault

Liste des secrets à provisionner **AVANT** le premier déploiement :

```bash
az keyvault create --name kv-ma2e-prod --resource-group ma2e-rg --location francecentral

# Génération JWT_SECRET sécurisé (à exécuter une seule fois)
JWT_SECRET=$(openssl rand -base64 48)
az keyvault secret set --vault-name kv-ma2e-prod --name jwt-secret --value "$JWT_SECRET"

# Idem pour BLOB_ENCRYPTION_KEY (clé symmétrique 256 bits base64)
BLOB_KEY=$(openssl rand -base64 32)
az keyvault secret set --vault-name kv-ma2e-prod --name blob-encryption-key --value "$BLOB_KEY"

# Secrets tiers
az keyvault secret set --vault-name kv-ma2e-prod --name groq-api-key --value "gsk_…"
az keyvault secret set --vault-name kv-ma2e-prod --name mindee-api-key --value "…"
az keyvault secret set --vault-name kv-ma2e-prod --name azure-openai-key --value "…"
az keyvault secret set --vault-name kv-ma2e-prod --name whatsapp-verify-token --value "…"
az keyvault secret set --vault-name kv-ma2e-prod --name smtp-password --value "SG.…"
```

L'identité managée du Container App (system-assigned) reçoit le rôle `Key Vault Secrets User` sur ce KV.

---

## 5. Procédure de déploiement (Container Apps)

### 5.1 Provisionnement initial (une seule fois)

```bash
# 1. Resource Group
az group create --name ma2e-rg --location francecentral

# 2. PostgreSQL Flexible Server (B2s, public en POC, VNet en prod réelle)
az postgres flexible-server create \
  --resource-group ma2e-rg --name pg-ma2e-prod \
  --location francecentral --sku-name Standard_B2s \
  --version 16 --storage-size 64 \
  --admin-user ma2e_admin --admin-password "$(openssl rand -base64 24)"

# Activer pgvector
az postgres flexible-server parameter set \
  --resource-group ma2e-rg --server-name pg-ma2e-prod \
  --name azure.extensions --value vector

# 3. Cache for Redis
az redis create --resource-group ma2e-rg --name redis-ma2e-prod \
  --location francecentral --sku Basic --vm-size C0

# 4. Blob Storage
az storage account create --name stma2eprod --resource-group ma2e-rg \
  --location francecentral --sku Standard_LRS --kind StorageV2 \
  --allow-blob-public-access false
az storage container create --account-name stma2eprod --name ma2e-dcp

# 5. Container Apps Environment + Log Analytics
az monitor log-analytics workspace create --resource-group ma2e-rg --workspace-name laws-ma2e-prod
az containerapp env create --name cae-ma2e-prod --resource-group ma2e-rg \
  --location francecentral --logs-workspace-id <id>
```

### 5.2 Déploiement de l'image backend

```bash
# Build + push vers Azure Container Registry
az acr login --name acrma2e
docker build -t acrma2e.azurecr.io/ma2e-backend:0.2.0 -f backend/Dockerfile backend/
docker push acrma2e.azurecr.io/ma2e-backend:0.2.0

# Crée le Container App avec injection des secrets KV
az containerapp create \
  --resource-group ma2e-rg \
  --name ma2e-backend \
  --environment cae-ma2e-prod \
  --image acrma2e.azurecr.io/ma2e-backend:0.2.0 \
  --target-port 8000 --ingress external \
  --min-replicas 1 --max-replicas 5 \
  --cpu 0.5 --memory 1.0Gi \
  --secrets jwt-secret=keyvaultref:https://kv-ma2e-prod.vault.azure.net/secrets/jwt-secret,identityref:/subscriptions/…/userAssignedIdentities/… \
  --env-vars APP_ENV=production DATABASE_URL=… JWT_SECRET=secretref:jwt-secret …
```

### 5.3 Migrations DB

Avant chaque déploiement majeur, exécuter les migrations via un **job ponctuel** :

```bash
# Option 1 : Container App Job ponctuel
az containerapp job create --name ma2e-migrate \
  --image acrma2e.azurecr.io/ma2e-backend:0.2.0 \
  --command "python" --args "-m,app.bootstrap" \
  --trigger-type Manual --replica-timeout 300

az containerapp job start --name ma2e-migrate

# Option 2 : exec dans le pod après deploy (POC)
az containerapp exec --name ma2e-backend --command "python -m app.bootstrap"
az containerapp exec --name ma2e-backend --command "python -m scripts.migrate_mfa"
```

Pour MFA (POC) :
```bash
python -m scripts.migrate_mfa
```

---

## 6. Probes Kubernetes / Container Apps

Endpoints exposés par le backend (`app/api/health.py`) :

| Endpoint | Cible probe | Comportement |
|----------|-------------|--------------|
| `GET /health/liveness` | `livenessProbe` | Toujours 200 si le process tourne |
| `GET /health/readiness` | `readinessProbe` | 200 si DB joignable, 503 sinon |
| `GET /health/system-info` | Dashboard ops | Admin uniquement (auth requise) |

Configuration recommandée Container App :

```yaml
probes:
  - type: Liveness
    httpGet:
      path: /health/liveness
      port: 8000
    initialDelaySeconds: 10
    periodSeconds: 30
    failureThreshold: 3
  - type: Readiness
    httpGet:
      path: /health/readiness
      port: 8000
    initialDelaySeconds: 5
    periodSeconds: 10
    failureThreshold: 2
  - type: Startup
    httpGet:
      path: /health/liveness
      port: 8000
    periodSeconds: 5
    failureThreshold: 12  # 60s pour démarrer
```

---

## 7. Monitoring

### Application Insights

Les logs structurés JSON (configurés par `app/core/logging_config.py`) sont automatiquement ingérés par Container Apps → Log Analytics → App Insights.

**Requêtes KQL utiles** :

```kusto
// Erreurs 5xx des dernières 24h
ContainerAppConsoleLogs_CL
| where Log_s contains "level"
| extend log = parse_json(Log_s)
| where tostring(log.level) == "error"
| where TimeGenerated > ago(24h)
| project TimeGenerated, log.msg, log.logger
| order by TimeGenerated desc

// Latence p95 endpoint /api/dossiers/{id}/validate
requests
| where name == "POST /api/dossiers/{dossier_id}/validate"
| summarize p95=percentile(duration, 95), count=count() by bin(timestamp, 1h)

// Alertes ARTCI : exports RGPD volumétrie
ContainerAppConsoleLogs_CL
| where Log_s contains "data_export"
| summarize exports=count() by bin(TimeGenerated, 1d)
```

### Alertes critiques (à provisionner)

| Alerte | Seuil | Action |
|--------|-------|--------|
| Erreur 5xx > 1% sur 5 min | > 1% | Email DevOps + Slack |
| Latence p95 > 2s sur 10 min | > 2s | Email DevOps |
| Lockouts login > 50/h | > 50 | Email DevOps + revue logs |
| Pod restarts > 3 en 1h | > 3 | Page DevOps (on-call) |
| Volume exports RGPD > 10/jour | > 10 | Email DPO (anomalie possible) |

---

## 8. Sauvegardes & restore

### Backups automatiques PostgreSQL

Activés par défaut sur Flexible Server :
- **Rétention courte** : 7 jours (PITR à la minute)
- **Rétention longue** : Geo-redundant backup activé → 35 jours

### Backup applicatif additionnel (cold storage)

Une fois par jour, dump logique vers Blob :

```bash
# Cron quotidien (Container App Job)
pg_dump --format=custom \
  --no-owner --no-privileges \
  --file=/tmp/ma2e_$(date +%Y%m%d).dump \
  "$DATABASE_URL"
az storage blob upload --account-name stma2eprod \
  --container-name ma2e-backups \
  --name "daily/$(date +%Y%m%d).dump" \
  --file /tmp/ma2e_$(date +%Y%m%d).dump
```

Rétention cold : 90 jours (conforme article 36 ARTCI sur la durée de conservation).

### Procédure de restore (RPO ≤ 24h, RTO ≤ 4h)

1. Provisionner un nouveau Flexible Server (peut être en dégradé sur la même région)
2. Restaurer le dernier dump via `pg_restore`
3. Re-pointer `DATABASE_URL` dans Container App
4. Lancer `python -m app.bootstrap` (pour s'assurer du schema courant)
5. Valider sur `/health/readiness`

---

## 9. CI/CD GitHub Actions

Workflow recommandé (`.github/workflows/deploy.yml`) :

1. **Trigger** : push sur `main`
2. **Steps** :
   - Tests unitaires Python (pytest)
   - Lint (ruff)
   - TypeCheck frontend (`tsc --noEmit`)
   - Build Docker `backend/Dockerfile`
   - Push vers ACR
   - `az containerapp update --image acrma2e.azurecr.io/ma2e-backend:${SHA}`
   - Wait pour readiness (`curl https://api.ma2e.ci/health/readiness`)
   - Notif Slack succès/échec

À implémenter en Phase 2 chapitre 7 (post-démo).

---

## 10. Runbook ops

### Redémarrer un pod

```bash
az containerapp revision restart \
  --resource-group ma2e-rg \
  --name ma2e-backend \
  --revision <revision-name>
```

### Voir les logs en temps réel

```bash
az containerapp logs show \
  --resource-group ma2e-rg \
  --name ma2e-backend \
  --tail 100 --follow
```

### Scale manuel

```bash
az containerapp update --name ma2e-backend --resource-group ma2e-rg \
  --min-replicas 2 --max-replicas 10
```

### Rollback (revert vers la révision précédente)

```bash
# Lister les révisions
az containerapp revision list --name ma2e-backend --resource-group ma2e-rg \
  --output table

# Activer la précédente, désactiver la courante
az containerapp revision activate --name ma2e-backend --resource-group ma2e-rg \
  --revision <previous>
az containerapp revision deactivate --name ma2e-backend --resource-group ma2e-rg \
  --revision <current>
```

---

## 11. Checklist pré-production

- [ ] `JWT_SECRET` généré aléatoirement (≥ 32 octets), stocké dans Key Vault
- [ ] `BLOB_ENCRYPTION_KEY` provisionnée, sauvegardée hors ligne (loi 2013-450 art.32)
- [ ] Backups PG quotidiens activés + test restore validé
- [ ] App Insights configuré avec alertes critiques (cf. §7)
- [ ] HTTPS/TLS forcé via Front Door
- [ ] CORS restreint à `https://app.ma2e.ci`
- [ ] WAF activé (OWASP Top 10)
- [ ] DPO email vérifié (`security.dpo_email` setting)
- [ ] Rétention dossiers paramétrée (5 ans par défaut, conforme ARTCI)
- [ ] MFA activé pour tous les comptes `super_admin` et `tenant_admin`
- [ ] Politique de mot de passe ≥ 12 caractères pour admins (vs 8 défaut)
- [ ] Test end-to-end parcours sociétaire WhatsApp + Web
- [ ] Test end-to-end conformité ARTCI : export RGPD individuel
- [ ] Doc de continuité d'activité (PCA) validée
- [ ] Runbook ops imprimé / accessible hors ligne

---

## 12. Contact

| Rôle | Personne | Contact |
|------|----------|---------|
| Architecte / dev lead | Abdoul OUATTARA | ouattaraab@gmail.com |
| Sponsor MA2E | (à compléter) | |
| DPO MA2E | (à compléter) | dpo@ma2e.ci |
| Support Azure | (compte Azure GS2E) | portal.azure.com |
| Support Groq | (organisation Groq) | console.groq.com |

---

_Document de référence — version 1.0 — 2026-06-15_
