# syntax=docker/dockerfile:1.6
# ===========================================================================
# Image production — multi-stage pour minimiser la taille finale.
#
# Stage 1 (builder) : installe les deps Python en mode wheel
# Stage 2 (runtime) : copie les wheels + le code, user non-root, healthcheck
#
# Usage local :
#   docker build -t ma2e-backend:dev -f backend/Dockerfile backend
#   docker run -p 8000:8000 --env-file backend/.env ma2e-backend:dev
# ===========================================================================

# ---------- Stage 1 : builder ------------------------------------------- #
FROM python:3.13-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Build deps : nécessaires pour psycopg2 (libpq) + Pillow (zlib)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        zlib1g-dev \
        libjpeg62-turbo-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements.txt .
RUN pip wheel --wheel-dir /wheels -r requirements.txt


# ---------- Stage 2 : runtime ------------------------------------------- #
FROM python:3.13-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APP_ENV=production \
    PORT=8000

# Runtime libs uniquement (pas de build-essential)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        libjpeg62-turbo \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r ma2e && useradd -r -g ma2e -d /app -s /sbin/nologin ma2e

WORKDIR /app

# Installe les wheels pré-buildées (rapide, reproductible)
COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN pip install --no-index --find-links /wheels -r requirements.txt \
    && rm -rf /wheels

# Code applicatif
COPY app ./app
COPY seeds ./seeds
COPY alembic.ini ./
COPY alembic ./alembic

# Navigateurs Playwright pour le scraper SPA (scraper_spa.py)
# Installés en root dans un cache système pour que l'utilisateur ma2e puisse les lire.
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN playwright install --with-deps chromium \
    && chmod -R a+rX /ms-playwright

# Permissions non-root
RUN chown -R ma2e:ma2e /app
USER ma2e

EXPOSE 8000

# Healthcheck Docker (k8s/Container Apps utilisent leurs propres probes via
# /health/liveness et /health/readiness — ce HEALTHCHECK est pour `docker ps`)
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -fsS "http://localhost:${PORT}/health/liveness" || exit 1

# Production : uvicorn avec un seul worker (les orchestrateurs scaleront en
# horizontal en démarrant plusieurs containers — c'est plus prévisible que
# uvicorn --workers N qui forke).
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips=*"]
