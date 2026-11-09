"""Générateur de Manuel Utilisateur MA2E Premium au format Word (.docx).
Ce script produit un document Word hautement stylisé grâce à python-docx.
- Police moderne : Segoe UI
- Marges aérées : 2.2 cm
- Page de garde moderne et sobre
- Boîtes d'alerte (Callout boxes) avec bordures gauches couleur 3pt
- Tableaux aérés (padding personnalisé, en-têtes colorés, zébrure des lignes)
- Séparateurs de sections colorés
- Chapitres complets sur l'Administration, l'IA, le RAG, l'Import massive, et la Sécurité ARTCI.
"""
from datetime import date
from pathlib import Path
from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

# Colors
INK_900 = RGBColor(0x0F, 0x17, 0x2A)  # Slate 900
INK_700 = RGBColor(0x33, 0x41, 0x55)  # Slate 700
INK_500 = RGBColor(0x64, 0x74, 0x8B)  # Slate 500
INK_200 = "E2E8F0"
INK_100 = "F1F5F9"
INK_50 = "F8FAFC"

ACCENT_DEEP = RGBColor(0x2D, 0x5F, 0x4F)  # Deep Green (MA2E primary)
ACCENT_MUTED = RGBColor(0x4A, 0x8F, 0x7A)  # Soft Teal
ACCENT_HEX = "2D5F4F"
ACCENT = "A6CFC5"
ACCENT_SOFT = "E8F2EE"
WHITE = "FFFFFF"
COLOR_WHITE = RGBColor(0xFF, 0xFF, 0xFF)

FONT_NAME = "Segoe UI"

def set_cell_background(cell, hex_color: str):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)

def set_cell_margins(cell, top=120, bottom=120, left=180, right=180):
    """Calcule le padding interne de la cellule (en dxa)."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('w:top', top), ('w:bottom', bottom), ('w:left', left), ('w:right', right)]:
        node = OxmlElement(m)
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def set_cell_borders(cell, **kwargs):
    """Configure les bordures d'une cellule spécifique.
    Exemples: top=(sz, type, color), bottom=(sz, type, color), etc.
    """
    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = OxmlElement("w:tcBorders")
    for edge, params in kwargs.items():
        if params is None:
            # Supprimer la bordure
            border = OxmlElement(f"w:{edge}")
            border.set(qn("w:val"), "nil")
            tcBorders.append(border)
            continue
        sz, b_type, color = params
        border = OxmlElement(f"w:{edge}")
        border.set(qn("w:val"), b_type)
        border.set(qn("w:sz"), str(sz))
        border.set(qn("w:color"), color)
        tcBorders.append(border)
    tcPr.append(tcBorders)

def set_run(run, *, size=11, bold=False, italic=False, color=None):
    run.font.name = FONT_NAME
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    if color is not None:
        run.font.color.rgb = color
    # East-Asian fallback override
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:ascii"), FONT_NAME)
    rFonts.set(qn("w:hAnsi"), FONT_NAME)
    rFonts.set(qn("w:eastAsia"), FONT_NAME)
    rFonts.set(qn("w:cs"), FONT_NAME)

def set_doc_defaults(doc):
    style = doc.styles["Normal"]
    style.font.name = FONT_NAME
    style.font.size = Pt(11)
    style.font.color.rgb = INK_700
    
    # Marges document
    for section in doc.sections:
        section.top_margin = Cm(2.2)
        section.bottom_margin = Cm(2.2)
        section.left_margin = Cm(2.2)
        section.right_margin = Cm(2.2)
        
        # En-tête et Pied de page
        header = section.header
        hp = header.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        hr = hp.add_run("Mutuelle MA2E  ·  Plateforme Digitale d'Identification")
        set_run(hr, size=8.5, color=INK_500)
        
        footer = section.footer
        fp = footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        fr = fp.add_run("Diffusion Interne & Sociétaires  —  Document de Référence v1.0")
        set_run(fr, size=8.5, color=INK_500)

def H(doc, text, level=1):
    p = doc.add_paragraph()
    p.paragraph_format.keep_with_next = True
    if level == 1:
        p.paragraph_format.space_before = Pt(22)
        p.paragraph_format.space_after = Pt(8)
        run = p.add_run(text)
        set_run(run, size=18, bold=True, color=INK_900)
        # Ligne de séparation sous le Heading 1
        sep = doc.add_table(rows=1, cols=1)
        sep.alignment = WD_TABLE_ALIGNMENT.LEFT
        sep.autofit = False
        cell = sep.rows[0].cells[0]
        cell.width = Cm(16.6)
        set_cell_background(cell, ACCENT)
        set_cell_margins(cell, top=0, bottom=0, left=0, right=0)
        # border nil
        set_cell_borders(cell, top=None, bottom=None, left=None, right=None)
        sp = cell.paragraphs[0]
        sp.paragraph_format.space_before = Pt(0)
        sp.paragraph_format.space_after = Pt(0)
        s_run = sp.add_run(" ")
        set_run(s_run, size=1)
    elif level == 2:
        p.paragraph_format.space_before = Pt(16)
        p.paragraph_format.space_after = Pt(6)
        run = p.add_run(text)
        set_run(run, size=14, bold=True, color=ACCENT_DEEP)
    else:
        p.paragraph_format.space_before = Pt(11)
        p.paragraph_format.space_after = Pt(4)
        run = p.add_run(text)
        set_run(run, size=12, bold=True, color=INK_900)
    return p

def P(doc, text, bold=False, italic=False, size=11, color=INK_700, space_after=6):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.15
    run = p.add_run(text)
    set_run(run, size=size, bold=bold, italic=italic, color=color)
    return p

def BUL(doc, text):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.15
    run = p.add_run(text)
    set_run(run, size=11, color=INK_700)
    return p

def NUM(doc, text):
    p = doc.add_paragraph(style="List Number")
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.15
    run = p.add_run(text)
    set_run(run, size=11, color=INK_700)
    return p

def CALLOUT(doc, title, text, type_box="info"):
    """Crée un encadré d'alerte stylisé.
    Utilise un tableau 1x1 avec une bordure gauche épaisse et un fond doux.
    """
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    table.autofit = False
    
    cell = table.rows[0].cells[0]
    cell.width = Cm(16.6)
    
    # Choix des couleurs selon le type
    if type_box == "warning":
        border_color = "B45309"  # Orange
        bg_color = "FFFBEB"      # Ambre très doux
        accent_color = RGBColor(0xB4, 0x53, 0x09)
    else:
        border_color = "2D5F4F"  # Vert profond (MA2E)
        bg_color = "E8F2EE"      # Vert doux
        accent_color = ACCENT_DEEP
        
    set_cell_background(cell, bg_color)
    # 24 = 3pt de bordure gauche
    set_cell_borders(cell, 
                     left=(24, "single", border_color),
                     top=None, right=None, bottom=None)
    set_cell_margins(cell, top=140, bottom=140, left=200, right=180)
    
    # Texte de l'encadré
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(4)
    run_title = p.add_run(f"⚡ {title}\n" if type_box == "warning" else f"ℹ️ {title}\n")
    set_run(run_title, size=10.5, bold=True, color=accent_color)
    
    run_text = p.add_run(text)
    set_run(run_text, size=10, italic=True, color=INK_700)
    # Ajouter un paragraphe vide après l'encadré pour aérer
    doc.add_paragraph().paragraph_format.space_before = Pt(4)

def TABLE_DESIGN(doc, headers, col_widths, rows):
    """Génère un tableau élégant et aéré avec zébrure des lignes."""
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    table.autofit = False
    
    # Remplir le Header
    for idx, (h, w) in enumerate(zip(headers, col_widths)):
        cell = table.rows[0].cells[idx]
        cell.width = Cm(w)
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        set_cell_background(cell, ACCENT_HEX)
        set_cell_margins(cell, top=140, bottom=140, left=150, right=150)
        set_cell_borders(cell, 
                         bottom=(12, "single", INK_200),
                         top=None, left=None, right=None)
        
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        run = p.add_run(h)
        set_run(run, size=10, bold=True, color=COLOR_WHITE)
        
    # Remplir les données
    for r_idx, r_data in enumerate(rows):
        row = table.rows[r_idx + 1]
        bg_row = INK_50 if r_idx % 2 == 0 else WHITE  # zébrure alternée
        for c_idx, val in enumerate(r_data):
            cell = row.cells[c_idx]
            cell.width = Cm(col_widths[c_idx])
            cell.vertical_alignment = WD_ALIGN_VERTICAL.TOP
            set_cell_background(cell, bg_row)
            set_cell_margins(cell, top=120, bottom=120, left=150, right=150)
            
            # Ligne de séparation fine entre lignes
            border_bottom = (4, "single", INK_200) if r_idx < len(rows) - 1 else (12, "single", ACCENT_HEX)
            set_cell_borders(cell, 
                             bottom=border_bottom,
                             top=None, left=None, right=None)
            
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.line_spacing = 1.15
            run = p.add_run(str(val))
            
            # Styliser le premier élément de ligne s'il est en gras
            bold_col = (c_idx == 0) and (len(headers) == 2 or headers[0] == "Vous voulez…")
            set_run(run, size=9.5, bold=bold_col, color=INK_900 if bold_col else INK_700)
            
    doc.add_paragraph().paragraph_format.space_before = Pt(8)
    return table

def build_cover_page(doc):
    """Construit une page de garde moderne."""
    p_space = doc.add_paragraph()
    p_space.paragraph_format.space_before = Pt(40)
    
    # Slogan / Sous-titre
    p_header = doc.add_paragraph()
    r_hdr = p_header.add_run("MUTUELLE DES AGENTS DE L'EAU ET DE L'ÉLECTRICITÉ  ·  GROUPE ERANOVE")
    set_run(r_hdr, size=9.5, bold=True, color=ACCENT_MUTED)
    
    # Grand Titre
    p_title = doc.add_paragraph()
    p_title.paragraph_format.space_before = Pt(20)
    p_title.paragraph_format.space_after = Pt(4)
    r_title = p_title.add_run("PLATEFORME DIGITALE\nD'IDENTIFICATION")
    set_run(r_title, size=36, bold=True, color=INK_900)
    
    p_subtitle = doc.add_paragraph()
    p_subtitle.paragraph_format.space_after = Pt(40)
    r_sub = p_subtitle.add_run("Manuel de l'utilisateur Général : Administration, Reporting & Intégrations")
    set_run(r_sub, size=14, italic=True, color=INK_500)
    
    # Tableau d'infos (cartes d'infos sans grille noire)
    info_table = doc.add_table(rows=6, cols=2)
    info_table.alignment = WD_TABLE_ALIGNMENT.LEFT
    info_table.autofit = False
    
    metadata = [
        ("Référence", "MA2E_Manuel_Utilisateur_v1.2.docx"),
        ("Version", "1.2 (Alignement plateforme POC déployée)"),
        ("Date", date.today().strftime("%d/%m/%Y")),
        ("Auteur", "Direction Digitalisation & Innovation (DDI)"),
        ("Destinataires", "Administrateurs, Gestionnaires & DPO MA2E"),
        ("Statut", "Document validé en Comité de Pilotage")
    ]
    
    for idx, (lbl, val) in enumerate(metadata):
        r = info_table.rows[idx]
        c1, c2 = r.cells[0], r.cells[1]
        c1.width = Cm(4.5)
        c2.width = Cm(12.1)
        
        set_cell_background(c1, INK_100)
        set_cell_background(c2, INK_50)
        set_cell_margins(c1, top=80, bottom=80, left=120, right=120)
        set_cell_margins(c2, top=80, bottom=80, left=120, right=120)
        set_cell_borders(c1, bottom=(4, "single", WHITE), top=None, left=None, right=None)
        set_cell_borders(c2, bottom=(4, "single", WHITE), top=None, left=None, right=None)
        
        p1 = c1.paragraphs[0]
        run_lbl = p1.add_run(lbl)
        set_run(run_lbl, size=9.5, bold=True, color=INK_900)
        
        p2 = c2.paragraphs[0]
        run_val = p2.add_run(val)
        set_run(run_val, size=9.5, color=INK_700)
        
    doc.add_paragraph().paragraph_format.space_before = Pt(50)
    
    p_ft = doc.add_paragraph()
    p_ft.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_ft = p_ft.add_run("© Copyright 2026 GS2E / MA2E. Diffusion interdite aux tiers.")
    set_run(r_ft, size=9, italic=True, color=INK_500)
    
    doc.add_page_break()

def generate_manual(output_path: Path):
    doc = Document()
    set_doc_defaults(doc)
    
    # 1. Page de garde
    build_cover_page(doc)
    
    #  Sommaire détaillé
    H(doc, "Sommaire Général", level=1)
    TOC_ITEMS = [
        "Partie A : Guide de l'Expérience Sociétaire",
        "   1. Introduction et Prérequis d'Identification",
        "   2. Accès via Scan QR Code en Agence",
        "   3. Éléments du Parcours Conversationnel WhatsApp (Inscription, Suivi, MAJ, FAQ)",
        "   4. Le Portail Web et la Synchronisation des Sessions",
        "   5. Relances, Notifications WhatsApp et Suivis par Email",
        "Partie B : Guide de l'Instructeur (Espace de Validation)",
        "   6. Connexion, MFA, Politique de Verrouillage de Session",
        "   7. Module de Rapprochement OCR & Traitement des Doublons",
        "   8. Instructions Décisionnelles : Validation, Refus Motivé, Complément",
        "Partie C : Portail de Configuration & Administration Globale",
        "   9. Administration des Comptes Utilisateurs et Profils RBAC Dynamiques",
        "  10. Administration Référentiels : Employeurs & Import de Collaborateurs en masse",
        "  11. Configuration de l'Assistante IA (Personnalité, Voix, Ton et Langue)",
        "  12. Ingestion Documentaire & Gestion du RAG (Base de connaissances)",
        "  13. Intégrations System (OCR Azure, Webhook Compta, SMTP)",
        "  14. Reporting Global, Statistiques et KPIs Opérationnels",
        "  15. Conformité ARTCI/RGPD et Audit Log Cryptographique",
        "Partie D : FAQ & Ressources Support",
        "  16. Foire Aux Questions (FAQ)",
        "  17. Contacts, escalades et support technique"
    ]
    for item in TOC_ITEMS:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(2.5)
        indent = Cm(0.8) if item.startswith(" ") else Cm(0)
        p.paragraph_format.left_indent = indent
        p.paragraph_format.keep_with_next = True
        run = p.add_run(item)
        set_run(run, size=10.5, bold=not item.startswith(" "))
        
    doc.add_page_break()
    
    # ==========================================
    # PARTIE A : GUIDE SOCIÉTAIRE
    # ==========================================
    H(doc, "Partie A : Guide de l'Expérience Sociétaire", level=1)
    P(doc, "Ce guide décrit le parcours d'identification mis en place pour les collaborateurs de la CIE, SODECI et ERANOVE, leur permettant de s'affilier numériquement à la mutuelle MA2E.")
    
    H(doc, "1. Introduction et Prérequis d'Identification", level=2)
    P(doc, "Le processus est conçu pour durer en moyenne moins de 5 minutes. Avant de démarrer, l'adhérent doit regrouper :")
    BUL(doc, "Son titre d'identité valide (CNI Ivoirienne, ou Passeport, Carte Consulaire).")
    BUL(doc, "Son matricule professionnel de salarié (qui figure sur son bulletin de salaire).")
    BUL(doc, "Un smartphone équipé de l'application WhatsApp ou muni d'un navigateur internet standard.")
    
    H(doc, "2. Accès via Scan QR Code en Agence", level=2)
    P(doc, "Dans toutes les agences MA2E et CIE/SODECI, des affiches comportent des QR Codes sécurisés d'identification.")
    NUM(doc, "Scannez le QR Code en agence à l'aide de l'appareil photo de votre smartphone.")
    NUM(doc, "Le scan vous redirige instantanément vers l'URL sécurisée https://ma2e.swedencentral.cloudapp.azure.com, qui propose de démarrer sur WhatsApp ou directement sur le Portail Web.")
    NUM(doc, "Phase 2 (à venir) : détection automatique du point de contact physique d'origine (agence émettrice) pour des statistiques d'enrôlement par agence.")

    H(doc, "3. Éléments du Parcours Conversationnel WhatsApp", level=2)
    P(doc, "En envoyant « Bonjour » au numéro WhatsApp POC MA2E (numéro communiqué par la DSI GS2E lors du déploiement pilote), l'employé lance le bot d'identification. Quatre flux principaux sont disponibles :")
    
    P(doc, "3.1 Flux d'Inscription :", bold=True)
    P(doc, "Permet d'initialiser son dossier d'enrôlement : recueil de la notice légale ARTCI, saisie du matricule, téléversement de la CNI (recto puis verso) et complétion des données de situation familiale (ayants droit) et professionnelles.")
    
    P(doc, "3.2 Flux de Consultation :", bold=True)
    P(doc, "En tapant 'Statut' ou 'Où en est mon dossier ?', le sociétaire reçoit le statut en temps réel de sa demande d'affiliation avec le motif précis si celle-ci nécessite un complément.")
    
    P(doc, "3.3 Flux de Mise à Jour (MAJ) :", bold=True)
    P(doc, "Le sociétaire peut modifier des données déclaratives déjà validées en transmettant des pièces modificatives (par exemple : un nouveau RIB bancaire, ou un acte de mariage pour les ayants droit).")
    
    P(doc, "3.4 Flux FAQ libre :", bold=True)
    P(doc, "Hors du parcours d'enrôlement, l'assistante répond en langage libre à tout moment sur les règles de la mutuelle, les taux de cotisations ou les agences physiques.")

    H(doc, "4. Le Portail Web et la Synchronisation des Sessions", level=2)
    P(doc, "Pour les utilisateurs préférant un grand écran, le portail https://ma2e.swedencentral.cloudapp.azure.com reproduit à l'identique les étapes du chatbot. Le backend synchronise l'enrôlement :")
    BUL(doc, "Persistance de session : Une session initiée sur le web peut être reprise sur son téléphone pour la prise de photo de la CNI par simple scan du QR Code de session généré en direct à l'écran.")
    BUL(doc, "Durée de sauvegarde : La progression est conservée 30 jours vous permettant de finaliser plus tard si un document vous manque.")

    H(doc, "5. Relances, Notifications WhatsApp et Suivis par Email", level=2)
    P(doc, "Pour éviter l'abandon du parcours, des règles de relance automatique relancent l'utilisateur :")
    BUL(doc, "Notifications WhatsApp : Notification immédiate si l'agent valide, rejette ou demande un complément de photo.")
    BUL(doc, "Emails de suivi : En cas d'inactivité de plus de 48h, un email formel de relance est envoyé à l'adresse professionnelle du collaborateur reprenant les éléments manquants à fournir.")

    doc.add_page_break()

    # ==========================================
    # PARTIE B : GUIDE DE L'INSTRUCTEUR
    # ==========================================
    H(doc, "Partie B : Guide de l'Instructeur (Espace de Validation)", level=1)
    P(doc, "Cette partie concerne les agents administratifs MA2E en charge de l'examen et du traitement manuel des dossiers.")
    
    H(doc, "6. Connexion, MFA, Politique de Verrouillage de Session", level=2)
    P(doc, "L'accès aux fonctions de back-office (agents, administrateurs, DPO) s'effectue via https://ma2e.swedencentral.cloudapp.azure.com — même URL que le portail sociétaire, l'accès étant filtré à la connexion selon le rôle. La sécurité d'accès respecte des exigences règlementaires :")
    BUL(doc, "MFA obligatoire : Obligation pour les gestionnaires et admins d'activer un token MFA Google/Microsoft Authenticator.")
    BUL(doc, "Verrouillage automatique : Après 5 tentatives infructueuses, le compte est bloqué 15 minutes. Session déconnectée automatiquement après 20 minutes d'inactivité.")

    H(doc, "7. Module de Rapprochement OCR & Traitement des Doublons", level=2)
    P(doc, "Dans la fiche descriptive du dossier, un panneau dynamique permet le contrôle de validité :")
    BUL(doc, "Zone OCR en face-à-face : Affichage côte à côte des informations extraites par l'OCR Azure AI Vision et des données saisies/corrigées par l'utilisateur. Le gestionnaire valide les écarts.")
    BUL(doc, "Vérification des Doublons : La plateforme examine automatiquement la base de données pour détecter si le numéro de CNI ou la combinaison matricule existe déjà dans un autre dossier de sociétaire.")

    H(doc, "8. Instructions Décisionnelles : Validation, Refus Motivé, Complément", level=2)
    P(doc, "Trois issues formelles sont possibles pour chaque dossier instruit :")
    TABLE_DESIGN(doc,
                 headers=["Action", "Effet technique", "Canal de retour pour l'utilisateur"],
                 col_widths=[4.5, 7.5, 4.6],
                 rows=[
                     ["Validation", "Dossier archivé, appel du Webhook comptable/paie pour prélèvement, ouverture des droits.", "WhatsApp immédiat + Email officiel de confirmation."],
                     ["Demande de Complément", "Dossier suspendu. Le bot sollicite le document précis désigné par l'agent (ex: CNI floue).", "WhatsApp conversationnel ciblé avec upload réactivé."],
                     ["Refus définitif", "Le dossier est rejeté. L'agent doit obligatoirement saisir un motif légal ou fonctionnel.", "Email de rejet comprenant le motif exact saisi par l'agent."]
                 ])

    doc.add_page_break()

    # ==========================================
    # PARTIE C : ADMINISTRATION ET CONFIGURATION GLOBALE
    # ==========================================
    H(doc, "Partie C : Portail de Configuration & Administration Globale", level=1)
    P(doc, "Cette section s'adresse aux profils d'administration (tenant_admin et super_admin) en charge du paramétrage de l'instance MA2E.")
    
    H(doc, "9. Administration des Comptes Utilisateurs et Profils RBAC Dynamiques", level=2)
    P(doc, "La gestion des accès internes s'appuie sur un système RBAC dynamique de contrôle d'accès :")
    BUL(doc, "Rôle Gestionnaire (Agent) : Traiter et instruire les demandes d'enrôlement. Pas d'accès aux configurations.")
    BUL(doc, "Rôle Administrateur (Tenant Admin) : Gestion des agents, paramétrage des modèles, IA, RAG et contrôles de purge.")
    BUL(doc, "Rôle Délégué à la Protection des Données (DPO) : Extraction de dossiers pour droits d'accès, validation des purges de données.")
    BUL(doc, "Rôle Viewer (Consultation) : Accès en lecture seule à tous les modules (dossiers, reporting, audit) — aucun droit d'écriture, de validation ou d'export sensible. Utile pour la direction, l'audit interne ou les stagiaires.")
    BUL(doc, "Rôle Super-Admin (GS2E) : Compte break-glass réservé à la DSI GS2E pour les opérations exceptionnelles (rotation des clés d'accès, réinitialisation MFA de dernier recours, incidents critiques).")

    H(doc, "10. Administration Référentiels : Employeurs & Import de Collaborateurs en masse", level=2)
    P(doc, "Le back-office permet de configurer les variables employeurs et d'ingérer l'annuaire de contrôle de sécurité :")
    
    P(doc, "10.1 Sociétés du Périmètre :", bold=True)
    P(doc, "Configuration des informations de base des 4 filiales du groupe GS2E (CIE, SODECI, SMB, AD ERANOVE) avec leurs préfixes de formulaires et variables de prélèvement correspondantes.")
    
    P(doc, "10.2 Import en masse de Collaborateurs :", bold=True)
    P(doc, "Pour éviter que des utilisateurs s'inscrivent avec de faux matricules, la plateforme dispose d'un outil d'importation dans 'Paramètres -> Imports' :")
    NUM(doc, "Téléchargez le modèle de fichier CSV ou Excel atomique normalisé.")
    NUM(doc, "Renseignez la liste des collaborateurs (Matricule, Nom, Prénoms, Date de Naissance, Email pro, Date d'embauche).")
    NUM(doc, "Téléversez le fichier dans l'outil d'importation.")
    NUM(doc, "Lancez l'étape de pré-vérification (Dry-Run) : Le système vérifie l'absence de doublons internes ou de lignes corrompues avant d'enregistrer.")
    
    CALLOUT(doc, "Structure stricte du fichier d'importation",
            "Le fichier d'importation doit comporter les en-têtes exacts : 'matricule', 'nom', 'prenoms', 'date_naissance' (format DD/MM/YYYY), 'email' et 'employeur'. Les matricules orphelins ou mal formatés seront rejetés au Dry-Run.",
            type_box="warning")

    H(doc, "11. Configuration de l'Assistante IA (Personnalité, Voix, Ton et Langue)", level=2)
    P(doc, "Le menu 'Paramètres -> Intelligence artificielle' permet de modifier le comportement conversationnel du bot :")
    BUL(doc, "Personnalité et Persona : Champ texte global définissant les rôles du bot (ex: 'Vous êtes l'assistante virtuelle de la mutuelle MA2E. Soyez courtoise...')")
    BUL(doc, "Voix et Ton : Ajustement de la température du modèle (paramètre technique réservé à l'IT — 0.0 pour un ton purement factuel, jusqu'à 0.8 pour un ton chaleureux et humain). Valeur recommandée en production : 0.3.")
    BUL(doc, "Langue : Gestion bilingue dynamique. Le bot passe automatiquement en Français ou en Anglais selon les préférences sélectionnées lors du premier échange.")

    H(doc, "12. Ingestion Documentaire & Gestion du RAG (Base de connaissances)", level=2)
    P(doc, "Pour répondre de manière fiable, le moteur utilise la technique de RAG (Génération Augmentée par Récupération) :")
    BUL(doc, "Fichiers Indexés : Possibilité dans le back-office d'enrôler des fichiers PDF, Word ou Excel de règlements intérieurs.")
    BUL(doc, "Scraping de FAQ : Renseignez les URLs de la foire aux questions officielle de la MA2E. Le bot parcourt les pages, découpe le contenu en fragments vectorisés, puis les stocke dans la BDD (pgvector).")

    H(doc, "13. Intégrations System (OCR, Webhook Compta, SMTP)", level=2)
    P(doc, "La plateforme configure ses connexions avec les infrastructures externes :")
    BUL(doc, "OCR Azure Vision (production) : paramétrage des endpoints cognitifs Microsoft pour l'extraction identitaire.")
    BUL(doc, "OCR.space (solution de secours) : bascule automatique en cas d'indisponibilité d'Azure. Configurable depuis l'admin sans redéploiement.")
    BUL(doc, "OTP : configuration de l'envoi de codes de sécurité par e-mail pro (SMTP) ou par messagerie instantanée d'authentification.")
    BUL(doc, "Webhook comptabilité : envoi d'une requête POST chiffrée avec signature HMAC SHA-256 au logiciel de paie MA2E/ERANOVE à chaque validation de dossier.")

    H(doc, "14. Reporting Global, Statistiques et KPIs Opérationnels", level=2)
    P(doc, "Le tableau de bord de supervision contient les indicateurs opérationnels en temps réel :")
    TABLE_DESIGN(doc,
                 headers=["Indicateur", "Définition / Méthode", "Cible opérationnelle"],
                 col_widths=[5.5, 7.5, 3.6],
                 rows=[
                     ["Temps moyen d'instruction", "Délai écoulé entre la soumission d'un dossier et la décision finale.", "Moins de 24h ouvrées"],
                     ["Taux de validation directe", "Pourcentage de dossiers validés sans demande de complément ou modifications.", "Supérieur à 80%"],
                     ["Score OCR moyen", "Moyenne de confiance de la retranscription optique de la CNI.", "Supérieur à 85%"],
                     ["Taux d'auto-complétion", "Ratio des demandes arrivées au bout du parcours conversationnel.", "Supérieur à 70%"]
                 ])

    H(doc, "15. Conformité ARTCI/RGPD et Audit Log Cryptographique", level=2)
    P(doc, "Le module de conformité permet au DPO de veiller au respect de la réglementation en Côte d'Ivoire (Loi 2013-450) :")
    BUL(doc, "Sécurité des Mots de Passe & MFA : Politique stricte imposant 12 caractères min, majuscule, chiffre et symbole.")
    BUL(doc, "Politique de Rétention : Archivage automatique et anonymisation complète 5 ans après la cessation du contrat mutuelle.")
    BUL(doc, "Audit Log Append-Only : Enregistrement de chaque action sensible. L'empreinte cryptographique chaînée empêche toute altération ou suppression des journaux de connexions ou de validations.")

    doc.add_page_break()

    # ==========================================
    # PARTIE D : FAQ & RESSOURCES SUPPORT
    # ==========================================
    H(doc, "Partie D : FAQ & Ressources Support", level=1)
    
    H(doc, "16. Foire Aux Questions (FAQ)", level=2)
    P(doc, "Questions Fréquentes pour les Administrateurs et les Sociétaires :")
    
    TABLE_DESIGN(doc,
                 headers=["Question récurrente", "Solution préconisée"],
                 col_widths=[6.0, 10.6],
                 rows=[
                     ["Le matricule du collaborateur n'est pas reconnu lors de l'inscription.", 
                      "Vérifiez si l'utilisateur figure dans la base de données Collaborateurs. Si ce n'est pas le cas, l'administrateur doit procéder à un import CSV correctif du collaborateur."],
                     ["L'agent a perdu l'appareil contenant son authentificateur MFA.",
                      "Un Administrateur (Tenant Admin) doit réinitialiser le token MFA de l'utilisateur depuis « Paramètres → Utilisateurs → Réinitialiser MFA ». L'agent pourra ensuite réassocier un nouvel authentificateur. En dernier recours, la DSI GS2E peut intervenir via le compte break-glass Super-Admin."],
                     ["Où sont stockées les photos de CNI des adhérents ?", 
                      "Les photos de CNI sont hébergées de manière sécurisée et chiffrée avec AES-256 dans un stockage Azure Blob Container. Aucun accès direct hors-plateforme n'est configuré."]
                 ])

    H(doc, "17. Contacts, escalades et support technique", level=2)
    P(doc, "En cas de dysfonctionnement technique bloquant de la plateforme, suivre l'un des canaux d'escalade suivants selon la nature de l'incident. Les coordonnées définitives (adresses email et numéros de téléphone) seront communiquées par la DSI GS2E lors de la mise en production.")

    TABLE_DESIGN(doc,
                 headers=["Canal d'escalade", "Périmètre", "Délai de réponse cible"],
                 col_widths=[6.0, 6.0, 4.6],
                 rows=[
                     ["Support Technique MA2E", "Incidents fonctionnels côté back-office (validation, exports, reporting).", "Moins de 4 heures ouvrées"],
                     ["Délégué à la Protection des Données (DPO)", "Demandes ARTCI : droit d'accès, rectification, oubli, incidents de sécurité.", "Sous 30 jours (délai réglementaire ARTCI)"],
                     ["Support Éditeur (DSI GS2E)", "Incidents plateforme (backend, base de données, intégrations Azure, WhatsApp).", "Selon convention SLA niveau 3"]
                 ])

    P(doc, "Note : les coordonnées précises de chaque canal (adresses email dédiées, numéros de téléphone, portail de tickets) seront ajoutées à ce manuel dès leur validation par la Direction Digitalisation & Innovation.")

    # Enregistrer le document
    doc.save(output_path)
    print(f"Fichier créé avec succès : {output_path}")

if __name__ == "__main__":
    out_file = Path(__file__).parent / "MA2E_Manuel_Utilisateur_v1.2.docx"
    generate_manual(out_file)
