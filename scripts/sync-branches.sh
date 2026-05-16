#!/usr/bin/env bash
# Synchronise les branches `backend` et `frontend` depuis `main`.
#
# Usage :
#   bash scripts/sync-branches.sh
#
# Prérequis : être sur `main` avec un working tree propre (rien de non-committé).

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}🔄 Synchronisation branches backend / frontend depuis main${NC}"

# 1. Vérifications préalables
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo -e "${RED}❌ Working tree non propre. Committez ou stashez d'abord.${NC}"
  exit 1
fi

CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "main" ]; then
  echo -e "${YELLOW}ℹ️  Vous êtes sur '$CURRENT_BRANCH', bascule sur main…${NC}"
  git checkout main
fi

# 2. S'assurer que main est à jour avec origin
echo -e "${YELLOW}📥 Pull main depuis origin…${NC}"
git pull origin main

# 3. Sync branche backend
echo -e "${YELLOW}🐍 Sync branche backend…${NC}"
git checkout backend
git reset --hard main
git rm -rf frontend/ 2>/dev/null || true
git commit -m "sync: backend $(date +%Y-%m-%d-%H%M)" || echo "  (rien à committer)"
git push origin backend --force-with-lease

# 4. Sync branche frontend
echo -e "${YELLOW}⚛️  Sync branche frontend…${NC}"
git checkout frontend
git reset --hard main
git rm -rf backend/ scripts/ seeds/ docker-compose.yml 2>/dev/null || true
git commit -m "sync: frontend $(date +%Y-%m-%d-%H%M)" || echo "  (rien à committer)"
git push origin frontend --force-with-lease

# 5. Retour sur main
git checkout main

echo -e "${GREEN}✅ Branches backend + frontend synchronisées depuis main${NC}"
echo -e "${GREEN}   Le DevOps peut redéployer.${NC}"
