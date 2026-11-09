"""Génère PROJETS_FLO.docx — document paysage listant les projets Flora.

Structure :
- Page 1 : page de garde (titre + auteur + date)
- Page 2 : sommaire visuel (1, 2, 3, 4 en grand)
- Pages 3-5 : Projet 1 MA2E (contexte, archi, stack, workflows, sécu)
- Placeholders pour projets 2, 3, 4 (à compléter plus tard)

Format A4 paysage, Times New Roman noir, tables sans couleur (règle MA2E).
"""
from __future__ import annotations

import datetime as _dt
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENTATION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

FONT = "Times New Roman"
BLACK = RGBColor(0, 0, 0)


# ---------------------------------------------------------------------------
# Helpers typographiques
# ---------------------------------------------------------------------------
def _force_run(run, size: float = 12, bold: bool = False, italic: bool = False):
    run.font.name = FONT
    run.font.size = Pt(size)
    run.font.color.rgb = BLACK
    run.bold = bold
    run.italic = italic
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rFonts.set(qn(attr), FONT)


def _set_landscape(section, margin_cm: float = 2.0):
    """Passe une section en A4 paysage avec marges de `margin_cm`."""
    section.orientation = WD_ORIENTATION.LANDSCAPE
    section.page_width, section.page_height = Cm(29.7), Cm(21.0)
    section.top_margin = section.bottom_margin = Cm(margin_cm)
    section.left_margin = section.right_margin = Cm(margin_cm)


def _set_doc_defaults(doc):
    style = doc.styles["Normal"]
    style.font.name = FONT
    style.font.size = Pt(12)
    style.font.color.rgb = BLACK
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.insert(0, rfonts)
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rfonts.set(qn(attr), FONT)


def _add_par(doc, text: str, *, size: float = 12, bold: bool = False,
             italic: bool = False, align=WD_ALIGN_PARAGRAPH.LEFT,
             space_after: float = 6):
    p = doc.add_paragraph()
    p.alignment = align
    p.paragraph_format.space_after = Pt(space_after)
    r = p.add_run(text)
    _force_run(r, size=size, bold=bold, italic=italic)
    return p


def _add_heading(doc, text: str, level: int = 1):
    """Titre simple, sans utiliser Heading Word (couleurs Word par défaut)."""
    sizes = {1: 18, 2: 14, 3: 12}
    _add_par(doc, text, size=sizes.get(level, 12), bold=True,
             space_after=10 if level == 1 else 6)


def _add_page_break(doc):
    p = doc.add_paragraph()
    r = p.add_run()
    r.add_break(WD_BREAK.PAGE)


def _bullet(doc, text: str, size: float = 11):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(3)
    r = p.add_run(text)
    _force_run(r, size=size)


# ---------------------------------------------------------------------------
# Sections du document
# ---------------------------------------------------------------------------
def cover_page(doc):
    """Page 1 : garde. Titre centré, auteur, date."""
    for _ in range(4):
        doc.add_paragraph()
    _add_par(doc, "PROJETS", size=72, bold=True,
             align=WD_ALIGN_PARAGRAPH.CENTER, space_after=0)
    _add_par(doc, "Portefeuille technique — Flora EBAH", size=20,
             align=WD_ALIGN_PARAGRAPH.CENTER, space_after=40)
    for _ in range(6):
        doc.add_paragraph()
    _add_par(doc, "Fondation Développeur · GS2E",
             size=14, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER,
             space_after=0)
    _add_par(doc, _dt.date.today().strftime("%d %B %Y"),
             size=12, align=WD_ALIGN_PARAGRAPH.CENTER)
    _add_page_break(doc)


def toc_page(doc):
    """Page 2 : sommaire avec 4 grands chiffres sur 2×2."""
    _add_par(doc, "Sommaire", size=24, bold=True,
             align=WD_ALIGN_PARAGRAPH.CENTER, space_after=20)

    projects = [
        ("1", "MA2E — Plateforme digitale d'identification"),
        ("2", "SNVC — Notification & vérification des contraventions"),
        ("3", "Emargeo — Émargement digital & CR automatisé"),
        ("4", "ES-CRC SODECI — Enquête satisfaction client centralisée"),
    ]

    # Tableau 2×2, cellules larges avec un gros chiffre + libellé
    table = doc.add_table(rows=2, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    for row in table.rows:
        row.height = Cm(7)
        for cell in row.cells:
            cell.width = Cm(12)

    for idx, (num, title) in enumerate(projects):
        cell = table.rows[idx // 2].cells[idx % 2]
        cell.text = ""  # reset default
        p_num = cell.paragraphs[0]
        p_num.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_num = p_num.add_run(num)
        _force_run(r_num, size=110, bold=True)
        p_title = cell.add_paragraph()
        p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_title = p_title.add_run(title)
        _force_run(r_title, size=13, italic=True)

    _add_page_break(doc)


def project_1_ma2e(doc):
    """Pages 3-5 : Projet 1 — MA2E, vue développeur."""
    # ── En-tête du projet
    _add_par(doc, "1", size=72, bold=True,
             align=WD_ALIGN_PARAGRAPH.LEFT, space_after=0)
    _add_par(doc, "MA2E — Plateforme digitale d'identification",
             size=22, bold=True, space_after=4)
    _add_par(doc, "Mutuelle des Agents de l'Eau et de l'Électricité · "
             "canaux WhatsApp + Web · conformité ARTCI (loi 2013-450)",
             size=11, italic=True, space_after=14)

    # ── Contexte (bloc court)
    _add_heading(doc, "Contexte métier", level=2)
    _add_par(doc,
             "Dématérialiser l'inscription des sociétaires du groupe GS2E "
             "(CIE, SODECI, ERANOVE, SMB…) sur un parcours conversationnel "
             "de bout en bout : identité, OCR de la pièce, consentements "
             "ARTCI, validation par un gestionnaire, notification au "
             "sociétaire. Cible démo : 15 mai 2026.",
             size=11)

    # ── Architecture (schéma en texte)
    _add_heading(doc, "Architecture logicielle", level=2)
    archi = doc.add_table(rows=1, cols=3)
    archi.autofit = False
    archi.alignment = WD_TABLE_ALIGNMENT.CENTER
    labels = [
        ("Frontend", "Next.js 14 (App Router)\nTypeScript · Tailwind\n"
         "Back-office agents + chat public\nhttpOnly cookies + CSRF"),
        ("Backend", "FastAPI async · SQLAlchemy 2.0\nWorkflow engine + RBAC\n"
         "Rate-limit Redis · PII scrub\nOCR multi-provider"),
        ("Data & infra", "PostgreSQL 16 + pgvector (RAG)\n"
         "Redis (sessions, JTI)\nMinIO S3 (pièces d'identité)\n"
         "Docker · Nginx · Alembic"),
    ]
    for i, (title, body) in enumerate(labels):
        cell = archi.rows[0].cells[i]
        cell.width = Cm(8)
        cell.text = ""
        pt = cell.paragraphs[0]
        pt.alignment = WD_ALIGN_PARAGRAPH.CENTER
        rt = pt.add_run(title)
        _force_run(rt, size=13, bold=True)
        pb = cell.add_paragraph()
        pb.alignment = WD_ALIGN_PARAGRAPH.CENTER
        rb = pb.add_run(body)
        _force_run(rb, size=10)
    _apply_table_grid(archi)
    doc.add_paragraph()

    _add_par(doc,
             "Flux principal : navigateur / WhatsApp → Nginx → FastAPI → "
             "workflow_executor → actions backend (OCR, notif, RAG) → "
             "PostgreSQL + Redis + MinIO. Meta Cloud API pour l'envoi "
             "WhatsApp sortant ; Azure OpenAI/Vision pour l'IA.",
             size=11)

    _add_page_break(doc)

    # ── Stack technique (tableau)
    _add_heading(doc, "Stack technique", level=2)
    stack = [
        ("Langage",       "Python 3.13 (backend) · TypeScript 5 (frontend)"),
        ("Framework web", "FastAPI 0.115 · Next.js 14"),
        ("Persistance",   "PostgreSQL 16 + pgvector · SQLAlchemy 2 async · Alembic"),
        ("Cache/queue",   "Redis 7 (rate-limit, refresh JTI, cache TTL)"),
        ("Storage",       "MinIO (S3-compatible), chiffrement au repos"),
        ("IA / OCR",      "Azure OpenAI (gpt-5.4-mini) · Azure AI Vision · "
                          "OCR.space (fallback) · pgvector 1536 dims"),
        ("Canaux",        "Meta WhatsApp Cloud API · Web chat React · Telegram (option)"),
        ("Sécurité",      "JWT httpOnly + refresh rotation · CSRF double-submit · "
                          "RBAC modules×actions · MFA TOTP · audit hash chaîné"),
        ("DevOps",        "Docker Compose · Alembic migrations · Nginx reverse proxy"),
    ]
    t = doc.add_table(rows=len(stack), cols=2)
    t.autofit = False
    for i, (k, v) in enumerate(stack):
        row = t.rows[i]
        row.cells[0].width = Cm(4.5)
        row.cells[1].width = Cm(20)
        row.cells[0].text = ""
        p1 = row.cells[0].paragraphs[0]
        r1 = p1.add_run(k)
        _force_run(r1, size=11, bold=True)
        row.cells[1].text = ""
        p2 = row.cells[1].paragraphs[0]
        r2 = p2.add_run(v)
        _force_run(r2, size=11)
    _apply_table_grid(t)
    doc.add_paragraph()

    # ── Workflows métier
    _add_heading(doc, "Parcours conversationnels (moteur maison)", level=2)
    _add_par(doc,
             "Le moteur de workflow est configurable via l'UI back-office "
             "(pas de code) : steps typés (message, question, action, décision), "
             "templates avec variables dynamiques, branches conditionnelles, "
             "routing inter-parcours. 4 parcours actifs :",
             size=11)
    _bullet(doc, "Inscription sociétaire — 180 étapes, OCR CNI, MRZ ICAO 9303, "
                 "validation croisée nom/prénom, 3 consentements ARTCI signés HMAC-SHA256.")
    _bullet(doc, "Consultation de dossier — recherche par matricule, statut, dates.")
    _bullet(doc, "Mise à jour d'infos — email, téléphone, adresse, RIB, situation familiale.")
    _bullet(doc, "Chat libre (FAQ) — RAG sur base de connaissances vectorisée (pgvector).")

    _add_page_break(doc)

    # ── Sécurité & conformité
    _add_heading(doc, "Sécurité & conformité ARTCI", level=2)
    _bullet(doc, "Authentification : cookie ma2e_token httpOnly + Secure + SameSite ; "
                 "refresh token en rotation Redis (GETDEL atomique anti-replay).")
    _bullet(doc, "CSRF : double-submit token ; middleware refuse toute mutation "
                 "sans header X-CSRF-Token matchant le cookie.")
    _bullet(doc, "Rate-limit Redis : 9 buckets (login, MFA, exports, refresh…) "
                 "avec verrouillage applicatif 5 essais / 15 min.")
    _bullet(doc, "RBAC dynamique : rôles métier configurables via UI, "
                 "matrice modules × actions (validation, reporting, admin, audit, conformité).")
    _bullet(doc, "Audit trail append-only + hash chaîné SHA-256 → détection de "
                 "manipulation post-hoc (loi 2013-450, art. 34).")
    _bullet(doc, "PII scrubber structlog : emails, CNI ivoiriens, matricules et "
                 "téléphones masqués dans tous les logs (RGPD/ARTCI).")
    _bullet(doc, "MFA TOTP compatible Google Authenticator / Authy.")

    # ── Défis techniques
    _add_heading(doc, "Défis techniques résolus", level=2)
    _bullet(doc, "Workflow engine dynamique — steps + templates + branches "
                 "modifiables en production sans redéploiement.")
    _bullet(doc, "OCR multi-provider avec vérification anti-fraude "
                 "(cohérence identité recto/verso vs numéro déclaré vs MRZ).")
    _bullet(doc, "Routing inter-parcours au runtime (menu principal → "
                 "workflow cible, avec reprise d'état par step_code).")
    _bullet(doc, "Frontend refactor : 21 pages ramenées sous 250 lignes chacune, "
                 "lib UI 11 composants, layout unifié route group (app).")

    # ── Livrables
    _add_heading(doc, "Livrables & métriques", level=2)
    _bullet(doc, "20 580 lignes Python backend · 37 services · 20 endpoints REST.")
    _bullet(doc, "21 pages Next.js refactorisées · 11 composants UI · design tokens.")
    _bullet(doc, "4 workflows conversationnels · 180 étapes seedées · 172 templates.")
    _bullet(doc, "5 rôles RBAC · 5 modules audités · MFA optionnel.")

    _add_page_break(doc)


def project_2_snvc(doc):
    """Pages 6-8 : Projet 2 — SNVC (Notification & Vérification des Contraventions)."""
    # ── En-tête
    _add_par(doc, "2", size=72, bold=True,
             align=WD_ALIGN_PARAGRAPH.LEFT, space_after=0)
    _add_par(doc, "SNVC — Système de Notification & Vérification des Contraventions",
             size=22, bold=True, space_after=4)
    _add_par(doc, "GS2E · plateforme B2B multi-tenant · canaux WhatsApp + Web + "
             "Telegram · assistant RAG intégré",
             size=11, italic=True, space_after=14)

    # ── Contexte
    _add_heading(doc, "Contexte métier", level=2)
    _add_par(doc,
             "Digitaliser la gestion des contraventions pour les gestionnaires "
             "de flottes GS2E : import en masse de PV (Excel/CSV), notification "
             "automatique des conducteurs par email, consultation sécurisée par "
             "le conducteur via WhatsApp ou chat web (auth OTP email). Un "
             "assistant conversationnel RAG répond aux questions réglementaires.",
             size=11)

    # ── Architecture
    _add_heading(doc, "Architecture logicielle", level=2)
    archi = doc.add_table(rows=1, cols=3)
    archi.autofit = False
    archi.alignment = WD_TABLE_ALIGNMENT.CENTER
    labels = [
        ("Frontend", "Next.js 14 (App Router)\nTypeScript · Tailwind\n"
         "12 pages : upload, flotte,\naudit, conversations, chat"),
        ("Backend", "FastAPI async · SQLAlchemy 2\nÉtat : machine à états\n"
         "conversationnelle (786 l.)\nOCR multi-fournisseurs"),
        ("Data & infra", "PostgreSQL 16 + pgvector\nRedis 7 · MinIO S3\n"
         "Docker multi-stage\nDéploiement Railway"),
    ]
    for i, (title, body) in enumerate(labels):
        cell = archi.rows[0].cells[i]
        cell.width = Cm(8)
        cell.text = ""
        pt = cell.paragraphs[0]
        pt.alignment = WD_ALIGN_PARAGRAPH.CENTER
        rt = pt.add_run(title)
        _force_run(rt, size=13, bold=True)
        pb = cell.add_paragraph()
        pb.alignment = WD_ALIGN_PARAGRAPH.CENTER
        rb = pb.add_run(body)
        _force_run(rb, size=10)
    _apply_table_grid(archi)
    doc.add_paragraph()

    _add_par(doc,
             "Monolithe modulaire orienté services, séparé en 2 repos "
             "(front / back). Multi-tenant strict via `tenant_id` sur toutes "
             "les tables métier (Tenant → User, Vehicule, Contravention, "
             "Conversation, KnowledgeSource…). Chaque canal (WhatsApp, "
             "Telegram, Web) est un webhook branché sur la même state machine.",
             size=11)

    _add_page_break(doc)

    # ── Stack
    _add_heading(doc, "Stack technique", level=2)
    stack = [
        ("Langage",       "Python 3.11 (backend) · TypeScript 5 (frontend)"),
        ("Framework web", "FastAPI · Next.js 14 (App Router)"),
        ("Persistance",   "PostgreSQL 16 + pgvector · SQLAlchemy 2 async · Alembic"),
        ("Cache",         "Redis 7 (OTP, rate-limit, cache session)"),
        ("Storage",       "MinIO (uploads Excel/CSV, chunks knowledge)"),
        ("IA / RAG",      "Azure OpenAI (GPT-4.1-mini · embeddings 1536) · "
                          "Groq · pgvector (multi-turn query rewrite)"),
        ("OCR",           "Azure AI Vision → OCR.space → Mindee (fallback en cascade)"),
        ("Canaux",        "WhatsApp Cloud API · Telegram Bot · Web chat · "
                          "SMTP Resend/Brevo (OTP email)"),
        ("Auth",          "JWT HS256 admin (python-jose, bcrypt) · "
                          "OTP email hashé pour end-users"),
        ("DevOps",        "Dockerfile multi-stage · Procfile · Railway"),
    ]
    t = doc.add_table(rows=len(stack), cols=2)
    t.autofit = False
    for i, (k, v) in enumerate(stack):
        row = t.rows[i]
        row.cells[0].width = Cm(4.5)
        row.cells[1].width = Cm(20)
        row.cells[0].text = ""
        p1 = row.cells[0].paragraphs[0]
        r1 = p1.add_run(k)
        _force_run(r1, size=11, bold=True)
        row.cells[1].text = ""
        p2 = row.cells[1].paragraphs[0]
        r2 = p2.add_run(v)
        _force_run(r2, size=11)
    _apply_table_grid(t)
    doc.add_paragraph()

    # ── Workflows
    _add_heading(doc, "Parcours & use-cases principaux", level=2)
    _bullet(doc, "Import PV en masse — POST `/api/contraventions/upload/stream` : "
                 "parsing Excel/CSV → création véhicule + contravention → envoi "
                 "email automatique (progression SSE temps réel).")
    _bullet(doc, "Gestion de flotte — CRUD référentiel véhicules + synchronisation "
                 "API tierce (`/api/contraventions/flotte/api-sync`).")
    _bullet(doc, "Consultation OTP conducteur — WhatsApp/Web : saisie plaque → "
                 "OTP email → liste des PV du véhicule (service `contraventions_otp`).")
    _bullet(doc, "Assistant RAG conversationnel — chat multi-turn avec query rewrite LLM, "
                 "recherche vectorielle pgvector, seuil de similarité configurable.")
    _bullet(doc, "Audit & conformité — logs et historique conversations "
                 "(`/api/audit/logs`, `/api/audit/conversations`).")

    _add_page_break(doc)

    # ── Sécurité
    _add_heading(doc, "Sécurité & auth", level=2)
    _bullet(doc, "Back-office : JWT HS256 signé (sub / tenant_id / role) · "
                 "expiration 1440 min · mots de passe bcrypt.")
    _bullet(doc, "End-users conducteurs : OTP email hashé + expiration + "
                 "compteur de tentatives (`ContraventionOTP`) — aucun compte "
                 "à créer côté conducteur.")
    _bullet(doc, "WhatsApp : verify token webhook Meta.")
    _bullet(doc, "Multi-tenant strict : isolation par `tenant_id` + slug sur "
                 "TOUTES les requêtes.")
    _bullet(doc, "À durcir en prod : politique CORS actuellement ouverte (`*`) → "
                 "whitelist des origines applicative.")

    # ── Points remarquables
    _add_heading(doc, "Points techniques remarquables", level=2)
    _bullet(doc, "Machine à états conversationnelle dédiée (786 lignes) : "
                 "menu principal → saisie email → validation OTP → questions/consultation.")
    _bullet(doc, "RAG multi-turn avec query rewrite LLM : reformulation contextuelle "
                 "de la question à partir de l'historique avant la recherche vectorielle.")
    _bullet(doc, "Streaming SSE pour les tâches longues (import massif, ingestion KB) — "
                 "l'utilisateur voit la progression ligne par ligne.")
    _bullet(doc, "OCR à 3 étages (Azure Vision → OCR.space → Mindee) : garantit "
                 "un résultat même si un fournisseur est down ou hors quota.")
    _bullet(doc, "Multi-canal unifié : la même state machine pilote WhatsApp, "
                 "Telegram et Web chat sans branchement spécial.")
    _bullet(doc, "Intégration flotte externe synchronisable — le référentiel "
                 "véhicules peut être re-synchronisé depuis une API tierce.")

    # ── Livrables
    _add_heading(doc, "Livrables & métriques", level=2)
    _bullet(doc, "≈ 6 963 lignes Python backend · 34 endpoints REST · "
                 "10+ tables SQL.")
    _bullet(doc, "≈ 8 454 lignes TypeScript frontend · 12 pages Next.js.")
    _bullet(doc, "Fichiers phares : `api/contraventions.py` (990 lignes), "
                 "`conversation/state_machine.py` (786 lignes).")
    _bullet(doc, "3 canaux d'entrée · 5 workflows métier · assistant RAG intégré.")

    _add_page_break(doc)


def project_3_emargeo(doc):
    """Pages 9-11 : Projet 3 — Emargeo (émargement digital + CR IA)."""
    # ── En-tête
    _add_par(doc, "3", size=72, bold=True,
             align=WD_ALIGN_PARAGRAPH.LEFT, space_after=0)
    _add_par(doc, "Emargeo — Émargement digital & compte-rendu automatisé",
             size=22, bold=True, space_after=4)
    _add_par(doc, "Groupe Eranove · monolithe Next.js full-stack · PWA offline · "
             "pipeline IA audio → transcription → CR Word",
             size=11, italic=True, space_after=14)

    # ── Contexte
    _add_heading(doc, "Contexte métier", level=2)
    _add_par(doc,
             "Digitaliser les feuilles de présence des réunions, formations "
             "et séminaires internes du groupe Eranove (énergie/eau, Afrique "
             "de l'Ouest) : QR code d'accès, signature manuscrite, calcul "
             "automatique des retards, génération de comptes-rendus par IA à "
             "partir de l'audio, export Word + envoi email aux participants.",
             size=11)

    # ── Architecture
    _add_heading(doc, "Architecture logicielle", level=2)
    archi = doc.add_table(rows=1, cols=3)
    archi.autofit = False
    archi.alignment = WD_TABLE_ALIGNMENT.CENTER
    labels = [
        ("Application", "Next.js 16 (App Router · RSC)\nReact 19 · TypeScript 5\n"
         "Pages back-office +\nroutes API unifiées"),
        ("Auth & sécu", "NextAuth v5 (JWT 24h)\nMiddleware Edge protégé\n"
         "RBAC double couche\nTokens opaques (public)"),
        ("Data & IA", "Prisma 7 + PostgreSQL\n28 modèles · 5 niveaux org\n"
         "Groq (Whisper + Llama)\nPWA · Service Worker"),
    ]
    for i, (title, body) in enumerate(labels):
        cell = archi.rows[0].cells[i]
        cell.width = Cm(8)
        cell.text = ""
        pt = cell.paragraphs[0]
        pt.alignment = WD_ALIGN_PARAGRAPH.CENTER
        rt = pt.add_run(title)
        _force_run(rt, size=13, bold=True)
        pb = cell.add_paragraph()
        pb.alignment = WD_ALIGN_PARAGRAPH.CENTER
        rb = pb.add_run(body)
        _force_run(rb, size=10)
    _apply_table_grid(archi)
    doc.add_paragraph()

    _add_par(doc,
             "Monolithe Next.js unifié — pas de backend Python séparé, "
             "les endpoints REST sont des `route.ts` dans App Router. "
             "Organisation feature-based (`components/{attendance, events, "
             "feedback, recordings, rooms, organisations, users}`). "
             "Hiérarchie organisationnelle stricte sur 5 niveaux : Group → "
             "Enterprise → Department → SubDirection → Service.",
             size=11)

    _add_page_break(doc)

    # ── Stack
    _add_heading(doc, "Stack technique", level=2)
    stack = [
        ("Framework",     "Next.js 16 (App Router, RSC) · React 19 · TypeScript 5"),
        ("Persistance",   "Prisma 7 + PostgreSQL (@prisma/adapter-pg) · 28 modèles"),
        ("Auth",          "NextAuth v5 Credentials + JWT 24h · bcryptjs · "
                          "Middleware Edge"),
        ("UI",            "Tailwind CSS v4 · shadcn/ui · Radix UI · lucide-react · "
                          "sonner · recharts"),
        ("PWA / offline", "Service Worker custom (public/sw.js) · Manifest · "
                          "Sync automatique (isOfflineSync + offlineId)"),
        ("Docs / export", "docx · docxtemplater · mammoth · @superdoc-dev/react · "
                          "exceljs · jspdf"),
        ("IA / média",    "Groq (Whisper large-v3-turbo) · Llama 3.3 70B · "
                          "ffmpeg-static (transcodage in-browser)"),
        ("Notif / QR",    "nodemailer · qrcode + @yudiel/react-qr-scanner · "
                          "PushSubscription web · leaflet"),
        ("Validation",    "react-hook-form + zod"),
    ]
    t = doc.add_table(rows=len(stack), cols=2)
    t.autofit = False
    for i, (k, v) in enumerate(stack):
        row = t.rows[i]
        row.cells[0].width = Cm(4.5)
        row.cells[1].width = Cm(20)
        row.cells[0].text = ""
        p1 = row.cells[0].paragraphs[0]
        r1 = p1.add_run(k)
        _force_run(r1, size=11, bold=True)
        row.cells[1].text = ""
        p2 = row.cells[1].paragraphs[0]
        r2 = p2.add_run(v)
        _force_run(r2, size=11)
    _apply_table_grid(t)
    doc.add_paragraph()

    # ── Workflows
    _add_heading(doc, "Parcours & use-cases principaux", level=2)
    _bullet(doc, "Gestion d'évènement — création meeting/formation/séminaire, "
                 "affectation salle + organisateur, cycle de statut "
                 "PLANNED → IN_PROGRESS → COMPLETED, participants multi-entités.")
    _bullet(doc, "Émargement QR — scan du QR de la salle → saisie identité + "
                 "fonction → signature manuscrite (dataURL en base) → calcul "
                 "auto du retard (ON_TIME / SLIGHT_DELAY / IMPORTANT_DELAY / VERY_LATE).")
    _bullet(doc, "Enregistrement audio + CR IA — capture in-browser → upload → "
                 "transcription Whisper → génération Markdown structuré par Llama "
                 "→ export Word → envoi email aux participants.")
    _bullet(doc, "Formulaires feedback — 8 types de questions, logique "
                 "conditionnelle, analyse IA des réponses libres.")
    _bullet(doc, "Templating docx dynamique — upload de modèles Word avec "
                 "placeholders `{{key}}`, auto-détection des champs, génération "
                 "de comptes-rendus et documents finalisés.")

    _add_page_break(doc)

    # ── Sécurité
    _add_heading(doc, "Sécurité & auth", level=2)
    _bullet(doc, "NextAuth v5 stratégie JWT (24h), provider Credentials, "
                 "mots de passe bcrypt.")
    _bullet(doc, "Middleware Edge (src/middleware.ts) : protège `/dashboard/*` "
                 "et `/api/*` avec allowlist des routes publiques.")
    _bullet(doc, "RBAC double couche : enum statique `Role` (SUPER_ADMIN / "
                 "ADMIN_ENTERPRISE / ORGANISATEUR) + système dynamique "
                 "`Module × Permission × DynamicRole × UserRole` (permissions "
                 "READ / CREATE / UPDATE / DELETE / EXPORT / MANAGE).")
    _bullet(doc, "Accès public via tokens opaques éphémères (creatorToken, "
                 "feedback token, event slug) — pas de compte requis pour "
                 "émarger ou répondre à un formulaire.")

    # ── Points remarquables
    _add_heading(doc, "Points techniques remarquables", level=2)
    _bullet(doc, "PWA avec émargement offline — l'utilisateur peut émarger "
                 "sans réseau ; sync automatique au retour de connexion "
                 "(identifiant `offlineId` unique + flag `isOfflineSync`).")
    _bullet(doc, "Signature manuscrite capturée en canvas, stockée en base "
                 "(`@db.Text` dataURL) — signature légalement opposable.")
    _bullet(doc, "Pipeline IA complet : audio browser → transcription Whisper "
                 "large-v3-turbo → CR structuré Llama 3.3 70B → export DOCX + "
                 "envoi mail — automatisation totale du secrétariat de réunion.")
    _bullet(doc, "Templating docx dynamique : upload d'un modèle Word avec "
                 "placeholders `{{name}}`, `{{date}}`… → détection automatique "
                 "→ génération des documents finalisés (PDF/DOCX).")
    _bullet(doc, "Créateurs anonymes d'évènements via `creatorToken` — un "
                 "organisateur externe peut créer sans compte.")
    _bullet(doc, "Push notifications web natives (PushSubscription p256dh/auth).")

    # ── Livrables
    _add_heading(doc, "Livrables & métriques", level=2)
    _bullet(doc, "≈ 32 600 lignes TypeScript / TSX (hors Prisma généré) — "
                 "l'un des projets les plus volumineux du portefeuille.")
    _bullet(doc, "Endpoints REST (`route.ts`) + pages Next.js unifiés dans "
                 "la même codebase full-stack.")
    _bullet(doc, "Périmètre : gestion d'évènements + présences signées + "
                 "comptes-rendus IA + feedback structuré.")
    _bullet(doc, "PWA installable · notifications push · mode offline avec sync.")

    _add_page_break(doc)


def project_4_escrc(doc):
    """Pages 12-14 : Projet 4 — ES-CRC SODECI (vue Ingénieur Backend)."""
    # ── En-tête
    _add_par(doc, "4", size=72, bold=True,
             align=WD_ALIGN_PARAGRAPH.LEFT, space_after=0)
    _add_par(doc, "ES-CRC SODECI — Plateforme d'Enquête de Satisfaction Client",
             size=22, bold=True, space_after=4)
    _add_par(doc, "SODECI (groupe Eranove) · rôle : ingénieur logiciel backend · "
             "NestJS 11 · Prisma 7 · PostgreSQL · Microsoft Entra ID",
             size=11, italic=True, space_after=14)

    # ── Contexte
    _add_heading(doc, "Contexte métier", level=2)
    _add_par(doc,
             "Plateforme centralisée d'Enquête de Satisfaction Client (« ES-CRC ») "
             "pour la SODECI : conception de questionnaires (à chaud / à froid / QR), "
             "distribution par liens courts, QR codes et SMS, collecte publique "
             "conforme RGPD & loi ivoirienne 2013-450, calcul de KPI (NPS, CSAT, "
             "taux de réponse, délais) par agence, alertes seuils et rapports "
             "hebdo/mensuel pour les DR, DMRC et DPO.",
             size=11)

    # ── Architecture
    _add_heading(doc, "Architecture logicielle (focus backend)", level=2)
    archi = doc.add_table(rows=1, cols=3)
    archi.autofit = False
    archi.alignment = WD_TABLE_ALIGNMENT.CENTER
    labels = [
        ("Backend", "NestJS 11 sur Fastify\nTypeScript · Node 20 · pnpm\n"
         "20 modules métier\n29 controllers · 120 routes"),
        ("Auth & sécu", "JWT httpOnly + SameSite=Strict\nRotation refresh single-use\n"
         "Microsoft Entra ID (OIDC/MSAL)\nRBAC + audit tamper-proof"),
        ("Data & jobs", "Prisma 7 + PostgreSQL 16\n33 tables · 12 migrations\n"
         "Redis + BullMQ + Cron\nSMTP · pdfkit · exceljs"),
    ]
    for i, (title, body) in enumerate(labels):
        cell = archi.rows[0].cells[i]
        cell.width = Cm(8)
        cell.text = ""
        pt = cell.paragraphs[0]
        pt.alignment = WD_ALIGN_PARAGRAPH.CENTER
        rt = pt.add_run(title)
        _force_run(rt, size=13, bold=True)
        pb = cell.add_paragraph()
        pb.alignment = WD_ALIGN_PARAGRAPH.CENTER
        rb = pb.add_run(body)
        _force_run(rb, size=10)
    _apply_table_grid(archi)
    doc.add_paragraph()

    _add_par(doc,
             "Monolithe modulaire NestJS style feature-first, couches "
             "infrastructure isolées. Chaque module suit "
             "`Controller → Service → PrismaService` (pas de repository "
             "pattern — Prisma sert de couche data). Guards globaux "
             "`JwtAuthGuard` + `ThrottlerGuard` ; décorateurs custom "
             "`@Public()`, `@Permissions()`, `@Roles()`, `@CurrentUser()`. "
             "Frontend Next.js 16 séparé (~20 pages, non détaillé ici).",
             size=11)

    _add_page_break(doc)

    # ── Stack
    _add_heading(doc, "Stack technique backend", level=2)
    stack = [
        ("Runtime",       "Node.js ≥ 20 · TypeScript 5 · pnpm 10"),
        ("Framework",     "NestJS 11 sur adaptateur Fastify (pas Express)"),
        ("Persistance",   "Prisma 7 + @prisma/adapter-pg · PostgreSQL · "
                          "12 migrations SQL versionnées"),
        ("Cache / queue", "Redis (ioredis) · cache-manager-ioredis-yet · "
                          "BullMQ (@nestjs/bullmq)"),
        ("Auth",          "@nestjs/jwt + passport-jwt · passport-ldapauth · "
                          "@azure/msal-node (Entra ID OIDC)"),
        ("Scheduling",    "@nestjs/schedule (cron) + BullMQ processors · "
                          "6 tâches actives"),
        ("Observabilité", "nestjs-pino (redact champs sensibles) · "
                          "@nestjs/terminus (health) · @nestjs/throttler (rate-limit)"),
        ("Docs API",      "Swagger @nestjs/swagger — auto-généré, exposé hors prod"),
        ("Génération",    "exceljs · fast-csv · pdfkit · qrcode · sharp · "
                          "handlebars (mails)"),
        ("Notifs",        "@nestjs-modules/mailer + nodemailer · socket.io (temps réel)"),
    ]
    t = doc.add_table(rows=len(stack), cols=2)
    t.autofit = False
    for i, (k, v) in enumerate(stack):
        row = t.rows[i]
        row.cells[0].width = Cm(4.5)
        row.cells[1].width = Cm(20)
        row.cells[0].text = ""
        p1 = row.cells[0].paragraphs[0]
        r1 = p1.add_run(k)
        _force_run(r1, size=11, bold=True)
        row.cells[1].text = ""
        p2 = row.cells[1].paragraphs[0]
        r2 = p2.add_run(v)
        _force_run(r2, size=11)
    _apply_table_grid(t)
    doc.add_paragraph()

    # ── Endpoints & modèle
    _add_heading(doc, "Endpoints & modèle de données", level=2)
    _bullet(doc, "`/auth` — login local (bcrypt cost 12) + OIDC Microsoft Entra ID "
                 "via MSAL Node, cookies httpOnly, rotation refresh single-use.")
    _bullet(doc, "`/questionnaires` — CRUD versionné (BROUILLON / ACTIF / ARCHIVE) "
                 "+ catalogue dynamique des types de réponse, affectations KPI.")
    _bullet(doc, "`/questionnaires/:id/links` — génération de liens courts stables "
                 "(`enq-001`) et QR codes PNG/PDF personnalisables.")
    _bullet(doc, "`/public/surveys/:code` — endpoint public répondant, throttled "
                 "30 req/min/IP, RGPD-compliant.")
    _bullet(doc, "`/dashboard`, `/kpis`, `/alerts`, `/reports` — KPI temps réel, "
                 "catalogue KPI, alertes seuils par agence, rapports PDF hebdo/mensuel.")
    _bullet(doc, "Administration : `/agences`, `/directions-regionales`, `/sites`, "
                 "`/users`, `/roles`, `/permissions`, `/audit-logs`, `/policy-versions`, "
                 "`/erasure-requests`, `/sms-templates`.")

    _add_page_break(doc)

    # ── Sécurité
    _add_heading(doc, "Sécurité backend", level=2)
    _bullet(doc, "Double auth : local (bcrypt cost 12, verrouillage 30 min après "
                 "5 échecs) + Microsoft Entra ID via OIDC (MSAL Node avec state "
                 "Redis TTL 5 min, mode mock en dev).")
    _bullet(doc, "JWT en cookies httpOnly + `SameSite=Strict` + `Secure` : "
                 "`escrc_at` (8 h) et `escrc_rt` (7 j, path `/api/auth`).")
    _bullet(doc, "Rotation refresh single-use — table `refresh_tokens` avec "
                 "`revokedAt` pour révoquer immédiatement une session.")
    _bullet(doc, "RBAC granulaire `module.action` (User × Role × Permission), "
                 "`sessionInvalidatedAt` invalide immédiatement les JWT émis "
                 "avant tout changement de rôle.")
    _bullet(doc, "Migration `audit_tamper_proof` — triggers PostgreSQL "
                 "empêchant UPDATE/DELETE sur `audit_logs` = piste d'audit "
                 "légale, opposable.")
    _bullet(doc, "Rate-limit @nestjs/throttler : 100 req/min global, 5 req/min "
                 "sur `/auth/login`, 30 req/min/IP sur endpoints publics.")
    _bullet(doc, "Pino redact sur champs sensibles ; validation FR "
                 "(class-validator traduit).")

    # ── Points remarquables
    _add_heading(doc, "Points techniques remarquables (backend)", level=2)
    _bullet(doc, "Questionnaires versionnés avec `publicSerial` auto-incrémenté — "
                 "les URLs courtes (`enq-001`) restent stables même après une "
                 "nouvelle version publiée.")
    _bullet(doc, "Snapshot JSON de la question dans `ResponseItem.questionSnapshot` — "
                 "les réponses restent lisibles même si la question est modifiée "
                 "ou supprimée par la suite.")
    _bullet(doc, "Override de seuil KPI par agence (`KpiAlertThresholdOverride`) "
                 "au-dessus du seuil global, sans dupliquer la définition KPI.")
    _bullet(doc, "Catalogue dynamique des types de réponse en base (`response_types`) "
                 "exposé via `GET /questionnaires/meta/response-types` — zéro "
                 "hardcoding UI, invariant avec l'enum Prisma.")
    _bullet(doc, "Provider OIDC swappable mock/real — le dev tourne sans dépendre "
                 "de l'AD tenant, la prod bascule via `OIDC_MODE=real`.")
    _bullet(doc, "Rapports PDF stockés en `Bytes` PostgreSQL (V1, sans S3), "
                 "migration vers stockage objet préparée.")
    _bullet(doc, "Cron scheduling déclaratif : alertes horaires, purge 03 h, "
                 "rapports hebdo (lundi 08 h) et mensuels (1er du mois 08 h), "
                 "rétention 12/36 mois selon type de donnée.")

    # ── Livrables
    _add_heading(doc, "Livrables & métriques (backend)", level=2)
    _bullet(doc, "≈ 20 500 lignes TypeScript backend · 181 fichiers `.ts`.")
    _bullet(doc, "29 controllers · ~120 routes REST · Swagger auto-généré.")
    _bullet(doc, "33 tables PostgreSQL · 12 migrations Prisma versionnées.")
    _bullet(doc, "20 modules métier + 10 modules infrastructure/config.")
    _bullet(doc, "6 tâches Cron actives · BullMQ processors (rétention, purge).")

    _add_page_break(doc)


def project_placeholder(doc, num: str, title: str):
    """Pages « À compléter » pour projets 2, 3, 4."""
    _add_par(doc, num, size=72, bold=True, space_after=0)
    _add_par(doc, title, size=22, bold=True, space_after=20)
    for _ in range(4):
        doc.add_paragraph()
    _add_par(doc, "— Contenu à compléter —", size=14, italic=True,
             align=WD_ALIGN_PARAGRAPH.CENTER)
    _add_par(doc,
             "Structure suggérée (identique au projet 1) : contexte métier, "
             "architecture logicielle, stack technique, workflows / logique "
             "principale, sécurité, défis résolus, livrables.",
             size=11, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    _add_page_break(doc)


def _apply_table_grid(table):
    """Bordures noires simples sur toutes les cellules (Table Grid)."""
    tbl = table._tbl
    tblPr = tbl.find(qn("w:tblPr")) or OxmlElement("w:tblPr")
    if tbl.find(qn("w:tblPr")) is None:
        tbl.insert(0, tblPr)
    tblBorders = OxmlElement("w:tblBorders")
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        b = OxmlElement(f"w:{side}")
        b.set(qn("w:val"), "single")
        b.set(qn("w:sz"), "4")
        b.set(qn("w:color"), "000000")
        tblBorders.append(b)
    old = tblPr.find(qn("w:tblBorders"))
    if old is not None:
        tblPr.remove(old)
    tblPr.append(tblBorders)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def build():
    doc = Document()
    _set_doc_defaults(doc)
    _set_landscape(doc.sections[0])

    cover_page(doc)
    toc_page(doc)
    project_1_ma2e(doc)
    project_2_snvc(doc)
    project_3_emargeo(doc)
    project_4_escrc(doc)

    out = Path(__file__).parent.parent / "PROJETS_FLO.docx"
    doc.save(out)
    print(f"[ok] {out}")


if __name__ == "__main__":
    build()
