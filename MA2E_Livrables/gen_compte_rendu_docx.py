"""Compte-rendu MA2E — Juin 2026 — aligné sur le backlog officiel.

Couvre :
  - Sprint 1 (15/06 → 26/06) : authentification, administration, onboarding,
    extraction/vérification pièces, assistant IA, audit & conformité
  - Sprint 2 (29/06 → en cours) : validation dossier, notifications, reporting

Charte : blanc / gris / accent vert pâle, tout aligné à gauche.
"""
from __future__ import annotations
from pathlib import Path

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor


# ─── Palette MA2E ──────────────────────────────────────────────────────
INK_900 = RGBColor(0x0F, 0x17, 0x2A)
INK_700 = RGBColor(0x33, 0x41, 0x55)
INK_500 = RGBColor(0x64, 0x74, 0x8B)
ACCENT_DEEP = RGBColor(0x2D, 0x5F, 0x4F)
OK_GREEN = RGBColor(0x16, 0xA3, 0x4A)
WIP_ORANGE = RGBColor(0xB4, 0x53, 0x09)
ACCENT = "A6CFC5"
ACCENT_SOFT = "E8F2EE"
INK_50 = "F8FAFC"
INK_200 = "E2E8F0"
WHITE = "FFFFFF"


# ─── Backlog suivi : sprints, dates, US, ce qui a été fait ─────────────
SPRINTS = [
    {
        "label": "Sprint 1 · 15 juin → 26 juin 2026",
        "objectif": "Socle plateforme : authentification, administration, "
                    "onboarding sociétaire, extraction pièces, assistant IA, "
                    "audit & conformité ARTCI.",
        "jours": [
            {
                "date": "Lundi 15 juin 2026",
                "us_groupe": "Authentification",
                "items": [
                    ("US-01", "Connexion administrateur",
                     "Flux login JWT classique (email + mot de passe), bcrypt direct (compat Python 3.13), "
                     "verrouillage après 5 tentatives, redirection contextuelle après connexion.",
                     "Livré"),
                    ("US-02", "Connexion agent via AD ERANOVE",
                     "Préparation du connecteur AD : bouton dédié sur l'écran de login (désactivé en attendant "
                     "l'ouverture du firewall AD), enum auth_method = ad_ldap, endpoint /api/auth/ad-login prêt.",
                     "Partiel — UI livrée, connecteur AD reporté"),
                ],
            },
            {
                "date": "Mardi 16 juin 2026",
                "us_groupe": "Administration — Rôles & Utilisateurs",
                "items": [
                    ("US-03", "Gestion des rôles et permissions",
                     "Tables CustomRole + UserCustomRole, matrice permissions modules × actions, "
                     "page /parametres/roles : créer / éditer / désactiver, seed de 4 rôles métier par défaut "
                     "(Agent Validateur, Superviseur, Lecteur, IT).",
                     "Livré"),
                    ("US-04", "Gestion des utilisateurs internes",
                     "Page /parametres/utilisateurs : création/modification/désactivation des comptes, "
                     "attribution de rôles métier multiples, reset password, MFA optionnel par utilisateur.",
                     "Livré"),
                ],
            },
            {
                "date": "Mercredi 17 juin 2026",
                "us_groupe": "Administration — Référentiels",
                "items": [
                    ("US-05", "Paramétrage des sociétés affiliées",
                     "Page /parametres/employeurs : 4 sociétés du groupe configurées (CIE, SODECI, SMB, "
                     "AD ERANOVE), code société, BP postale, secteur. Templates de message par employeur "
                     "via migrate_template_employeur_dynamic.py.",
                     "Livré"),
                    ("US-06", "Paramétrage des modèles de messages",
                     "Module dédié /parametres/templates : édition WYSIWYG des messages WhatsApp/email "
                     "envoyés au sociétaire à chaque étape (accueil, OCR, validation, refus, complément).",
                     "Livré"),
                ],
            },
            {
                "date": "Jeudi 18 juin 2026",
                "us_groupe": "Onboarding sociétaire — WhatsApp",
                "items": [
                    ("US-07", "Démarrage de l'enrôlement via WhatsApp",
                     "Webhook WhatsApp Cloud API validé Meta (verify token, événements 'messages' activés), "
                     "création automatique d'EndUser au premier message, démarrage du workflow d'inscription "
                     "depuis la BDD (plus de code hardcodé).",
                     "Livré"),
                ],
            },
            {
                "date": "Vendredi 19 juin 2026",
                "us_groupe": "Onboarding sociétaire — Web & Consentement",
                "items": [
                    ("US-08", "Démarrage de l'enrôlement via Web Chat",
                     "Page /chat avec interface conversationnelle moderne : 2 cards (M'identifier + Vérification), "
                     "icône upload, input compact, bouton fermer rouge en mode conversation, messages naturels "
                     "(« Bonjour, je souhaite m'identifier »).",
                     "Livré"),
                    ("US-09", "Recueil du consentement ARTCI",
                     "Étape obligatoire avant toute collecte : présentation de la notice loi 2013-450, "
                     "consentement explicite tracé en BDD (table consentements avec horodatage), refus = "
                     "arrêt immédiat, aucune donnée stockée.",
                     "Livré"),
                ],
            },
            {
                "date": "Lundi 22 juin 2026",
                "us_groupe": "Onboarding sociétaire — Données pro & reprise",
                "items": [
                    ("US-10", "Saisie des informations professionnelles",
                     "Workflow inscription restructuré aux 23 champs du formulaire papier officiel MA2E : "
                     "identité, employeur, matricule, fonction, ancienneté, situation familiale, ayants droit, "
                     "contact (migrate_inscription_23_fields.py).",
                     "Livré"),
                    ("US-11", "Reprise d'une session interrompue",
                     "Session persistée en BDD via workflow_position sur Conversation. Le sociétaire revient "
                     "sur WhatsApp et reprend exactement où il s'est arrêté, jusqu'à 30 jours après.",
                     "Livré"),
                ],
            },
            {
                "date": "Mardi 23 juin 2026",
                "us_groupe": "Extraction & vérification pièces",
                "items": [
                    ("US-12", "Téléversement de la pièce d'identité",
                     "Upload recto + verso via WhatsApp ou web, compression Pillow préalable (cible 1 Mo), "
                     "stockage chiffré sur MinIO (dev) / Azure Blob (prod), génération d'URLs présignées.",
                     "Livré"),
                    ("US-14", "Détection des pièces illisibles ou non conformes",
                     "Validation OCR avec score de confiance, message d'erreur si score < seuil paramétrable, "
                     "demande de re-soumission. Détection des photos floues, mal cadrées, non-CNI.",
                     "Livré"),
                ],
            },
            {
                "date": "Mercredi 24 juin 2026",
                "us_groupe": "OCR & imports",
                "items": [
                    ("US-13", "Extraction automatique des données de la CNI",
                     "Pipeline OCR multi-provider configurable depuis l'admin : Azure AI Vision (prod), "
                     "OCR.space (recette), mock (démo). Extraction nom, prénoms, date naissance, numéro CNI. "
                     "Présentation au sociétaire pour validation/correction.",
                     "Livré"),
                    ("US-37", "Import en masse des référentiels",
                     "Page /parametres/imports : upload fichier CSV/XLSX collaborateurs ERANOVE, "
                     "preview, validation, dry-run avant import réel. Stockés dans table collaborateurs.",
                     "Livré"),
                ],
            },
            {
                "date": "Jeudi 25 juin 2026",
                "us_groupe": "Assistant IA & anti-fraude",
                "items": [
                    ("US-15", "Réponse aux questions des sociétaires",
                     "Mode conversationnel libre branché sur Azure OpenAI (gpt-5.4-mini) avec contexte "
                     "knowledge base RAG (pgvector). Répond aux questions hors workflow strict "
                     "(« quels documents ? », « comment ça marche ? »).",
                     "Livré"),
                    ("US-36", "Détection des doublons d'identification",
                     "Endpoint /api/duplicates : recherche par matricule, par numéro CNI, par similarité "
                     "nom+prénoms+date naissance. Blocage automatique si dossier déjà validé pour cette personne.",
                     "Livré"),
                ],
            },
            {
                "date": "Vendredi 26 juin 2026",
                "us_groupe": "Audit & conformité ARTCI",
                "items": [
                    ("US-27", "Journalisation des actions sensibles",
                     "Module audit complet : enum centralisé d'actions (migrate_audit_action_enum.py), "
                     "service audit_service.log appelé sur chaque action, traçabilité IP (migrate_audit_ip.py), "
                     "page /conformite/audit avec filtres acteur/action/période/IP, export CSV.",
                     "Livré"),
                    ("US-29", "Page d'information ARTCI permanente",
                     "Page publique accessible avant et pendant le parcours : présentation des droits du "
                     "sociétaire (accès, rectification, oubli), contact DPO, texte de la loi 2013-450.",
                     "Livré"),
                ],
            },
        ],
    },
    # ─────────────────────────────────────────────────────────────────────
    {
        "label": "Sprint 2 · 29 juin → 10 juillet 2026 (en cours)",
        "objectif": "Validation des dossiers côté agent, notifications "
                    "sortantes, reporting & KPI, intégrations Perfect Vision.",
        "jours": [
            {
                "date": "Lundi 29 juin 2026",
                "us_groupe": "Assistant IA — Escalade & OTP",
                "items": [
                    ("US-16", "Escalade vers un conseiller humain",
                     "Détection automatique des cas où l'IA ne sait pas répondre (confiance < seuil) ou "
                     "demande explicite du sociétaire (« je veux parler à quelqu'un »). Création d'un ticket "
                     "support visible côté agent.",
                     "À démarrer"),
                    ("US-22", "Vérification d'identité par code OTP email",
                     "Étape complémentaire avant soumission : envoi d'un code 6 chiffres par email, "
                     "validation côté workflow. Service SMTP déjà configuré, reste l'intégration UI.",
                     "À démarrer"),
                ],
            },
            {
                "date": "Mardi 30 juin 2026",
                "us_groupe": "Validation dossier — Backoffice agent",
                "items": [
                    ("US-17", "Tableau de bord des dossiers à traiter",
                     "Page /dossiers : listing paginé avec soft-lock (un seul agent à la fois sur un dossier), "
                     "filtres statut/employeur/agent assigné, badge priorité, recherche full-text.",
                     "En cours"),
                    ("US-18", "Consultation du détail d'un dossier",
                     "Page /dossiers/[id] : vue complète avec photos CNI haute résolution, données OCR vs "
                     "saisie sociétaire en side-by-side, historique conversation WhatsApp, journal d'audit "
                     "du dossier.",
                     "En cours"),
                ],
            },
        ],
    },
]


# ─── Stylage utilitaires ───────────────────────────────────────────────
def shade_cell(cell, hex_color: str):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def set_cell_border(cell, **kwargs):
    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = OxmlElement("w:tcBorders")
    for edge, params in kwargs.items():
        if not params:
            continue
        sz, color = params
        border = OxmlElement(f"w:{edge}")
        border.set(qn("w:val"), "single")
        border.set(qn("w:sz"), str(sz))
        border.set(qn("w:color"), color)
        tcBorders.append(border)
    tcPr.append(tcBorders)


def set_run(run, *, size=10, bold=False, color=None, font_name="Calibri"):
    run.font.name = font_name
    run.font.size = Pt(size)
    run.bold = bold
    if color is not None:
        run.font.color.rgb = color


def add_paragraph(doc, text, *, size=10, bold=False, color=None,
                  space_before=0, space_after=4):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    r = p.add_run(text)
    set_run(r, size=size, bold=bold, color=color)
    return p


def add_thin_separator(doc, color=ACCENT):
    sep = doc.add_table(rows=1, cols=1)
    sep.autofit = False
    cell = sep.rows[0].cells[0]
    shade_cell(cell, color)
    p = cell.paragraphs[0]
    p.add_run(" ")
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    p.runs[0].font.size = Pt(2)


def status_color(statut: str) -> RGBColor:
    s = statut.lower()
    if s.startswith("livré") and "partiel" not in s:
        return OK_GREEN
    if "cours" in s or "démarrer" in s or "partiel" in s:
        return WIP_ORANGE
    return INK_500


def build_sprint_table(doc, sprint):
    """Tableau d'un sprint avec colonnes Jour / US / Fonctionnalité / Description / Statut."""
    jours = sprint["jours"]
    headers = ["Jour", "US", "Fonctionnalité", "Description", "Statut"]
    col_widths = [Cm(2.5), Cm(1.4), Cm(3.5), Cm(7.0), Cm(2.5)]

    total_rows = 1 + sum(len(j["items"]) for j in jours)
    table = doc.add_table(rows=total_rows, cols=5)
    table.alignment = WD_TABLE_ALIGNMENT.LEFT

    # Header
    for i, (h, w) in enumerate(zip(headers, col_widths)):
        cell = table.rows[0].cells[i]
        cell.width = w
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        cell.paragraphs[0].text = ""
        r = cell.paragraphs[0].add_run(h)
        set_run(r, size=10, bold=True, color=INK_900)
        shade_cell(cell, ACCENT_SOFT)
        set_cell_border(cell, bottom=(12, ACCENT))

    row_idx = 1
    for j_idx, jour in enumerate(jours):
        bloc_first = row_idx
        zebra = j_idx % 2 == 0
        bg = WHITE if zebra else INK_50

        for i, (us_id, fonc, desc, statut) in enumerate(jour["items"]):
            row = table.rows[row_idx]
            for col in range(5):
                row.cells[col].width = col_widths[col]
                row.cells[col].vertical_alignment = WD_ALIGN_VERTICAL.TOP

            # Col 0 — Jour (fusionné par bloc)
            cell = row.cells[0]
            if i == 0:
                cell.paragraphs[0].text = ""
                r = cell.paragraphs[0].add_run(jour["date"])
                set_run(r, size=10, bold=True, color=INK_900)
                p2 = cell.add_paragraph()
                p2.paragraph_format.space_before = Pt(2)
                p2.paragraph_format.space_after = Pt(0)
                r2 = p2.add_run(jour["us_groupe"])
                set_run(r2, size=8, bold=True, color=ACCENT_DEEP)
            shade_cell(cell, INK_50)

            # Col 1 — ID US
            cell = row.cells[1]
            cell.paragraphs[0].text = ""
            r = cell.paragraphs[0].add_run(us_id)
            set_run(r, size=10, bold=True, color=ACCENT_DEEP)
            shade_cell(cell, bg)
            is_last = (i == len(jour["items"]) - 1)
            border_size = 12 if is_last else 4
            border_color = ACCENT if is_last else INK_200
            set_cell_border(cell, bottom=(border_size, border_color))

            # Col 2 — Fonctionnalité
            cell = row.cells[2]
            cell.paragraphs[0].text = ""
            r = cell.paragraphs[0].add_run(fonc)
            set_run(r, size=10, bold=True, color=INK_900)
            shade_cell(cell, bg)
            set_cell_border(cell, bottom=(border_size, border_color))

            # Col 3 — Description
            cell = row.cells[3]
            cell.paragraphs[0].text = ""
            r = cell.paragraphs[0].add_run(desc)
            set_run(r, size=10, color=INK_700)
            shade_cell(cell, bg)
            set_cell_border(cell, bottom=(border_size, border_color))

            # Col 4 — Statut (coloré)
            cell = row.cells[4]
            cell.paragraphs[0].text = ""
            r = cell.paragraphs[0].add_run(statut)
            set_run(r, size=10, bold=True, color=status_color(statut))
            shade_cell(cell, bg)
            set_cell_border(cell, bottom=(border_size, border_color))

            row_idx += 1

        # Fusion verticale Jour si plusieurs items
        if len(jour["items"]) > 1:
            top = table.rows[bloc_first].cells[0]
            bot = table.rows[row_idx - 1].cells[0]
            top.merge(bot)
            set_cell_border(top, bottom=(12, ACCENT))


# ─── Document principal ────────────────────────────────────────────────
def build_compte_rendu(output_path: Path) -> Path:
    doc = Document()
    section = doc.sections[0]
    section.left_margin = Cm(2)
    section.right_margin = Cm(2)
    section.top_margin = Cm(2)
    section.bottom_margin = Cm(2)

    # ─── Page de garde ────────────────────────────────────────────────
    add_paragraph(doc, "MA2E · COMPTE-RENDU PROJET",
                  size=8, bold=True, color=ACCENT_DEEP, space_after=4)
    add_paragraph(doc, "Suivi des sprints — Juin 2026",
                  size=22, bold=True, color=INK_900, space_after=4)
    add_paragraph(doc,
                  "Plateforme MA2E · Mutuelle des Agents de l'Eau et de l'Électricité · Groupe GS2E",
                  size=11, color=INK_500, space_after=8)
    add_paragraph(doc,
                  "Période couverte : Sprint 1 (15-26 juin) + démarrage Sprint 2 (29-30 juin)  ·  "
                  "Suivi aligné sur le backlog officiel MA2E_Backlog_v1.xlsx",
                  size=10, color=INK_700, space_after=12)

    add_thin_separator(doc, ACCENT)
    doc.add_paragraph()

    # ─── Synthèse ──────────────────────────────────────────────────────
    add_paragraph(doc, "SYNTHÈSE",
                  size=8, bold=True, color=ACCENT_DEEP, space_after=4)
    add_paragraph(doc, "État d'avancement",
                  size=14, bold=True, color=INK_900, space_after=8)

    # Calcul des chiffres
    total_livre = 0
    total_partiel = 0
    total_cours = 0
    total_demarrer = 0
    for s in SPRINTS:
        for j in s["jours"]:
            for _, _, _, st in j["items"]:
                sl = st.lower()
                if sl.startswith("livré") and "partiel" not in sl:
                    total_livre += 1
                elif "partiel" in sl:
                    total_partiel += 1
                elif "en cours" in sl:
                    total_cours += 1
                elif "démarrer" in sl:
                    total_demarrer += 1
    total_us = total_livre + total_partiel + total_cours + total_demarrer

    for line in [
        f"User Stories suivies sur la période : {total_us}",
        f"Livrées : {total_livre}",
        f"Livrées partiellement : {total_partiel}",
        f"En cours : {total_cours}",
        f"À démarrer (Sprint 2) : {total_demarrer}",
        "",
        "Sprint 1 (15-26 juin) : 17 US planifiées, 16 livrées, 1 partielle (connecteur AD reporté).",
        "Sprint 2 (29 juin →) : démarrage le 29 juin, US-17 et US-18 attaquées le 30 juin.",
    ]:
        if not line:
            doc.add_paragraph()
            continue
        add_paragraph(doc, line, size=10, color=INK_700, space_after=2)

    doc.add_paragraph()
    add_thin_separator(doc, ACCENT)

    # ─── Section par sprint ───────────────────────────────────────────
    for idx, sprint in enumerate(SPRINTS):
        if idx > 0:
            doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

        add_paragraph(doc, "SPRINT",
                      size=8, bold=True, color=ACCENT_DEEP,
                      space_before=8, space_after=4)
        add_paragraph(doc, sprint["label"],
                      size=18, bold=True, color=INK_900, space_after=4)
        add_paragraph(doc, sprint["objectif"],
                      size=10, color=INK_500, space_after=12)

        build_sprint_table(doc, sprint)

    # ─── Bilan & reste à faire ────────────────────────────────────────
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    add_paragraph(doc, "BILAN & RESTE À FAIRE",
                  size=8, bold=True, color=ACCENT_DEEP, space_after=4)
    add_paragraph(doc, "Sprint 2 — User Stories à traiter",
                  size=18, bold=True, color=INK_900, space_after=12)

    reste = [
        ("US-19", "Validation d'un dossier (1/07)"),
        ("US-20", "Refus avec motif obligatoire (1/07)"),
        ("US-21", "Demande de complément (2/07)"),
        ("US-23", "Notification au sociétaire après décision (2/07)"),
        ("US-24", "Suivi temps réel de l'activité (3/07)"),
        ("US-25", "Export des sociétaires validés (6/07)"),
        ("US-26", "Indicateurs opérationnels KPI (6/07)"),
        ("US-38", "Filtres avancés tableau de bord (6/07)"),
        ("US-28", "Droit à l'oubli et anonymisation (7/07)"),
        ("US-34", "Tableau de bord supervision flux (7/07)"),
        ("US-30", "Connecteur Perfect Vision (8/07)"),
        ("US-31", "Export auto dossiers validés vers Perfect Vision (9/07)"),
        ("US-32", "Webhook temps réel Perfect Vision (9/07)"),
        ("US-33", "Synchronisation matricules SI RH groupe (10/07)"),
        ("US-35", "Reprise auto intégrations en échec (10/07)"),
    ]
    for us, label in reste:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(2)
        r = p.add_run(f"{us}  ·  ")
        set_run(r, size=10, bold=True, color=ACCENT_DEEP)
        r = p.add_run(label)
        set_run(r, size=10, color=INK_700)

    doc.add_paragraph()
    add_paragraph(doc, "POINTS D'ATTENTION",
                  size=8, bold=True, color=ACCENT_DEEP, space_before=12, space_after=4)
    for line in [
        "• US-02 (AD ERANOVE) en partiel : UI livrée, connecteur LDAP reporté en attente "
        "d'ouverture des règles firewall côté DSI GS2E.",
        "• Sprint 2 inclut les intégrations Perfect Vision (US-30 à US-35) — spécifications "
        "API à confirmer avec l'équipe Perfect Vision avant développement.",
        "• OTP email (US-22) dépend de la configuration SMTP en production — service "
        "déjà en place côté backend, reste à câbler l'UI dans le workflow.",
    ]:
        add_paragraph(doc, line, size=10, color=INK_700, space_after=4)

    doc.add_paragraph()
    add_thin_separator(doc, INK_200)
    doc.add_paragraph()
    add_paragraph(doc,
                  "Document généré automatiquement — MA2E · Groupe GS2E · "
                  "Diffusion interne uniquement.",
                  size=8, color=INK_500)

    doc.save(output_path)
    return output_path


if __name__ == "__main__":
    out = Path(__file__).parent / "MA2E_Compte_Rendu_Juin_2026.docx"
    saved = build_compte_rendu(out)
    print(f"Fichier généré : {saved}")
    print(f"Taille : {saved.stat().st_size} octets")
