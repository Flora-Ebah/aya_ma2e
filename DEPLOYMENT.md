# Déploiement MA2E — Guide DevOps

Plateforme d'identification digitale des sociétaires MA2E
(WhatsApp Cloud API + Web Chat + Back-office + Assistant IA AYA)

---

## 🏗 Architecture cible

```
Internet
   │
   ▼
[ Reverse proxy ]  ── Caddy / Traefik / Nginx + Let's Encrypt
   ├─ api.ma2e.ci    → Backend FastAPI (port 8000)
   └─ app.ma2e.ci    → Frontend Next.js (port 3000)
        │
        ▼
   ┌────────────────────────────────────┐
   │  PostgreSQL 16 + pgvector          │
   │  Redis 7                           │
   │  MinIO (chiffré AES-256)           │
   └────────────────────────────────────┘
```

---

## 📦 Composants

| Service | Tech | Port | Persistance |
|---|---|---|---|
| **backend** | FastAPI 0.115 + Python 3.11 | 8000 | Stateless |
| **frontend** | Next.js 14 + Plus Jakarta Sans | 3000 | Stateless |
| **postgres** | PostgreSQL 16 + extension `vector` | 5432 | Volume persistant |
| **redis** | Redis 7 | 6379 | Volume (AOF) |
| **minio** | MinIO server | 9000 / 9001 | Volume persistant |

---

## 🚀 Déploiement rapide (Docker Compose)

### 1. Cloner le repo

```bash
git clone https://github.com/Flora-Ebah/aya_ma2e.git
cd aya_ma2e
```

### 2. Configurer les secrets

```bash
cp backend/.env.example backend/.env
cp frontend/.env.local.example frontend/.env.local
# Éditer ces fichiers avec les vrais secrets (cf. section "Variables à demander")
```

### 3. Lancer les services

```bash
docker-compose up -d
```

### 4. Bootstrap de la base

```bash
docker-compose exec backend python -m app.bootstrap
docker-compose exec backend python seeds/seed.py
```

### 5. Valider le webhook public

```bash
curl -i "https://api.ma2e.ci/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=VOTRE_VERIFY_TOKEN&hub.challenge=test123"
# Doit retourner HTTP 200 avec body `test123`
```

---

## 🔐 Variables d'environnement (à mettre dans un coffre de secrets)

### Backend (`backend/.env`)

```bash
# DB
DATABASE_URL=postgresql+asyncpg://USER:PASS@db:5432/ma2e
DATABASE_URL_SYNC=postgresql://USER:PASS@db:5432/ma2e

# Redis
REDIS_URL=redis://redis:6379/0

# MinIO
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=<généré>
MINIO_SECRET_KEY=<généré 32+ chars>
MINIO_SECURE=true   # true en prod si MinIO derrière HTTPS

# JWT
JWT_SECRET=<openssl rand -hex 32>
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# LLM Groq (assistant AYA)
GROQ_API_KEY=<demandé à MA2E>
GROQ_MODEL=llama-3.3-70b-versatile

# Mindee OCR
MINDEE_API_KEY=<demandé à MA2E>
MINDEE_MODEL_ID=<demandé à MA2E>

# Azure OpenAI Embeddings (RAG)
AZURE_OPENAI_EMBEDDING=<endpoint>
AZURE_OPENAI_API_KEY_EMBEDDING=<clé>

# WhatsApp Meta
WHATSAPP_VERIFY_TOKEN=<chaîne random — sera saisie dans Meta Console>
WHATSAPP_PHONE_ID_MA2E=<fourni par MA2E après création du numéro>
WHATSAPP_ACCESS_TOKEN_MA2E=<token System User permanent>
WABA_ID_MA2E=<fourni par MA2E>

# App
APP_ENV=production
APP_BASE_URL=https://api.ma2e.ci
PUBLIC_WEBHOOK_URL=https://api.ma2e.ci
```

### Frontend (`frontend/.env.local`)

```bash
NEXT_PUBLIC_API_URL=https://api.ma2e.ci
NEXT_PUBLIC_WHATSAPP_NUMBER=22587137512
```

---

## 🌐 DNS & SSL

### DNS

| Sous-domaine | Pointe vers | Usage |
|---|---|---|
| `api.ma2e.ci` | IP serveur backend | API REST + webhook WhatsApp |
| `app.ma2e.ci` | IP serveur frontend | Back-office gestionnaires |

### SSL

- **Let's Encrypt** via Caddy / Traefik avec auto-renew
- **TLS 1.3 minimum** (exigence ARTCI §10.1)
- **HSTS** activé

Exemple Caddyfile :

```
api.ma2e.ci {
    reverse_proxy backend:8000
    tls admin@ma2e.ci
    encode gzip
}

app.ma2e.ci {
    reverse_proxy frontend:3000
    tls admin@ma2e.ci
    encode gzip
}
```

---

## 🔗 Configuration du webhook WhatsApp Meta

Une fois le backend déployé et accessible publiquement :

1. Aller sur **https://developers.facebook.com/apps** → MA2E Identification
2. Menu de gauche : **WhatsApp → API Setup → Webhook**
3. Cliquer **Modifier** sur la configuration webhook
4. Saisir :
   - **URL de rappel** : `https://api.ma2e.ci/webhooks/whatsapp`
   - **Verify token** : la valeur exacte de `WHATSAPP_VERIFY_TOKEN` côté backend
5. **Valider** — Meta envoie un GET de validation
6. Si ✅ vert → s'abonner aux événements : cocher **`messages`**

---

## 📊 Monitoring & observabilité

### Logs
- **Stdout** des conteneurs → Loki / Datadog / Papertrail
- **Niveau** : `INFO` en prod, `DEBUG` en staging

### Métriques recommandées
- Health check : `GET /health` → backend retourne `{"status": "healthy"}`
- Erreurs HTTP 5xx
- Latence P95 endpoints OCR (cible < 15s)
- Volume messages WhatsApp entrants/sortants
- Taille base vectorielle (chunks)

### Alerting
- Erreurs OCR > 10% → alerter
- Latence webhook > 5s → alerter
- DB disque > 80% → alerter
- Certificat SSL expire dans < 14 jours → alerter

---

## 💾 Sauvegardes

### PostgreSQL
- **Backup quotidien** automatisé (pg_dump)
- **Rétention** : 30 jours chaud, 7 ans froid (exigence ARTCI §10.5)
- **Test restauration** mensuel

### MinIO
- Réplication sur site secondaire
- Politique de rétention liée au cycle de vie sociétaire (cf. PRD §10.5)

### Redis
- AOF activé pour persistance
- Snapshot RDB quotidien

---

## 🧪 Endpoints à tester en staging

```bash
# Health
curl https://api.ma2e.ci/health

# Webhook verify
curl "https://api.ma2e.ci/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=YOUR_TOKEN&hub.challenge=ping"

# Login back-office
curl -X POST https://api.ma2e.ci/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@ma2e.ci", "password": "ma2e123"}'

# Frontend
curl -I https://app.ma2e.ci/login
```

---

## 🔄 CI/CD recommandé (GitHub Actions)

```yaml
# .github/workflows/deploy.yml
name: Deploy
on:
  push:
    branches: [main]
jobs:
  build-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/build-push-action@v5
        with:
          context: ./backend
          push: true
          tags: registry.ma2e.ci/backend:${{ github.sha }}
  build-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/build-push-action@v5
        with:
          context: ./frontend
          push: true
          tags: registry.ma2e.ci/frontend:${{ github.sha }}
  deploy:
    needs: [build-backend, build-frontend]
    runs-on: ubuntu-latest
    steps:
      - run: ssh deploy@api.ma2e.ci 'cd /opt/ma2e && docker-compose pull && docker-compose up -d'
```

---

## ⚠️ Avant la mise en prod

- [ ] Business Verification Meta validée (limite 250 destinataires/24h levée)
- [ ] Templates HSM `dossier_valide`, `dossier_rejete`, `complement_requis` approuvés par Meta
- [ ] Déclaration ARTCI déposée
- [ ] AIPD produite
- [ ] DPO MA2E désigné
- [ ] Politique de confidentialité publiée
- [ ] MFA TOTP activé pour comptes admin back-office
- [ ] Pen test externe effectué (exigence PRD §11)
- [ ] Plan de continuité (RPO 1h / RTO 4h) testé

---

## 📞 Contacts

- **Tech lead** : A. Siriki OUATTARA — GS2E / ERANOVE
- **Dev** : Flora Ebah
- **Issues** : https://github.com/Flora-Ebah/aya_ma2e/issues
