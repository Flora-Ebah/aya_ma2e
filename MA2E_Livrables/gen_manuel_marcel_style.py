"""Manuel Utilisateur MA2E — style Marcel'IA (concis, pro, peu de captures).

Version courte alignée sur la vraie structure de l'app :
- 6 groupes de sidebar principale : Espace de travail, Chatbot, Référentiels,
  Administration, Conformité ARTCI, Paramètres.
- Chaque groupe = 1 section H2 avec 1 seule capture d'écran.
- Notes N.B uniquement sur les points VRAIMENT sensibles.
- ~11 captures au total, pas 25.
"""
from __future__ import annotations
from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor


# ─── Palette EXACTE Marcel'IA ──────────────────────────────────────────
HEADING_BLUE = RGBColor(0x4F, 0x81, 0xBD)
NB_RED = RGBColor(0xFF, 0x00, 0x00)
BODY_GRAY = RGBColor(0x37, 0x41, 0x51)
INK_400 = RGBColor(0x94, 0xA3, 0xB8)
INK_200_HEX = "E2E8F0"
INK_50_HEX = "F8FAFC"
FONT_NAME = "Calibri"


# ─── Helpers ──────────────────────────────────────────────────────────
def shade(cell, hex_color: str):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def cell_borders(cell, size=8, color=INK_200_HEX):
    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = OxmlElement("w:tcBorders")
    for edge in ("top", "left", "bottom", "right"):
        b = OxmlElement(f"w:{edge}")
        b.set(qn("w:val"), "dashed")
        b.set(qn("w:sz"), str(size))
        b.set(qn("w:color"), color)
        tcBorders.append(b)
    tcPr.append(tcBorders)


def set_run(run, *, size=11, bold=False, italic=False, color=None):
    run.font.name = FONT_NAME
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    if color is not None:
        run.font.color.rgb = color


def configure_styles(doc):
    h1 = doc.styles["Heading 1"]
    h1.font.name = FONT_NAME
    h1.font.size = Pt(16)
    h1.font.bold = True
    h1.font.color.rgb = HEADING_BLUE
    h1.paragraph_format.space_before = Pt(24)
    h1.paragraph_format.space_after = Pt(12)

    h2 = doc.styles["Heading 2"]
    h2.font.name = FONT_NAME
    h2.font.size = Pt(13)
    h2.font.bold = True
    h2.font.color.rgb = HEADING_BLUE
    h2.paragraph_format.space_before = Pt(14)
    h2.paragraph_format.space_after = Pt(6)

    normal = doc.styles["Normal"]
    normal.font.name = FONT_NAME
    normal.font.size = Pt(11)
    normal.font.color.rgb = BODY_GRAY
    normal.paragraph_format.space_after = Pt(6)


def H1(doc, text, *, centered=False):
    p = doc.add_heading(text, level=1)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER if centered else WD_ALIGN_PARAGRAPH.LEFT


def H2(doc, text):
    p = doc.add_heading(text, level=2)
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT


def P(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_after = Pt(6)
    r = p.add_run(text)
    set_run(r, size=11, color=BODY_GRAY)


def NB(doc, text):
    """N.B en rouge gras — exactement comme Marcel'IA."""
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(8)
    r = p.add_run(f"N.B : {text}")
    set_run(r, size=11, bold=True, color=NB_RED)


def SCREENSHOT(doc, description):
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    cell = tbl.rows[0].cells[0]
    cell.width = Cm(15)
    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    shade(cell, INK_50_HEX)
    cell_borders(cell, size=8, color=INK_200_HEX)

    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(20)
    p.paragraph_format.space_after = Pt(0)
    r = p.add_run("Capture d'écran à insérer")
    set_run(r, size=10, bold=True, italic=True, color=BODY_GRAY)

    p2 = cell.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p2.paragraph_format.space_before = Pt(2)
    p2.paragraph_format.space_after = Pt(20)
    r2 = p2.add_run(description)
    set_run(r2, size=9.5, italic=True, color=INK_400)

    doc.add_paragraph()


def add_toc(doc):
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r = title.add_run("Table des matières")
    set_run(r, size=16, bold=True, color=HEADING_BLUE)
    title.paragraph_format.space_after = Pt(12)

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
    fldChar3.text = ("Ouvrez ce document dans Word puis faites clic droit sur "
                     "cette ligne → « Mettre à jour les champs » pour générer "
                     "la table des matières.")
    fldChar4 = OxmlElement("w:fldChar")
    fldChar4.set(qn("w:fldCharType"), "end")
    run._r.append(fldChar1)
    run._r.append(instrText)
    run._r.append(fldChar2)
    run._r.append(fldChar3)
    run._r.append(fldChar4)


# ─── Construction du manuel ────────────────────────────────────────────
def build_manuel(output_path: Path) -> Path:
    doc = Document()
    section = doc.sections[0]
    section.left_margin = Cm(2.0)
    section.right_margin = Cm(2.0)
    section.top_margin = Cm(1.6)
    section.bottom_margin = Cm(1.6)
    configure_styles(doc)

    H1(doc, "Manuel Utilisateur – MA2E", centered=True)
    add_toc(doc)
    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════
    # APPLICATION WEB — Back-office
    # ═══════════════════════════════════════════════════════════════════
    H1(doc, "Application web")

    # Accès
    H2(doc, "Accès à l'application")
    P(doc,
      "Accéder au back-office MA2E via l'URL "
      "https://ma2e.swedencentral.cloudapp.azure.com. Saisir l'adresse email "
      "professionnelle et le mot de passe, puis valider avec le code à 6 "
      "chiffres généré par l'application d'authentification (MFA).")
    NB(doc,
       "Après 5 tentatives infructueuses, le compte est bloqué 15 minutes.")
    SCREENSHOT(doc, "Écran de connexion et étape MFA")

    # Interface principale
    H2(doc, "Présentation de l'interface")
    P(doc,
      "L'interface est composée d'une sidebar principale à gauche donnant "
      "accès à six espaces : Espace de travail, Pilotage du chatbot, "
      "Référentiels, Administration, Conformité ARTCI et Paramètres. Chaque "
      "espace ouvre une page hub avec sa propre sous-navigation contextuelle.")
    NB(doc,
       "La sidebar affiche uniquement les espaces auxquels l'utilisateur a "
       "accès selon son rôle.")
    SCREENSHOT(doc, "Interface principale — sidebar 6 espaces + zone de travail")

    # Espace de travail
    H2(doc, "Espace de travail — Dossiers & Reporting")
    P(doc,
      "L'Espace de travail regroupe la validation des dossiers et le "
      "reporting opérationnel. La liste des dossiers est filtrable par "
      "statut, employeur, période ou agent assigné. Cliquer sur un dossier "
      "ouvre son détail : photos de la CNI, comparaison OCR / saisie, "
      "conversation, journal d'audit.")
    P(doc,
      "Trois actions sont possibles depuis le détail : Valider, Refuser "
      "avec motif, Demander un complément. Chaque décision déclenche une "
      "notification automatique au sociétaire.")
    NB(doc,
       "Un dossier ouvert par un agent est verrouillé pour les autres "
       "agents pendant 15 minutes.")
    SCREENSHOT(doc, "Liste des dossiers avec filtres et bouton Exporter Excel")
    SCREENSHOT(doc, "Détail d'un dossier — OCR / saisie + boutons de décision")

    P(doc,
      "La sous-section Reporting affiche les indicateurs opérationnels : "
      "volumes traités, délais moyens, taux de validation, entonnoir de "
      "conversion, alertes KPI. Un export PDF est disponible.")
    SCREENSHOT(doc, "Tableau de bord Reporting avec KPI et bouton Export PDF")

    # Pilotage du chatbot
    H2(doc, "Pilotage du chatbot")
    P(doc,
      "L'espace Pilotage regroupe la configuration de l'assistant IA "
      "(personnalité, langue, ton), les workflows conversationnels "
      "(parcours d'inscription, sous-flux de correction), les modèles de "
      "messages envoyés au sociétaire et la base de connaissances (RAG).")
    NB(doc,
       "Les paramètres techniques du modèle IA (température, embeddings) "
       "sont réservés à l'IT.")
    SCREENSHOT(doc, "Espace Pilotage du chatbot — sous-navigation contextuelle")

    # Référentiels
    H2(doc, "Référentiels")
    P(doc,
      "L'espace Référentiels centralise la configuration des sociétés "
      "affiliées (CIE, SODECI, SMB, AD ERANOVE) et l'import en masse des "
      "collaborateurs à partir d'un fichier CSV ou Excel. Un mode Dry-run "
      "permet de vérifier les erreurs avant enregistrement.")
    SCREENSHOT(doc, "Espace Référentiels — employeurs et import collaborateurs")

    # Administration
    H2(doc, "Administration")
    P(doc,
      "L'espace Administration permet de gérer les comptes utilisateurs, "
      "les rôles métier (Agent Validateur, Superviseur, Lecteur, IT, "
      "Viewer) et les paramètres de sécurité (politique de mot de passe, "
      "MFA, verrouillage de session).")
    SCREENSHOT(doc, "Espace Administration — utilisateurs et rôles")

    # Conformité
    H2(doc, "Conformité ARTCI")
    P(doc,
      "L'espace Conformité regroupe le journal d'audit (chronologique, "
      "filtrable, exportable) et la consultation des conversations pour "
      "les demandes de droit d'accès ARTCI.")
    NB(doc,
       "Le journal d'audit est en mode append-only. Aucune modification "
       "ni suppression n'est possible. Conservation 10 ans (loi 2013-450).")
    SCREENSHOT(doc, "Espace Conformité ARTCI — journal d'audit")

    # Paramètres
    H2(doc, "Paramètres et profil")
    P(doc,
      "L'espace Paramètres regroupe les paramètres généraux de la "
      "plateforme et le profil personnel de l'utilisateur connecté "
      "(informations, mot de passe, MFA).")

    # Fin de session
    H2(doc, "Fin de session")
    P(doc,
      "Cliquer sur l'icône de profil en haut à droite puis sur "
      "« Déconnexion ». La session est également fermée automatiquement "
      "après 20 minutes d'inactivité.")

    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════
    # PARCOURS SOCIÉTAIRE
    # ═══════════════════════════════════════════════════════════════════
    H1(doc, "Parcours sociétaire (Web Chat & WhatsApp)")

    # Accès
    H2(doc, "Accès au portail")
    P(doc,
      "Le sociétaire accède au portail via l'URL "
      "https://ma2e.swedencentral.cloudapp.azure.com ou envoie « Bonjour » "
      "au numéro WhatsApp communiqué par la DSI GS2E.")
    NB(doc,
       "L'inscription est réservée aux collaborateurs des sociétés du "
       "groupe GS2E (CIE, SODECI, SMB, AD ERANOVE).")
    SCREENSHOT(doc, "Écran d'accueil du portail sociétaire")

    # Parcours
    H2(doc, "Parcours d'inscription")
    P(doc,
      "Le parcours conversationnel se déroule en cinq étapes : recueil du "
      "consentement ARTCI, saisie du matricule et des informations "
      "personnelles, téléversement du recto et du verso de la CNI, "
      "validation des données extraites par l'OCR, soumission finale du "
      "dossier.")
    NB(doc,
       "En cas de refus du consentement ARTCI, la conversation s'arrête "
       "immédiatement et aucune donnée n'est stockée.")
    SCREENSHOT(doc, "Parcours d'inscription — exemple d'étape (matricule / CNI)")

    # Suivi
    H2(doc, "Suivi du dossier et notifications")
    P(doc,
      "Le sociétaire peut consulter à tout moment le statut de son dossier "
      "via la carte « Vérification » du portail ou la commande « Statut » "
      "sur WhatsApp. Chaque décision (validation, refus, demande de "
      "complément) déclenche une notification immédiate sur WhatsApp et par "
      "email.")
    SCREENSHOT(doc, "Écran de suivi du statut du dossier")

    # Reprise
    H2(doc, "Reprise d'une session interrompue")
    P(doc,
      "En cas d'abandon, le sociétaire peut revenir sur WhatsApp ou sur le "
      "portail web avec le même identifiant. Le bot propose de reprendre à "
      "l'étape où le parcours s'est interrompu.")
    NB(doc,
       "La session est conservée 30 jours. Au-delà, un nouveau parcours "
       "doit être démarré.")

    doc.add_page_break()

    # ═══════════════════════════════════════════════════════════════════
    # SUPPORT
    # ═══════════════════════════════════════════════════════════════════
    H1(doc, "Support et escalade")
    P(doc,
      "En cas de dysfonctionnement, contacter le canal d'escalade adapté à "
      "la nature de l'incident : Support Technique MA2E pour les incidents "
      "fonctionnels, DPO MA2E pour les demandes ARTCI, Support Éditeur DSI "
      "GS2E pour les incidents plateforme.")
    NB(doc,
       "Les coordonnées précises seront communiquées par la Direction "
       "Digitalisation & Innovation dès leur validation.")

    doc.save(output_path)
    return output_path


if __name__ == "__main__":
    out = Path(__file__).parent / "MA2E_Manuel_Utilisateur_v2.docx"
    saved = build_manuel(out)
    print(f"Fichier généré : {saved}")
    print(f"Taille : {saved.stat().st_size} octets")
