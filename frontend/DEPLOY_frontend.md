# 🚀 Déploiement MA2E Frontend

> Guide de déploiement du back-office Next.js 14 (MA2E).
> Stack : Next.js 14 (App Router) · TypeScript · Tailwind CSS · React 18

---

## 📋 Sommaire

1. [Prérequis](#1-prérequis)
2. [Variables d'environnement](#2-variables-denvironnement)
3. [Build & déploiement Docker](#3-build--déploiement-docker)
4. [Déploiement Azure App Service (alternative)](#4-déploiement-azure-app-service-alternative)
5. [Vérifications post-déploiement](#5-vérifications-post-déploiement)
6. [Troubleshooting](#6-troubleshooting)

---

## 1. Prérequis

| Composant | Version | Notes |
|---|---|---|
| Node.js | **20+** (LTS) | Si build hors Docker |
| Backend MA2E | déployé et accessible | URL HTTPS à fournir via `NEXT_PUBLIC_API_URL` |

L'image Docker fait tout — pas besoin d'installer Node localement si on déploie via conteneur.

---

## 2. Variables d'environnement

À configurer dans **Azure App Service → Configuration → Application settings**
(ou en variables Docker `--env`).

```env
# URL publique du backend FastAPI (impérative)
NEXT_PUBLIC_API_URL=https://api.ma2e.ci

# (optionnel) — si frontend déployé sur un sous-domaine séparé
NEXT_PUBLIC_APP_URL=https://app.ma2e.ci
```

⚠️ Les variables `NEXT_PUBLIC_*` sont **embarquées dans le bundle JavaScript
côté navigateur**. Ne jamais y mettre de secret. Pour des secrets côté
serveur, utiliser des variables sans le préfixe `NEXT_PUBLIC_`.

---

## 3. Build & déploiement Docker

### 3.1 Build local

```bash
cd frontend
docker build -t ma2e-frontend:latest .
```

Sortie attendue (multi-stage) :
```
Step 1/N : FROM node:20-alpine AS deps
...
Successfully built abc123def456
Successfully tagged ma2e-frontend:latest
```

Taille de l'image finale : **~150 MB** (grâce à `output: "standalone"` Next.js).

### 3.2 Run local (test)

```bash
docker run -d \
  --name ma2e-frontend \
  -p 3001:3001 \
  -e NEXT_PUBLIC_API_URL=http://host.docker.internal:8000 \
  ma2e-frontend:latest

# Vérifie
curl http://localhost:3001
# Doit renvoyer le HTML de la page d'accueil
```

### 3.3 Push de l'image vers Azure Container Registry

```bash
# Authentification
az acr login --name ma2eRegistry

# Tag pour ACR
docker tag ma2e-frontend:latest ma2eRegistry.azurecr.io/ma2e-frontend:latest

# Push
docker push ma2eRegistry.azurecr.io/ma2e-frontend:latest
```

### 3.4 Déploiement sur Azure App Service (conteneur)

```bash
az webapp create \
  --resource-group MA2E-RG \
  --plan MA2E-Plan \
  --name ma2e-frontend \
  --deployment-container-image-name ma2eRegistry.azurecr.io/ma2e-frontend:latest

az webapp config appsettings set \
  --resource-group MA2E-RG \
  --name ma2e-frontend \
  --settings NEXT_PUBLIC_API_URL=https://api.ma2e.ci WEBSITES_PORT=3001
```

> Important : **`WEBSITES_PORT=3001`** pour qu'Azure route correctement vers
> le port exposé par le conteneur.

---

## 4. Déploiement Azure App Service (alternative sans Docker)

Si l'équipe préfère ne pas passer par Docker :

```bash
az webapp up \
  --name ma2e-frontend \
  --resource-group MA2E-RG \
  --runtime "NODE:20-lts" \
  --location eastus2

az webapp config set \
  --resource-group MA2E-RG \
  --name ma2e-frontend \
  --startup-file "npm start"

az webapp config appsettings set \
  --resource-group MA2E-RG \
  --name ma2e-frontend \
  --settings NEXT_PUBLIC_API_URL=https://api.ma2e.ci
```

L'App Service exécutera automatiquement :
```bash
npm install
npm run build
npm start
```

---

## 5. Vérifications post-déploiement

### 5.1 Page d'accueil
```bash
curl -I https://app.ma2e.ci
# HTTP/2 200
```

### 5.2 Test de login

Ouvrir `https://app.ma2e.ci/login` et se connecter avec :

| Email | Mot de passe | Rôle |
|---|---|---|
| `admin@gs2e.ci` | `admin123` | Super Admin (tous tenants) |
| `admin@ma2e.ci` | `ma2e123` | Tenant Admin MA2E |
| `agent@ma2e.ci` | `agent123` | Agent MA2E (validation dossiers) |
| `viewer@ma2e.ci` | `viewer123` | **Viewer lecture-seule** |

### 5.3 Smoke test interactif

1. Login en tant qu'admin → voir les pages :
   - `/dossiers` (liste vide au début)
   - `/parametres/integrations` (services activables)
   - `/assistante/parcours` (workflows conversationnels)

2. Login en tant que viewer → vérifier que :
   - Les pages se chargent en lecture
   - Les boutons d'action (valider, modifier…) sont grisés ou renvoient 403

---

## 6. Troubleshooting

### `Error: Cannot find module '/app/server.js'`

L'option `output: "standalone"` n'est pas activée dans `next.config.mjs`.
Vérifier qu'elle est bien présente :
```js
const nextConfig = {
  output: "standalone",   // ← doit être là
  ...
};
```

### Le frontend ne contacte pas le backend

1. Vérifier `NEXT_PUBLIC_API_URL` est bien défini AU BUILD (le `NEXT_PUBLIC_*`
   est figé dans le bundle au moment du `npm run build`).
2. Pour Docker : il faut passer la variable en `--build-arg` OU rebuild
   l'image avec la bonne valeur. Au runtime, c'est trop tard pour
   `NEXT_PUBLIC_*`.

Solution : passer un argument de build :

```dockerfile
# Dans le Dockerfile, ajouter avant le RUN npm run build :
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
```

Et build avec :
```bash
docker build \
  --build-arg NEXT_PUBLIC_API_URL=https://api.ma2e.ci \
  -t ma2e-frontend:latest .
```

### CORS errors dans la console navigateur

Le backend doit autoriser l'origine du frontend. Vérifier sur le backend :
```env
CORS_ALLOWED_ORIGINS=https://app.ma2e.ci
```

### Image Docker trop grosse (> 500 MB)

`output: "standalone"` doit être activé. Sans lui, l'image embarque tout
`node_modules` (souvent 400+ MB). Avec, elle tombe à ~150 MB.

---

## 📧 Support

Pour toute question : **Abdoul Bakary OUATTARA** — `ouattaraab@gmail.com`
