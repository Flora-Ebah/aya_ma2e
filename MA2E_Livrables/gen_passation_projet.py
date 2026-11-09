"""Document de passation projet — MA2E Plateforme Digitale d'Identification.

Style : sobre, noir et blanc, aucune couleur d'accent, mise en forme
Word classique (Times New Roman / Calibri, titres gras, tableaux
bordures fines). Objectif : passer le projet à un collaborateur avant
un congé, sans ambiguïté.
"""
from __future__ import annotations
from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor


BLACK = RGBColor(0x00, 0x00, 0x00)
DARK = RGBColor(0x1A, 0x1A, 0x1A)
GRAY = RGBColor(0x55, 0x55, 0x55)
LIGHT_GRAY_HEX = "F2F2F2"
BORDER_HEX = "999999"
FONT = "Calibri"


# ─── Helpers OOXML ─────────────────────────────────────────────────────
def shade(cell, hex_color: str):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def cell_borders(cell, sz=6, color=BORDER_HEX):
    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = OxmlElement("w:tcBorders")
    for edge in ("top", "left", "bottom", "right"):
        b = OxmlElement(f"w:{edge}")
        b.set(qn("w:val"), "single")
        b.set(qn("w:sz"), str(sz))
        b.set(qn("w:color"), color)
        tcBorders.append(b)
    tcPr.append(tcBorders)


def set_run(run, *, size=11, bold=False, italic=False, color=DARK):
    run.font.name = FONT
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    if color is not None:
        run.font.color.rgb = color


def configure_styles(doc):
    h1 = doc.styles["Heading 1"]
    h1.font.name = FONT
    h1.font.size = Pt(18)
    h1.font.bold = True
    h1.font.color.rgb = BLACK
    h1.paragraph_format.space_before = Pt(24)
    h1.paragraph_format.space_after = Pt(10)

    h2 = doc.styles["Heading 2"]
    h2.font.name = FONT
    h2.font.size = Pt(13)
    h2.font.bold = True
    h2.font.color.rgb = BLACK
    h2.paragraph_format.space_before = Pt(14)
    h2.paragraph_format.space_after = Pt(6)

    h3 = doc.styles["Heading 3"]
    h3.font.name = FONT
    h3.font.size = Pt(11)
    h3.font.bold = True
    h3.font.color.rgb = DARK
    h3.paragraph_format.space_before = Pt(10)
    h3.paragraph_format.space_after = Pt(4)

    normal = doc.styles["Normal"]
    normal.font.name = FONT
    normal.font.size = Pt(11)
    normal.font.color.rgb = DARK
    normal.paragraph_format.space_after = Pt(6)


def H1(doc, text):
    doc.add_heading(text, level=1)


def H2(doc, text):
    doc.add_heading(text, level=2)


def H3(doc, text):
    doc.add_heading(text, level=3)


def P(doc, text, *, italic=False):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_after = Pt(6)
    r = p.add_run(text)
    set_run(r, size=11, italic=italic, color=DARK)


def BUL(doc, text):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(3)
    r = p.add_run(text)
    set_run(r, size=11, color=DARK)


def NUM(doc, text):
    p = doc.add_paragraph(style="List Number")
    p.paragraph_format.space_after = Pt(3)
    r = p.add_run(text)
    set_run(r, size=11, color=DARK)


def CODE(doc, text):
    """Bloc de code / commande — police monospace, léger fond gris."""
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.LEFT
    tbl.autofit = False
    cell = tbl.rows[0].cells[0]
    cell.width = Cm(16)
    shade(cell, LIGHT_GRAY_HEX)
    cell_borders(cell, sz=4, color=BORDER_HEX)
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run(text)
    r.font.name = "Consolas"
    r.font.size = Pt(9.5)
    r.font.color.rgb = DARK
    doc.add_paragraph()


def TABLE(doc, headers, rows, col_widths=None):
    n = len(headers)
    total = len(rows) + 1
    t = doc.add_table(rows=total, cols=n)
    t.alignment = WD_TABLE_ALIGNMENT.LEFT
    for i, h in enumerate(headers):
        cell = t.rows[0].cells[i]
        if col_widths and i < len(col_widths):
            cell.width = col_widths[i]
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        cell.paragraphs[0].text = ""
        r = cell.paragraphs[0].add_run(h)
        set_run(r, size=10, bold=True, color=BLACK)
        shade(cell, LIGHT_GRAY_HEX)
        cell_borders(cell, sz=6, color=BORDER_HEX)
    for ri, row in enumerate(rows, start=1):
        for ci, val in enumerate(row):
            cell = t.rows[ri].cells[ci]
            if col_widths and ci < len(col_widths):
                cell.width = col_widths[ci]
            cell.vertical_alignment = WD_ALIGN_VERTICAL.TOP
            cell.paragraphs[0].text = ""
            r = cell.paragraphs[0].add_run(str(val))
            set_run(r, size=10, color=DARK)
            cell_borders(cell, sz=4, color=BORDER_HEX)
    doc.add_paragraph()


def add_toc(doc):
    para = doc.add_paragraph()
    run = para.add_run()
    fldChar1 = OxmlElement("w:fldChar")
    fldChar1.set(qn("w:fldCharType"), "begin")
    instrText = OxmlElement("w:instrText")
    instrText.set(qn("xml:space"), "preserve")
    instrText.text = 'TOC \\o "1-3" \\h \\z \\u'
    fldChar2 = OxmlElement("w:fldChar")
    fldChar2.set(qn("w:fldCharType"), "separate")
    fldChar3 = OxmlElement("w:t")
    fldChar3.text = ("Faites clic droit sur cette ligne dans Word puis « Mettre "
                     "à jour les champs » pour générer la table des matières.")
    fldChar4 = OxmlElement("w:fldChar")
    fldChar4.set(qn("w:fldCharType"), "end")
    run._r.append(fldChar1)
    run._r.append(instrText)
    run._r.append(fldChar2)
    run._r.append(fldChar3)
    run._r.append(fldChar4)


# ─── Construction du document ──────────────────────────────────────────
def build_passation(output_path: Path) -> Path:
    doc = Document()

    section = doc.sections[0]
    section.left_margin = Cm(2.2)
    section.right_margin = Cm(2.2)
    section.top_margin = Cm(2.2)
    section.bottom_margin = Cm(2.2)

    configure_styles(doc)

    # ── Page de garde ──────────────────────────────────────────────────
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r = p.add_run("DOCUMENT DE PASSATION DE PROJET")
    set_run(r, size=10, bold=True, color=GRAY)
    p.paragraph_format.space_after = Pt(4)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r = p.add_run("MA2E — Plateforme Digitale d'Identification")
    set_run(r, size=24, bold=True, color=BLACK)
    p.paragraph_format.space_after = Pt(4)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r = p.add_run("Mutuelle des Agents de l'Eau et de l'Électricité — Groupe GS2E")
    set_run(r, size=12, color=GRAY)
    p.paragraph_format.space_after = Pt(40)

    # Métadonnées
    TABLE(doc,
          ["Champ", "Valeur"],
          [
              ["Référence document", "MA2E_Passation_Projets_Conges.docx"],
              ["Version", "1.0"],
              ["Date", date.today().strftime("%d/%m/%Y")],
              ["Objet", "Passation du projet pendant congés"],
              ["Destinataires", "Collaborateurs en charge de la continuité du projet"],
              ["Statut projet", "En production sur environnement pilote Azure"],
          ],
          col_widths=[Cm(5), Cm(11)])

    doc.add_page_break()

    # ── Sommaire — grandes lignes ──────────────────────────────────────
    H1(doc, "Sommaire")
    P(doc,
      "Ce document présente l'ensemble des informations nécessaires à la "
      "reprise et à la continuité du projet MA2E Plateforme Digitale "
      "d'Identification. Il est organisé selon les onze grandes lignes "
      "suivantes.")

    for i, title in enumerate([
        "Vue d'ensemble du projet",
        "Architecture technique et stack",
        "Environnements et URL d'accès",
        "Comptes et accès",
        "Fonctionnalités livrées",
        "Sécurité — état actuel et prochaines étapes",
        "Procédures opérationnelles",
        "Incidents résolus et points de vigilance",
        "Livrables documentaires",
        "Contacts clés",
        "Roadmap Phase 2 et reste à faire",
    ], start=1):
        NUM(doc, title)

    doc.add_paragraph()
    P(doc,
      "Une table des matières automatique est disponible ci-dessous. "
      "Faites clic droit sur la ligne et sélectionnez « Mettre à jour les "
      "champs » dans Word pour la générer.")
    add_toc(doc)
    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════
    # 1. VUE D'ENSEMBLE
    # ═══════════════════════════════════════════════════════════════════
    H1(doc, "1. Vue d'ensemble du projet")

    H2(doc, "Contexte")
    P(doc,
      "La MA2E (Mutuelle des Agents de l'Eau et de l'Électricité) est la "
      "mutuelle sociale des collaborateurs des sociétés du groupe GS2E "
      "(CIE, SODECI, SMB, AD ERANOVE). Elle traite historiquement les "
      "inscriptions de nouveaux sociétaires via un formulaire papier de "
      "23 champs, avec un délai moyen de deux semaines par dossier.")

    H2(doc, "Objectif")
    P(doc,
      "Digitaliser le parcours d'identification et d'inscription des "
      "sociétaires MA2E via deux canaux complémentaires (WhatsApp et Web "
      "Chat), en respectant intégralement la loi ivoirienne 2013-450 "
      "relative à la protection des données à caractère personnel "
      "(autorité de contrôle : ARTCI).")

    H2(doc, "Cibles de gain")
    BUL(doc, "Durée du parcours sociétaire : moins de 10 minutes.")
    BUL(doc, "Délai de décision agent : moins de 24 heures ouvrées.")
    BUL(doc, "Taux d'automatisation du parcours : supérieur à 70 %.")
    BUL(doc, "Volumétrie cible sur trois ans : 50 000 sociétaires identifiés.")

    H2(doc, "Périmètre POC actuel")
    P(doc,
      "Le projet est actuellement en phase de pilote (POC) déployé sur "
      "une machine virtuelle Azure. La démonstration initiale a été "
      "présentée le 15 mai 2026. Les développements post-démo ont porté "
      "sur la conformité ARTCI, la sécurité, les workflows dynamiques et "
      "les intégrations Azure (OpenAI, Vision, Blob).")

    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════
    # 2. ARCHITECTURE TECHNIQUE
    # ═══════════════════════════════════════════════════════════════════
    H1(doc, "2. Architecture technique et stack")

    H2(doc, "Stack retenue")
    TABLE(doc,
          ["Couche", "Technologie", "Justification"],
          [
              ["Frontend", "Next.js 14 + TypeScript + Tailwind CSS 3",
               "Rendu serveur rapide, écosystème React, DX moderne"],
              ["Backend", "Python 3.13 + FastAPI + SQLAlchemy 2",
               "Async natif, écosystème IA et OCR le plus mature"],
              ["Base de données", "PostgreSQL 16 + extension pgvector",
               "Relationnel ACID + recherche sémantique sur conversations"],
              ["Cache et sessions", "Redis 7",
               "Sessions WhatsApp et cache de configuration en mémoire"],
              ["Stockage fichiers", "MinIO (dev) — Azure Blob Storage (prod cible)",
               "Chiffrement au repos, conformité ARTCI"],
              ["Intelligence artificielle", "Azure OpenAI (chat) + Azure AI Vision (OCR)",
               "Services managés, SLA, région conforme"],
              ["Canal utilisateur", "WhatsApp Cloud API (Meta)",
               "97 % des Ivoiriens utilisent déjà WhatsApp"],
              ["Reverse proxy", "Nginx + Let's Encrypt SSL",
               "HTTPS obligatoire pour webhooks Meta"],
              ["Orchestration", "Docker + Docker Compose (VM unique)",
               "Simplicité d'exploitation, portabilité"],
          ],
          col_widths=[Cm(3.5), Cm(6), Cm(6.5)])

    H2(doc, "Architecture fonctionnelle")
    P(doc,
      "Le sociétaire entre par WhatsApp ou par le portail Web Chat. "
      "L'agent MA2E accède au back-office Next.js. Les deux flux "
      "convergent vers une API FastAPI unique qui expose les endpoints "
      "métier. Sept modules internes assurent l'authentification, "
      "l'onboarding, l'extraction OCR de la pièce d'identité, "
      "l'assistant IA, les notifications, la validation des dossiers et "
      "le module audit conformité ARTCI. Quatre services externes sont "
      "consommés : Active Directory ERANOVE (préparé), WhatsApp Cloud "
      "API, Azure AI (OCR et LLM) et SMTP.")

    H2(doc, "Découpage des composants")
    P(doc,
      "Trois repositories Git distincts hébergés sur Azure DevOps :")
    BUL(doc, "Repository backend : API FastAPI, workflows, migrations, seeds.")
    BUL(doc, "Repository frontend : back-office Next.js et portail Web Chat.")
    BUL(doc, "Repository racine (virtual-ai) : livrables documentaires et diagrammes.")

    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════
    # 3. ENVIRONNEMENTS ET URL
    # ═══════════════════════════════════════════════════════════════════
    H1(doc, "3. Environnements et URL d'accès")

    H2(doc, "Environnement de production pilote (Azure)")
    TABLE(doc,
          ["Ressource", "URL / valeur", "Commentaire"],
          [
              ["Portail sociétaire", "https://ma2e.swedencentral.cloudapp.azure.com",
               "Point d'entrée public unique, HTTPS obligatoire"],
              ["Back-office agents", "https://ma2e.swedencentral.cloudapp.azure.com",
               "Même URL, filtrage à la connexion selon rôle"],
              ["Webhook WhatsApp Meta", "https://ma2e.swedencentral.cloudapp.azure.com/webhooks/whatsapp",
               "Configuré dans Meta for Developers"],
              ["IP publique VM", "20.240.187.5",
               "IP de la VM Azure (uniquement pour debug interne)"],
              ["Port backend interne", "8000",
               "FastAPI, routé par nginx via /api/* et /webhooks/*"],
              ["Port frontend interne", "3001",
               "Next.js, routé par nginx sur toutes les autres routes"],
              ["Port console MinIO", "9001",
               "Interface admin MinIO (accès humain)"],
              ["Port API S3 MinIO", "9000",
               "Endpoint programmatique pour uploads (critique)"],
          ],
          col_widths=[Cm(3.5), Cm(7), Cm(5.5)])

    H2(doc, "Configuration nginx")
    P(doc,
      "Le reverse proxy nginx sur la VM Azure route les requêtes selon "
      "leur chemin. Toute modification doit être validée par la commande "
      "nginx -t avant rechargement.")
    CODE(doc,
         "location /api/       -> proxy vers localhost:8000  (backend)\n"
         "location /webhooks/  -> proxy vers localhost:8000  (backend)\n"
         "location /           -> proxy vers localhost:3001  (frontend)")

    H2(doc, "Environnement de développement local")
    P(doc,
      "Chaque développeur utilise ses conteneurs Docker locaux (préfixe "
      "vai_) pour PostgreSQL, Redis et MinIO. Le backend tourne en mode "
      "uvicorn avec rechargement automatique sur le port 8088. Le "
      "frontend tourne en mode Next.js dev sur le port 3000.")

    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════
    # 4. COMPTES ET ACCÈS
    # ═══════════════════════════════════════════════════════════════════
    H1(doc, "4. Comptes et accès")

    H2(doc, "Comptes de démonstration back-office")
    TABLE(doc,
          ["Rôle", "Adresse e-mail", "Mot de passe", "Périmètre"],
          [
              ["Super Admin GS2E", "admin@gs2e.ci", "admin123",
               "Compte break-glass, accès total"],
              ["Admin MA2E", "admin@ma2e.ci", "ma2e123",
               "Administration complète de l'instance"],
              ["Agent MA2E", "agent@ma2e.ci", "agent123",
               "Validation des dossiers uniquement"],
              ["Viewer MA2E", "viewer@ma2e.ci", "viewer123",
               "Consultation en lecture seule tous modules"],
          ],
          col_widths=[Cm(3.5), Cm(4), Cm(2.5), Cm(6)])

    P(doc,
      "Ces mots de passe sont provisoires et doivent être renouvelés "
      "avant tout passage en production réelle.",
      italic=True)

    H2(doc, "Comptes techniques et secrets")
    TABLE(doc,
          ["Service", "Localisation du secret", "Statut"],
          [
              ["Azure OpenAI (chat)", "Fichier .env de la VM, variable AZURE_OPENAI_API_KEY",
               "À faire tourner (a été partagé en clair)"],
              ["Azure AI Vision (OCR)", "Fichier .env, variable AZURE_AI_VISION_KEY",
               "À faire tourner"],
              ["WhatsApp Cloud API", "Fichier .env, variables WHATSAPP_ACCESS_TOKEN_MA2E et WHATSAPP_PHONE_ID_MA2E",
               "En place, valable jusqu'à expiration Meta"],
              ["JWT signing key", "Fichier .env, variable JWT_SECRET_KEY",
               "À faire tourner"],
              ["OCR.space (fallback)", "Fichier .env, variable OCR_SPACE_API_KEY",
               "Clé de secours en cas d'indisponibilité Azure Vision"],
              ["Verify token webhook", ".env variable WHATSAPP_VERIFY_TOKEN",
               "Doit correspondre exactement à la valeur Meta"],
          ],
          col_widths=[Cm(4), Cm(7.5), Cm(4.5)])

    H2(doc, "MFA")
    P(doc,
      "L'authentification à deux facteurs est disponible et activable par "
      "chaque utilisateur depuis son profil. Elle est fortement "
      "recommandée pour tous les rôles Admin et DPO. Après cinq "
      "tentatives infructueuses, un compte est bloqué automatiquement "
      "pendant quinze minutes.")

    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════
    # 5. FONCTIONNALITÉS LIVRÉES
    # ═══════════════════════════════════════════════════════════════════
    H1(doc, "5. Fonctionnalités livrées")

    H2(doc, "Sprint 1 (15 juin — 26 juin 2026) — Socle plateforme")
    P(doc, "Dix-sept User Stories planifiées, seize livrées.")

    TABLE(doc,
          ["Module", "Fonctionnalités livrées"],
          [
              ["Authentification", "Connexion administrateur (JWT, bcrypt), écran login épuré, MFA optionnel"],
              ["Administration", "Gestion rôles et permissions, utilisateurs internes, sociétés affiliées (CIE, SODECI, SMB, AD ERANOVE), templates de messages"],
              ["Onboarding sociétaire", "Démarrage via WhatsApp et Web Chat, recueil consentement ARTCI, saisie informations professionnelles (23 champs), reprise session interrompue"],
              ["Extraction pièces", "Téléversement CNI recto/verso, extraction OCR (Azure Vision + fallback OCR.space), détection des pièces illisibles"],
              ["Assistant IA", "Réponses aux questions sociétaires (RAG pgvector), détection doublons"],
              ["Audit ARTCI", "Journalisation actions sensibles, traçabilité IP, page ARTCI publique permanente"],
          ],
          col_widths=[Cm(4), Cm(12)])

    H2(doc, "Sprint 2 (29 juin — 10 juillet 2026) — Validation et reporting")
    P(doc, "Fonctionnalités cœur métier toutes livrées avant les congés.")

    TABLE(doc,
          ["US", "Fonctionnalité", "Statut"],
          [
              ["US-19", "Validation d'un dossier (endpoint validate + audit + notification)", "Livré"],
              ["US-20", "Refus d'un dossier avec motif obligatoire", "Livré"],
              ["US-21", "Demande de complément (workflow retour vers sociétaire)", "Livré"],
              ["US-23", "Notification sociétaire après décision agent (WhatsApp + email)", "Livré"],
              ["US-24", "Suivi temps réel de l'activité (overview, timeline, funnel)", "Livré"],
              ["US-25", "Export sociétaires validés au format Excel stylé", "Livré"],
              ["US-26", "Indicateurs opérationnels (KPI) + alertes seuil + export PDF", "Livré"],
              ["US-38", "Filtres avancés tableau de bord (statut, agent, période, OCR, priorité)", "Livré"],
          ],
          col_widths=[Cm(2), Cm(11), Cm(3)])

    P(doc, "Fonctionnalités reportées explicitement en Phase 2 :", italic=True)
    BUL(doc, "US-28 Droit à l'oubli et anonymisation (module DPO).")
    BUL(doc, "US-30 à US-35 Connecteurs Perfect-Vision (conditionné à la convention CAGECFI).")
    BUL(doc, "US-33 Synchronisation matricules temps réel depuis le SI RH groupe.")

    H2(doc, "Fonctionnalités transverses livrées")
    BUL(doc, "Rôle Viewer lecture seule sur tous modules avec filtrage sidebar dynamique.")
    BUL(doc, "Endpoint /api/me qui renvoie profil et permissions agrégées.")
    BUL(doc, "Refonte PDF reporting et export Excel dossiers stylés.")
    BUL(doc, "Token JWT accepté en query string pour les téléchargements de fichiers.")
    BUL(doc, "Redirection automatique vers /login sur session expirée.")
    BUL(doc, "Bibliothèque de composants UI réutilisables dans components/ui/ (Button, Card, PageHeader, Toolbar, SearchInput, StatusPill, EmptyState, Spinner) et hooks partagés dans lib/hooks/ (useApi, useDebounce), avec documentation README.md et exemple de refactor sur /parametres/mfa. Objectif : chaque page < 250 lignes.")
    BUL(doc, "Détection auto du type de fichier à l'import (CSV, XLSX, PDF).")

    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════
    # 6. SÉCURITÉ
    # ═══════════════════════════════════════════════════════════════════
    H1(doc, "6. Sécurité — état actuel et prochaines étapes")

    H2(doc, "Mesures actives en production")
    BUL(doc, "Authentification JWT et MFA optionnel par utilisateur.")
    BUL(doc, "RBAC côté backend (super_admin, tenant_admin, agent, viewer).")
    BUL(doc, "Verrouillage automatique après cinq tentatives infructueuses (15 minutes).")
    BUL(doc, "Session applicative expirant après vingt minutes d'inactivité (IdleGuard).")
    BUL(doc, "AuthGuard qui bloque le rendu de toute page protégée sans token valide.")
    BUL(doc, "Nettoyage complet du localStorage à la déconnexion.")
    BUL(doc, "Redirection immédiate sur 401 vers /login avec message de session expirée.")
    BUL(doc, "Chiffrement HTTPS obligatoire de bout en bout, HSTS actif un an.")
    BUL(doc, "Headers de sécurité complets : X-Frame-Options, X-Content-Type-Options, Content-Security-Policy, Referrer-Policy, Permissions-Policy, Cross-Origin-Opener-Policy.")
    BUL(doc, "Framework masqué (X-Powered-By retiré) et sourcemaps désactivés en production.")
    BUL(doc, "Journal d'audit ARTCI append-only, conservation dix ans.")
    BUL(doc, "Chiffrement au repos des pièces d'identité (MinIO en dev, Azure Blob AES-256 en cible).")
    BUL(doc, "Rate limit applicatif Redis sur les endpoints sensibles (validation, refus, complément, exports, login, MFA, OTP). Middleware transparent, fail-open si Redis KO.")
    BUL(doc, "Session par cookie httpOnly + jeton CSRF double-submit (Phase 2, migré fin juillet 2026). Le JWT n'est plus lisible par JavaScript et est immunisé contre les vols par XSS. Toute mutation exige un header X-CSRF-Token vérifié par middleware.")
    BUL(doc, "CORS restrictif : liste blanche d'origines (localhost:3000/3001 + domaine Azure pilote), plus d'allow_origins wildcard.")
    BUL(doc, "Endpoint POST /api/auth/logout qui purge les cookies httpOnly côté serveur.")
    BUL(doc, "Durée de vie du JWT d'accès réduite à 60 minutes par défaut (au lieu de 8 heures). Attention : le fichier .env de la VM prod contient encore JWT_EXPIRE_MINUTES=480 hérité de la Phase 1 — à retirer ou baisser à 60 pour bénéficier de la nouvelle valeur.")
    BUL(doc, "Refresh token httpOnly avec rotation à chaque usage (7 jours de durée par défaut, scope réduit au path /api/auth). Le jti est stocké en Redis (GETDEL atomique) pour détecter et bloquer toute réutilisation d'un ancien refresh (signal de vol). L'agent ne se reconnecte donc pas toutes les heures : le frontend refresh automatiquement en tâche de fond.")
    BUL(doc, "Verrou global côté frontend sur le refresh : N requêtes concurrentes en 401 déclenchent UN SEUL refresh, les autres attendent le résultat commun. Évite la consommation multiple du jti et un faux logout.")
    BUL(doc, "Masquage automatique des données personnelles (emails, CNI, numéros sociétaires, téléphones ivoiriens) dans tous les logs applicatifs backend, via un filtre logging + processor structlog. Aucun impact sur les IDs techniques (UUID, IP, timestamps).")

    H2(doc, "Points d'attention en cours")
    BUL(doc, "Rotation des clés Azure OpenAI, Azure AI Vision et JWT secret non encore effectuée (action manuelle DevOps requise avant tout accès externe non maîtrisé).")
    BUL(doc, "Aucun test automatisé de sécurité récurrent en CI.")
    BUL(doc, "Bouton Active Directory ERANOVE désactivé (bordure pointillée) — attente ouverture firewall DSI.")
    BUL(doc, "Ancien fallback token en query string (?token=...) conservé côté backend pour compatibilité mais plus utilisé côté frontend. À retirer une fois la migration cookies validée en prod.")
    BUL(doc, "Cookie SameSite : par défaut Lax (compatible dev cross-origin). Recommandé en prod : forcer AUTH_COOKIE_SAMESITE=strict dans le .env, puisque le back-office n'est jamais lié depuis l'extérieur (même origine via nginx).")

    H2(doc, "Roadmap sécurité pour la Phase 2")
    NUM(doc, "Rotation immédiate de toutes les clés d'API exposées.")
    NUM(doc, "Passage à SameSite=Strict et Secure=True (activés en prod, gardés Lax/off en dev HTTP).")
    NUM(doc, "Baisser encore la durée du JWT d'accès (actuellement 60 min, cible finale 15 min) — sans impact utilisateur grâce au refresh token en place.")
    NUM(doc, "Audit npm et pip trimestriel pour détecter les CVE dans les dépendances.")
    NUM(doc, "Mise en place d'une pipeline CI/CD avec tests de sécurité récurrents (bandit, safety, npm audit, OWASP ZAP baseline).")
    NUM(doc, "Nettoyage progressif des 20+ pages qui contiennent encore des `if (!getToken()) router.replace('/login')` — la fonction getToken() est désormais un shim obsolète (renvoie null). L'AuthGuard côté layout + l'intercepteur 401 dans lib/api.ts assurent déjà la protection. À supprimer au fil des refactors — cf. components/ui/README.md.")
    NUM(doc, "Migration progressive des pages vers la bibliothèque de composants UI (PageHeader, Button, Card, useApi…) pour passer sous les 250 lignes par fichier. Priorité aux gros fichiers (parcours/page.tsx 1644 lignes, dossiers/[id]/page.tsx 1297 lignes, administration/utilisateurs 832 lignes).")

    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════
    # 7. PROCÉDURES OPÉRATIONNELLES
    # ═══════════════════════════════════════════════════════════════════
    H1(doc, "7. Procédures opérationnelles")

    H2(doc, "Redéploiement du backend")
    P(doc, "Après un git push sur la branche main du repository backend :")
    CODE(doc,
         "cd ~/backend\n"
         "git pull\n"
         "docker stop ma2e_backend\n"
         "docker rm ma2e_backend\n"
         "docker build --no-cache -t ma2e-backend .\n"
         "docker run -d --name ma2e_backend --env-file .env \\\n"
         "  --network ma2e_net -p 8000:8000 \\\n"
         "  --restart unless-stopped ma2e-backend")

    H2(doc, "Redéploiement du frontend")
    P(doc,
      "L'option --build-arg est indispensable car NEXT_PUBLIC_API_URL "
      "est bakée dans le bundle JavaScript à la compilation.")
    CODE(doc,
         "cd ~/frontend\n"
         "git pull\n"
         "docker stop ma2e_frontend\n"
         "docker rm ma2e_frontend\n"
         "docker build --no-cache \\\n"
         "  --build-arg NEXT_PUBLIC_API_URL=https://ma2e.swedencentral.cloudapp.azure.com \\\n"
         "  -t ma2e-frontend .\n"
         "docker run -d --name ma2e_frontend --network ma2e_net \\\n"
         "  -p 3001:3000 --restart unless-stopped ma2e-frontend")

    H2(doc, "Exécution des migrations et seeds")
    P(doc,
      "Le script seed_all.py orchestre l'ensemble des migrations et "
      "seeds nécessaires. Il est idempotent et peut être relancé "
      "autant de fois que nécessaire.")
    CODE(doc,
         "docker exec -it ma2e_backend python -m scripts.seed_all")

    H2(doc, "Modification du fichier .env")
    P(doc,
      "Le fichier .env est injecté au démarrage du conteneur via l'option "
      "--env-file. Après modification, un simple docker restart ne "
      "recharge PAS les nouvelles valeurs : il faut absolument recréer "
      "le conteneur (docker stop + rm + run).")

    H2(doc, "Consultation des logs applicatifs")
    CODE(doc,
         "docker logs ma2e_backend --tail 200 -f\n"
         "docker logs ma2e_frontend --tail 200 -f")

    H2(doc, "Vérification du webhook WhatsApp")
    P(doc,
      "En cas de dysfonctionnement du parcours WhatsApp, tester la "
      "réponse du verify token de Meta :")
    CODE(doc,
         'curl "https://ma2e.swedencentral.cloudapp.azure.com/webhooks/whatsapp'
         '?hub.mode=subscribe&hub.verify_token=<VALEUR_ENV>&hub.challenge=test123"')
    P(doc, "La réponse attendue est exactement : test123")

    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════
    # 8. INCIDENTS RÉSOLUS ET POINTS DE VIGILANCE
    # ═══════════════════════════════════════════════════════════════════
    H1(doc, "8. Incidents résolus et points de vigilance")

    H2(doc, "Incidents résolus (historique récent)")
    TABLE(doc,
          ["Date", "Incident", "Résolution"],
          [
              ["19/06", "Webhook WhatsApp en 404 (nginx routait vers frontend)",
               "Ajout d'un bloc location /webhooks/ dans la config nginx"],
              ["19/06", "Alertes CRITIQUE fantômes en reporting sur base vide",
               "Skip silencieux des KPI de type ratio quand le dénominateur est 0"],
              ["22/06", "Token JWT expiré affichait erreur 401 au lieu de rediriger",
               "Interception globale des 401 dans lib/api.ts + AuthGuard"],
              ["23/06", "Upload CNI échouait avec « S3 API Requests must be made to API port »",
               "Correction MINIO_ENDPOINT en prod : port 9000 (API S3) au lieu de 9001 (console)"],
              ["23/06", "Sécurité frontend insuffisante pour pentest à venir",
               "Ajout headers HTTP stricts, AuthGuard, IdleGuard, purge complète localStorage"],
          ],
          col_widths=[Cm(2), Cm(8), Cm(6)])

    H2(doc, "Points de vigilance ouverts")
    BUL(doc, "Volume Docker sur la base PostgreSQL : sans volume monté, la base est perdue au restart du conteneur. À valider avec la DevOps avant tout arrêt planifié.")
    BUL(doc, "Backup base PostgreSQL : aucune procédure automatisée actuellement. Prévoir un dump journalier vers Azure Blob avant utilisation réelle.")
    BUL(doc, "Rotation des clés Azure : à faire d'urgence, plusieurs clés ont été partagées en clair dans les échanges de mise en place.")
    BUL(doc, "SLA agent : la valeur cible de 24 heures ouvrées n'est pas encore alertée automatiquement (KPI présent mais alerte à câbler).")
    BUL(doc, "Import collaborateurs : sans référentiel chargé, tous les dossiers passent en revue manuelle par l'agent. Prévoir l'import des matricules ERANOVE avant lancement.")

    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════
    # 9. LIVRABLES DOCUMENTAIRES
    # ═══════════════════════════════════════════════════════════════════
    H1(doc, "9. Livrables documentaires")

    P(doc,
      "L'ensemble des livrables du projet est centralisé dans le dossier "
      "MA2E_Livrables à la racine du repository virtual-ai. Les scripts "
      "de génération Python (_diagrams*.py, gen_*.py) permettent de "
      "régénérer chaque diagramme ou document à volonté.")

    H2(doc, "Documents officiels")
    TABLE(doc,
          ["Nom du fichier", "Contenu"],
          [
              ["MA2E_Cahier_des_Charges_v1.docx", "Cahier des charges fonctionnel complet"],
              ["MA2E_Architecture_Technique_v1.docx", "Architecture technique détaillée"],
              ["MA2E_Architecture_Deploiement_v1.docx", "Architecture de déploiement Azure"],
              ["MA2E_Plan_de_Tests_v1.docx", "Plan de tests avec pyramide des tests"],
              ["MA2E_Backlog_v1.xlsx", "Backlog produit complet (User Stories US-01 à US-38)"],
              ["MA2E_CVATL_v2.pptx", "Présentation du Comité de Validation Architecture (dernière version)"],
              ["MA2E_Manuel_Utilisateur_v2.docx", "Manuel utilisateur au format procédural (à compléter avec captures)"],
              ["MA2E_Compte_Rendu_Juin_2026.docx", "Compte-rendu détaillé du Sprint 1 et démarrage Sprint 2"],
          ],
          col_widths=[Cm(6.5), Cm(9.5)])

    H2(doc, "Documents de support à la présentation CVATL")
    BUL(doc, "CVATL_SPEECH.md — script de présentation général.")
    BUL(doc, "CVATL_SPEECH_ARCHITECTURE.md — speech détaillé slide par slide (11 slides).")
    BUL(doc, "PHASE2_ROADMAP.md — roadmap post-CVATL.")
    BUL(doc, "PLAN_CONDUITE_CHANGEMENT.md — plan de conduite du changement pour le rollout.")
    BUL(doc, "GUIDE_SOCIETAIRE.md — guide utilisateur pour le sociétaire final.")
    BUL(doc, "GUIDE_GESTIONNAIRE.md — guide utilisateur pour l'agent MA2E.")
    BUL(doc, "AUDIT_BACKLOG.md — audit du backlog en cours.")
    BUL(doc, "PROD_DEPLOYMENT.md — procédure complète de déploiement production.")

    H2(doc, "Diagrammes générés")
    P(doc,
      "L'ensemble des diagrammes utilisés dans le CVATL est disponible au "
      "format PNG dans MA2E_Livrables. Les sources Python (matplotlib) "
      "sont dans les fichiers _diagrams*.py et permettent de régénérer "
      "les diagrammes à toute modification.")

    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════
    # 10. CONTACTS CLÉS
    # ═══════════════════════════════════════════════════════════════════
    H1(doc, "10. Contacts clés")

    TABLE(doc,
          ["Rôle", "Personne / entité", "Périmètre"],
          [
              ["Chef de projet", "À compléter",
               "Direction Digitalisation & Innovation (DDI) — GS2E"],
              ["DevOps / Infrastructure", "Line Teki",
               "Déploiement, containers Docker, nginx, DNS Azure"],
              ["Sponsor MA2E", "À compléter",
               "Direction MA2E — validation métier"],
              ["Sponsor GS2E", "À compléter",
               "Direction GS2E — gouvernance groupe"],
              ["Compte Meta WhatsApp Business", "Compte administré par la DSI GS2E",
               "Gestion du numéro pilote et rotation des tokens Cloud API"],
              ["Support Azure", "Portail Azure du tenant GS2E",
               "Escalades sur incidents plateforme Cloud"],
              ["Contact ARTCI", "À définir",
               "DPO à désigner pour déclarations et incidents éventuels"],
          ],
          col_widths=[Cm(4), Cm(5), Cm(7)])

    P(doc,
      "Il est recommandé de compléter les cases « À compléter » avec les "
      "coordonnées définitives (adresses e-mail, numéros de téléphone) "
      "dès validation par la Direction Digitalisation & Innovation.",
      italic=True)

    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════
    # 11. ROADMAP PHASE 2
    # ═══════════════════════════════════════════════════════════════════
    H1(doc, "11. Roadmap Phase 2 et reste à faire")

    H2(doc, "État à la date de la passation")
    P(doc,
      "L'ensemble des User Stories du Sprint 2 initialement prévues avant "
      "les congés (US-19 à US-26, US-38) a été livré et déployé sur "
      "l'environnement pilote Azure. Le rate limit applicatif sur les "
      "endpoints sensibles a été ajouté en dernier lieu pour préparer les "
      "tests de sécurité à venir. Aucun développement bloquant n'est en "
      "cours au moment de la passation.")

    H2(doc, "Sujets Phase 2 (post-CVATL)")
    BUL(doc, "Intégration Active Directory ERANOVE — attente ouverture firewall DSI.")
    BUL(doc, "Migration du JWT vers cookie httpOnly + refresh token.")
    BUL(doc, "Intégration Perfect-Vision (SI comptable) — US-30 à US-35.")
    BUL(doc, "Synchronisation temps réel avec SI RH du groupe.")
    BUL(doc, "Mise en cluster PostgreSQL (Patroni ou Azure Database for PostgreSQL).")
    BUL(doc, "Monitoring complet (Prometheus, Grafana, alerting).")
    BUL(doc, "Application mobile native (iOS et Android) — décision à valider selon retour usage POC.")
    BUL(doc, "Migration éventuelle vers Laravel côté backend (spécifiée dans le PRD initial, reportée en Phase 2).")

    H2(doc, "Points d'attention métier pour la reprise")
    P(doc,
      "Trois éléments non techniques nécessitent une attention "
      "particulière au retour de congés :")
    NUM(doc, "Signature de la convention CAGECFI, préalable à l'ouverture des connecteurs Perfect-Vision.")
    NUM(doc, "Désignation officielle du DPO MA2E (obligatoire loi 2013-450) pour les demandes de droit d'accès.")
    NUM(doc, "Validation du numéro WhatsApp définitif par la Direction MA2E, remplaçant le numéro pilote actuel.")

    doc.add_page_break()

    # ── Clôture ────────────────────────────────────────────────────────
    H1(doc, "Clôture du document")

    P(doc,
      "Ce document de passation a été rédigé dans le cadre d'un congé "
      "temporaire. Il centralise l'ensemble des informations "
      "opérationnelles, techniques et métier nécessaires à la "
      "continuité du projet MA2E Plateforme Digitale d'Identification.")

    P(doc,
      "En cas de doute sur un point non couvert, se référer prioritairement "
      "au dossier MA2E_Livrables, au repository Git du projet et aux "
      "commentaires du code source, qui documentent systématiquement les "
      "décisions techniques prises.")

    P(doc,
      "Le compte-rendu détaillé du Sprint 1 et du démarrage du Sprint 2 "
      "(MA2E_Compte_Rendu_Juin_2026.docx) apporte le contexte "
      "chronologique complet des choix effectués depuis la démonstration "
      "du 15 mai 2026.")

    doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p.add_run(f"Document généré le {date.today().strftime('%d/%m/%Y')} — MA2E · Groupe GS2E")
    set_run(r, size=9, italic=True, color=GRAY)

    doc.save(output_path)
    return output_path


if __name__ == "__main__":
    out = Path(__file__).parent / "MA2E_Passation_Projets_Conges.docx"
    saved = build_passation(out)
    print(f"Fichier généré : {saved}")
    print(f"Taille : {saved.stat().st_size} octets")
