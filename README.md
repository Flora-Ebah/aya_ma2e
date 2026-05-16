# MA2E — Plateforme Digitale d'Identification des Sociétaires

**POC v0.1** — Implémentation pragmatique du PRD MA2E v1.0 (A. Siriki OUATTARA, GS2E/ERANOVE — Mai 2026)

> Mutuelle des Agents de l'Eau et de l'Électricité — Dématérialisation du parcours d'enrôlement et de mise à jour des dossiers sociétaires.

---

## Conformité au PRD MA2E v1.0

| Exigence PRD | Implémentation POC |
|---|---|
| § 6.1 — Conversation WhatsApp + state machine | ✅ FastAPI + Redis sessions + 14 états |
| § 6.2 — Consentement & droits ARTCI | ✅ Texte versionné, hash, HMAC, commande `DROITS` |
| § 6.3 — Pipeline OCR/MRZ | ✅ **Mock Mindee** + parser MRZ ICAO 9303 simulé _(Mindee réel : Sprint 2)_ |
| § 6.4 — Données professionnelles | ✅ Matricule + employeur (liste fermée) + fonction + ancienneté + situation |
| § 6.6 — Back-office gestion | ✅ Liste filtrée, vue OCR vs saisie, validation/rejet/complément |
| § 6.7 — Sécurité & audit | ✅ JWT + RBAC + journal append-only avec hash chaîné |
| § 8 — 14 étapes + 3 GATES | ✅ Implémentés dans `app/conversation/state_machine.py` |
| § 9 — Modèle 14 entités | ✅ 11 entités implémentées (Dossier, Consentement, TexteConsentement, PieceIdentite, DonneesPro, Employeur, EndUser, AuditLog, Conversation, Message, Tenant) |
| § 10.3 — Audit immuable hash chaîné | ✅ SHA-256 chaîné sur chaque entrée |
| § 10.4 — Consentement versionné signé | ✅ Versionning + content_hash + HMAC-SHA256 |

### Choix de stack pour le POC

Le PRD spécifie **Laravel 11 + MySQL 8 + React** pour la production. Le POC est livré en **FastAPI + PostgreSQL 16 + Next.js 14** pour les raisons suivantes :

- Time-to-validation court (équipe solo, démo J+1)
- Écosystème Python optimal pour le pipeline OCR/IA
- Architecture découplée (state machine, services, API) → migration Laravel maîtrisée en Sprint dédié
- PostgreSQL + pgvector permet de tester la base de connaissances RAG (Epic IA, V2 PRD)

**Le périmètre fonctionnel et la conformité ARTCI sont 100% alignés au PRD.**

---

## Architecture

```
virtual-ai/
├── README.md
├── docker-compose.yml          ← Postgres + Redis + MinIO
│
├── backend/                    ← FastAPI Python 3.11
│   └── app/
│       ├── core/               ← config, db, redis, storage, security, tenancy
│       ├── models/             ← Tenant, Dossier, Consentement, PieceIdentite, AuditLog…
│       ├── services/           ← ocr_mock, consent_service, audit_service, dossiers
│       ├── conversation/       ← state_machine (14 étapes), llm Groq
│       ├── webhooks/           ← WhatsApp Meta + Telegram
│       └── api/                ← auth, tenants, dossiers, me
│
├── frontend/                   ← Next.js 14 + Tailwind
│   └── app/
│       ├── login/              ← auth
│       └── dossiers/           ← liste + détail (OCR vs saisie, consents, actions)
│
├── seeds/seed.py               ← MA2E + ARTCI v1.0 + employeurs + comptes
└── scripts/                    ← setup webhooks Telegram/WhatsApp
```

---

## Démarrage rapide

### 1. Pré-requis
- Docker Desktop · Python 3.11+ · Node.js 20+ · ngrok

### 2. Configuration
```bash
cp backend/.env.example backend/.env
cp frontend/.env.local.example frontend/.env.local
```

Édite `backend/.env` au minimum :
- `GROQ_API_KEY` (clé Groq, gratuite)
- `TELEGRAM_TOKEN_MA2E` (ou WhatsApp)
- `PUBLIC_WEBHOOK_URL` (URL ngrok)
- `JWT_SECRET` (à changer)

### 3. Infra
```bash
docker compose up -d
```

### 4. Backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/Mac

pip install -e .
python -m app.bootstrap         # crée tables + pgvector
cd .. && python seeds/seed.py   # seed MA2E + ARTCI v1.0

cd backend && uvicorn app.main:app --reload --port 8000
```

### 5. Frontend (autre terminal)
```bash
cd frontend
npm install
npm run dev
```
→ http://localhost:3000

### 6. Exposition webhook (autre terminal)
```bash
ngrok http 8000
# Copier l'URL HTTPS dans backend/.env (PUBLIC_WEBHOOK_URL)
# Puis :
python scripts/setup_telegram_webhook.py
```

---

## Comptes de démo

| Rôle | Email | Mot de passe |
|---|---|---|
| Super admin GS2E | `admin@gs2e.ci` | `admin123` |
| Admin MA2E | `admin@ma2e.ci` | `ma2e123` |
| Agent MA2E | `agent@ma2e.ci` | `agent123` |

---

## Scénario de démo (script)

### Acte 1 — Le parcours sociétaire (WhatsApp/Telegram)
1. Le sociétaire **Awa** envoie "Bonjour" → accueil multilingue
2. **🛑 GATE 1** — Texte ARTCI complet → "1. J'accepte"
3. Numéro de matricule : `SODE-2018-4521`
4. Sélection employeur : `SODECI`
5. Fonction : `Technicienne réseau`
6. Ancienneté : `12`
7. Situation : `2 — Mariée`
8. Type pièce : `1 — CNI UEMOA`
9. Photo recto envoyée → **mock OCR** retourne nom/prénom/N° pièce en 2 sec
10. Photo verso envoyée → **mock MRZ ICAO 9303** retourne données chaînées
11. **🛑 GATE 2** — Validation OCR → "1. Correct"
12. Récapitulatif complet
13. **🛑 GATE 3** — Certification → "1. Je certifie"
14. 🎉 Dossier `MA2E-2026-000001` créé et transmis

### Acte 2 — Le back-office MA2E (Next.js)
1. Login `admin@ma2e.ci`
2. Dashboard : KPIs (Total / Soumis / En validation / Validés / Rejetés)
3. Clic sur le dossier `MA2E-2026-000001`
4. Vue détaillée :
   - **Données pro** structurées
   - **OCR recto** ↔ **MRZ verso** côte à côte
   - **Consentements ARTCI** signés (3 gates, version 1.0, hash visible)
5. Clic "Valider" → statut bascule, audit log enrichi

### Acte 3 — La conformité (point différenciant)
1. Montrer la table `audit_logs` (via `/docs` Swagger) → chaîne de hash
2. Montrer la signature HMAC d'un consentement
3. Montrer la table `textes_consentement` versionnée

### Acte 4 — L'extension groupe
1. Login `admin@gs2e.ci` (super admin)
2. Switcher de tenant : voir MA2E actif + CIE/SODECI placeholder (`is_active=false`)
3. Argument : "L'architecture est prête. Onboarder CIE = 30 min de configuration."

---

## Points de différenciation vs autre proposition

| | Autre POC | **Notre POC** |
|---|---|---|
| State machine | Probablement linéaire | **14 états + 3 GATES + commandes globales (AIDE/DROITS/ANNULER)** |
| Consentement | Booléen simple | **Versionné, hashé, signé HMAC, audit chaîné** |
| OCR | Statique ou indispo | **Mock Mindee fidèle + MRZ ICAO 9303** |
| Audit | Logs applicatifs | **Append-only avec hash chaîné vérifiable** |
| Back-office | Liste simple | **OCR vs MRZ côte à côte, modal validation/rejet/complément** |
| Vision groupe | MA2E seul | **Multi-tenant prêt, MA2E pilote, CIE/SODECI roadmap visible** |
| Conformité PRD | Approximative | **Mapping complet exigence par exigence (voir tableau ci-dessus)** |

---

## URLs locales

| Service | URL |
|---|---|
| Frontend MA2E | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| Swagger docs | http://localhost:8000/docs |
| MinIO console | http://localhost:9001 (minioadmin / minioadmin) |

---

## Roadmap post-démo

| Sprint | Livrable |
|---|---|
| Sprint 0 | AIPD + déclaration ARTCI + finalisation infra |
| Sprint 1 | Migration Laravel 11 (parité fonctionnelle) |
| Sprint 2 | Intégration **Mindee** réel (remplacement du mock OCR) |
| Sprint 3-4 | Portail Web sociétaire + OTP SMS/WhatsApp |
| Sprint 5-7 | Back-office complet + tableau de bord productivité |
| Sprint 8 | Tesseract V2 souverain (fallback Mindee) |
| Sprint 9-10 | Onboarding CIE + SODECI |
| Sprint 11-12 | Module MARCEL IA (Claude API) — Epic IA V2 |

---

*Auteur : A. Siriki OUATTARA · Mai 2026 · MA2E / GS2E / ERANOVE*
