# syntax=docker/dockerfile:1.7
# ─────────────────────────────────────────────────────────────────────────
# MA2E Frontend — Next.js 14 (App Router, output: standalone)
#
# Build multi-stage pour image finale ~150 MB :
#   1. deps     → installe uniquement les dépendances de prod
#   2. builder  → build Next.js (génère .next/standalone)
#   3. runner   → image finale légère, user non-root, port 3001
# ─────────────────────────────────────────────────────────────────────────

# ─── Stage 1 : deps ──────────────────────────────────────────────────────
FROM node:20-alpine AS deps
WORKDIR /app

# libc6-compat est requis par certains paquets Node compilés sur Alpine
RUN apk add --no-cache libc6-compat

# Copie uniquement les manifests pour exploiter le cache Docker
COPY package.json package-lock.json* ./
RUN npm ci --only=production --no-audit --no-fund


# ─── Stage 2 : builder ───────────────────────────────────────────────────
FROM node:20-alpine AS builder
WORKDIR /app

# Variables NEXT_PUBLIC_* — figées au build (embedded dans le bundle JS).
# À passer avec --build-arg lors du `docker build`.
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

# Récupère les deps de prod déjà installées
COPY --from=deps /app/node_modules ./node_modules

# Copie tout le code source
COPY . .

# Installe aussi les devDependencies pour le build (typescript, tailwind, etc.)
RUN npm install --no-audit --no-fund

# Build Next.js — génère .next/standalone et .next/static
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build


# ─── Stage 3 : runner (image finale) ─────────────────────────────────────
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3001
ENV HOSTNAME=0.0.0.0

# User non-root pour la sécurité
RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

# Copie les artefacts du build standalone
# .next/standalone contient server.js + node_modules réduits + package.json
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs

EXPOSE 3001

# Healthcheck (vérifie que Next.js répond)
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:3001/ || exit 1

# Lance le server standalone (pas besoin de next start, plus léger)
CMD ["node", "server.js"]
