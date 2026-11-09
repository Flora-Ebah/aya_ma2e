"""Genere MA2E_CVATL_v1.pptx
Strategie : on part du modele GS2E SODECI et on remplace le texte + on insere
nos schemas MA2E N&B + on nettoie les fonds colores des tableaux.
"""
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

HERE = Path(__file__).parent
TEMPLATE = Path(r"C:/Users/LENOVO/Downloads/GS2E-ES_CRC-CVATL_2026_V1_1.pptx")
OUT = HERE / "MA2E_CVATL_v1.pptx"


# =================================================================== #
# Helpers
# =================================================================== #
def set_text_keep_format(tf, new_text):
    """Remplace tout le texte d'un text frame en preservant le formatage
    de son premier run. Gere les multi-lignes via les paragraphes.
    """
    lines = new_text.split("\n")
    template_run = None
    template_para = None
    for para in tf.paragraphs:
        if para.runs:
            template_run = para.runs[0]
            template_para = para
            break

    if template_run is None:
        tf.text = new_text
        return

    font = template_run.font
    style = {
        "name": font.name,
        "size": font.size,
        "bold": font.bold,
        "italic": font.italic,
        "underline": font.underline,
    }
    try:
        style["color"] = font.color.rgb
    except Exception:
        style["color"] = None

    para_align = template_para.alignment

    txBody = tf._txBody
    for p in list(txBody.findall(qn("a:p"))):
        txBody.remove(p)

    for line_idx, line in enumerate(lines):
        p = txBody.makeelement(qn("a:p"), {})
        txBody.append(p)
        if para_align is not None:
            pPr = p.makeelement(qn("a:pPr"), {})
            p.insert(0, pPr)
            algn_map = {1: "l", 2: "ctr", 3: "r", 4: "just"}
            try:
                pPr.set("algn", algn_map.get(int(para_align), "l"))
            except Exception:
                pass
        r = p.makeelement(qn("a:r"), {})
        p.append(r)
        rPr = r.makeelement(qn("a:rPr"), {"lang": "fr-FR"})
        r.append(rPr)
        if style["bold"]:
            rPr.set("b", "1")
        if style["italic"]:
            rPr.set("i", "1")
        if style["size"]:
            rPr.set("sz", str(int(style["size"].pt * 100)))
        if style["name"]:
            latin = rPr.makeelement(qn("a:latin"), {"typeface": style["name"]})
            rPr.append(latin)
        if style["color"]:
            fill = rPr.makeelement(qn("a:solidFill"), {})
            rPr.append(fill)
            clr = fill.makeelement(qn("a:srgbClr"), {"val": str(style["color"])})
            fill.append(clr)
        t = r.makeelement(qn("a:t"), {})
        r.append(t)
        t.text = line


def replace_in_shape(slide, shape_index, new_text):
    shape = list(slide.shapes)[shape_index]
    if shape.has_text_frame:
        set_text_keep_format(shape.text_frame, new_text)


def remove_shape_by_index(slide, idx):
    shape = list(slide.shapes)[idx]
    sp = shape._element
    sp.getparent().remove(sp)


def replace_first_picture_by_image(slide, image_path):
    """Trouve la premiere image (shape_type=13) et la remplace par image_path
    a la meme position/taille.
    """
    for shape in list(slide.shapes):
        if shape.shape_type == 13:
            left, top = shape.left, shape.top
            width, height = shape.width, shape.height
            sp = shape._element
            sp.getparent().remove(sp)
            slide.shapes.add_picture(
                str(image_path), left, top, width, height,
            )
            return True
    return False


def add_centered_picture(slide, image_path, top_in=2.5, width_in=18, height_in=10):
    """Ajoute une image centree horizontalement a une position donnee."""
    slide_width = slide.part.package.presentation_part.presentation.slide_width
    img_width_emu = Inches(width_in)
    left_emu = (slide_width - img_width_emu) // 2
    slide.shapes.add_picture(
        str(image_path),
        left_emu, Inches(top_in),
        Inches(width_in), Inches(height_in),
    )


def strip_table_cell_fill(table):
    """Met toutes les cellules du tableau en fond transparent (pas de couleur)."""
    for row in table.rows:
        for cell in row.cells:
            tcPr = cell._tc.get_or_add_tcPr()
            # Supprime tout fill existant
            for tag in ["a:solidFill", "a:gradFill", "a:pattFill", "a:blipFill"]:
                for el in tcPr.findall(qn(tag)):
                    tcPr.remove(el)
            # Ajoute noFill
            noFill = tcPr.makeelement(qn("a:noFill"), {})
            tcPr.append(noFill)


def force_table_text_black(table):
    """Force tout le texte du tableau en noir."""
    for row in table.rows:
        for cell in row.cells:
            for para in cell.text_frame.paragraphs:
                for run in para.runs:
                    run.font.color.rgb = RGBColor(0, 0, 0)


# =================================================================== #
# Ouverture du template
# =================================================================== #
print(f"Lecture template : {TEMPLATE}")
prs = Presentation(str(TEMPLATE))
slides = list(prs.slides)
slide_w_in = prs.slide_width / 914400
slide_h_in = prs.slide_height / 914400
print(f"Slides : {len(slides)} ({slide_w_in:.1f} x {slide_h_in:.1f} pouces)")

# =================================================================== #
# SLIDE 1 - Page de garde
# =================================================================== #
replace_in_shape(slides[0], 6, "JUIN 2026")
replace_in_shape(slides[0], 8,
    "CVATL :\nPLATEFORME MA2E - IDENTIFICATION DIGITALE DES SOCIETAIRES")

# =================================================================== #
# SLIDE 2 - Equipe projet
# =================================================================== #
replace_in_shape(slides[1], 0, "Juin 2026")
replace_in_shape(slides[1], 5,
    "PLATEFORME MA2E - IDENTIFICATION DIGITALE DES SOCIETAIRES")
replace_in_shape(slides[1], 8,
    "A. Siriki OUATTARA : Architecte / Developpeur Lead - GS2E\n"
    "[A completer] : Chef de Projet MA2E\n"
    "[A completer] : Sponsor metier MA2E\n"
    "[A completer] : Representant DSI ERANOVE\n"
    "[A completer] : Representant DPO MA2E\n"
    "[A completer] : Representant securite GS2E")

# =================================================================== #
# SLIDE 4 - Contexte, Enjeux, Objectifs
# =================================================================== #
contexte_ma2e = (
    "Contexte, Enjeux, Objectifs\n"
    "La Mutuelle des Agents de l'Eau et de l'Electricite (MA2E) regroupe les "
    "agents actifs et retraites des societes du groupe ERANOVE (CIE, SODECI, "
    "SMB, etc.).\n"
    "L'identification des nouveaux societaires reposait sur un formulaire papier "
    "traite en agence puis remonte mensuellement. Ce circuit prenait en moyenne "
    "35 minutes par dossier et un dossier sur trois revenait incomplet.\n"
    "Pour fluidifier ce processus, MA2E a engage la mise en place d'une "
    "plateforme digitale permettant a chaque societaire de s'identifier depuis "
    "son telephone via WhatsApp ou un navigateur web, guide par une assistante "
    "virtuelle nommee AYA.\n"
    "Les principaux objectifs vises a travers la mise en place du systeme sont :\n"
    "Reduire le delai d'enrolement de 35 minutes a moins de 10 minutes,\n"
    "Atteindre 95 % de completude des dossiers en premiere soumission,\n"
    "Diviser par trois le cout administratif unitaire d'un dossier,\n"
    "Garantir la conformite avec la loi 2013-450 sur la protection des donnees personnelles,\n"
    "Tracer toutes les operations sur un journal d'audit non modifiable."
)
replace_in_shape(slides[3], 1, contexte_ma2e)

# =================================================================== #
# SLIDE 5 - Type de projet / Equipe / Prestataire
# Correction : Equipe Projet = MA2E (client) et Prestataire = GS2E
# =================================================================== #
replace_in_shape(slides[4], 5, "MA2E (DSI ERANOVE + DPO)")
replace_in_shape(slides[4], 6, "GS2E")

# =================================================================== #
# SLIDE 6 - Etape projet / macro planning : insertion du diagramme planning
# =================================================================== #
slide6 = slides[5]
# Remplace le placeholder "A METTRE A JOUR CP/METIER" par titre du planning
replace_in_shape(slide6, 2, "Macro planning - 7 phases sur Mars 2026 - Fevrier 2027")
# Insere notre schema planning
add_centered_picture(slide6, HERE / "diagram_planning.png",
                     top_in=3.2, width_in=22, height_in=10)

# =================================================================== #
# SLIDE 7 - Architecture fonctionnelle : insertion archi_macro
# =================================================================== #
slide7 = slides[6]
replace_first_picture_by_image(slide7, HERE / "diagram_archi_macro.png")

# =================================================================== #
# SLIDE 8 - Evaluation PRI : insertion matrice PRI
# =================================================================== #
slide8 = slides[7]
replace_in_shape(slide8, 2, "Matrice probabilite x impact - 5 risques identifies")
# Note : la slide 8 a deja une image placeholder en shape index 1
# On la remplace
if not replace_first_picture_by_image(slide8, HERE / "diagram_pri.png"):
    add_centered_picture(slide8, HERE / "diagram_pri.png",
                         top_in=2.0, width_in=22, height_in=11)

# =================================================================== #
# SLIDE 9 - Top 3 workflows : flux_onboarding
# =================================================================== #
slide9 = slides[8]
replace_first_picture_by_image(slide9, HERE / "diagram_flux_onboarding.png")

# =================================================================== #
# SLIDE 10 - Top 5 entites metier
# =================================================================== #
slide10 = slides[9]
if not replace_first_picture_by_image(slide10, HERE / "diagram_entites_metier.png"):
    add_centered_picture(slide10, HERE / "diagram_entites_metier.png",
                         top_in=2.0, width_in=22, height_in=11)

# =================================================================== #
# SLIDE 11 - Architecture logicielle 1/2 : couches
# =================================================================== #
slide11 = slides[10]
if not replace_first_picture_by_image(slide11, HERE / "diagram_archi_log_1.png"):
    add_centered_picture(slide11, HERE / "diagram_archi_log_1.png",
                         top_in=2.0, width_in=22, height_in=11)

# =================================================================== #
# SLIDE 12 - Architecture logicielle 2/2 : modules
# =================================================================== #
slide12 = slides[11]
if not replace_first_picture_by_image(slide12, HERE / "diagram_archi_log_2.png"):
    add_centered_picture(slide12, HERE / "diagram_archi_log_2.png",
                         top_in=2.0, width_in=22, height_in=11)

# =================================================================== #
# SLIDE 13 - Architecture logicielle 3 : integrations externes
# =================================================================== #
slide13 = slides[12]
if not replace_first_picture_by_image(slide13, HERE / "diagram_archi_log_3.png"):
    add_centered_picture(slide13, HERE / "diagram_archi_log_3.png",
                         top_in=2.0, width_in=22, height_in=11)

# =================================================================== #
# SLIDE 14 - Architecture technique 1/2 : topologie
# =================================================================== #
slide14 = slides[13]
replace_first_picture_by_image(slide14, HERE / "diagram_topologie.png")

# =================================================================== #
# SLIDE 15 - Architecture technique 2/2 : CI/CD
# =================================================================== #
slide15 = slides[14]
replace_first_picture_by_image(slide15, HERE / "diagram_cicd.png")

# =================================================================== #
# SLIDE 16 - Tableau RAM/CPU - nettoyer fonds + texte noir
# =================================================================== #
table_data = [
    ["Couche", "Utilisateurs simultanes", "RAM", "CPU", "Disque", "OS"],
    ["Site web MA2E (sociétaire + back-office)", "100", "4 Go", "2 vCPU", "50 Go", "Ubuntu 24.04 LTS"],
    ["Application serveur MA2E", "200", "8 Go", "4 vCPU", "100 Go", "Ubuntu 24.04 LTS"],
    ["Base de donnees PostgreSQL", "N/A", "8 Go", "4 vCPU", "100 Go", "Ubuntu 24.04 LTS"],
    ["Service de notifications", "N/A", "2 Go", "1 vCPU", "30 Go", "Ubuntu 24.04 LTS"],
]
slide16 = slides[15]
for shape in slide16.shapes:
    if shape.has_table:
        tbl = shape.table
        for r, row_data in enumerate(table_data):
            for c, val in enumerate(row_data):
                if r < len(tbl.rows) and c < len(tbl.columns):
                    set_text_keep_format(tbl.cell(r, c).text_frame, val)
        strip_table_cell_fill(tbl)
        force_table_text_black(tbl)
        break

# =================================================================== #
# SLIDE 17 - Matrice des flux
# =================================================================== #
flux_data = [
    ["Source", "Destination", "Protocole / Port", "Description"],
    ["Sociétaire (navigateur ou WhatsApp)",
     "Passerelle d'entrée Azure (ma2e.gs2e.ci)",
     "TCP / 443 (HTTPS)",
     "Accès du sociétaire à l'application web et à l'API conversationnelle MA2E"],
    ["Application serveur MA2E",
     "Base de données PostgreSQL",
     "TCP / 5432",
     "Lecture / écriture des dossiers, conversations et journal d'audit"],
    ["Administrateur GS2E",
     "Serveurs applicatifs, base de données, coffre-fort",
     "TCP / 22 (SSH) via VPN groupe",
     "Administration système, déploiements, supervision via le bastion ERANOVE"],
]
slide17 = slides[16]
for shape in slide17.shapes:
    if shape.has_table:
        tbl = shape.table
        for r, row_data in enumerate(flux_data):
            for c, val in enumerate(row_data):
                if r < len(tbl.rows) and c < len(tbl.columns):
                    set_text_keep_format(tbl.cell(r, c).text_frame, val)
        strip_table_cell_fill(tbl)
        force_table_text_black(tbl)
        break

# =================================================================== #
# SLIDE 18 - Mode de deploiement : insertion schema deploiement
# Note : la slide a deja des icones et du texte. On supprime les pictures
# decoratives et on insere notre schema.
# =================================================================== #
slide18 = slides[17]
# Supprime toutes les pictures decoratives de la slide
pics_to_remove = []
for i, shape in enumerate(slide18.shapes):
    if shape.shape_type == 13:  # PICTURE
        pics_to_remove.append(shape)
for shape in pics_to_remove:
    sp = shape._element
    sp.getparent().remove(sp)
# Egalement supprimer les text boxes "Data Center GS2E", "Cloud (Azure...)", "Docker"
# car notre schema les contient deja
boxes_to_remove = []
for shape in slide18.shapes:
    if shape.has_text_frame:
        txt = shape.text_frame.text.strip()
        if txt in ("Data Center GS2E", "CLOUD ( Azure et autres)", "Docker"):
            boxes_to_remove.append(shape)
for shape in boxes_to_remove:
    sp = shape._element
    sp.getparent().remove(sp)
# Insere le schema de deploiement
add_centered_picture(slide18, HERE / "diagram_mode_deploiement.png",
                     top_in=3.0, width_in=22, height_in=11)

# =================================================================== #
# SLIDE 19 - Eco-conception
# =================================================================== #
replace_in_shape(slides[18], 2,
    "Evaluation prevue avec Lighthouse sur l'application sociétaire MA2E "
    "(score cible >= 90 sur les axes performance, accessibilite et bonnes pratiques)")

# =================================================================== #
# SLIDE 21 - DCP Collectes
# =================================================================== #
replace_in_shape(slides[20], 2,
    "DCP collectees\n"
    "Nom, prenoms, date de naissance, numero CNI, photo CNI recto/verso, "
    "email, telephone, societe employeuse, matricule, date d'embauche")
replace_in_shape(slides[20], 3,
    "Finalite\n"
    "Identification du societaire pour son affiliation a la mutuelle MA2E. "
    "Aucune autre exploitation des donnees collectees.")
replace_in_shape(slides[20], 4,
    "Moyens de securite\n"
    "Chiffrement HTTPS de bout en bout, stockage chiffre au repos, "
    "authentification des agents via Active Directory ERANOVE, "
    "journal d'audit non modifiable, signature electronique du consentement")
replace_in_shape(slides[20], 6,
    "Duree de conservation\n"
    "Donnees du societaire : 5 ans apres la fin de l'affiliation, puis suppression automatique.\n"
    "Conversations et journal d'audit : 12 mois minimum.\n"
    "Donnees agents internes : conservees tant que le compte est actif.")
replace_in_shape(slides[20], 7,
    "Seul un nombre restreint d'administrateurs habilites peut acceder aux donnees "
    "des societaires. Au niveau applicatif, seuls les agents MA2E et le DPO "
    "peuvent consulter un dossier complet. Aucune donnee n'est transferee a un tiers "
    "en dehors des sous-traitants techniques contractualises.")

# =================================================================== #
# SLIDE 22 - Politique de securite
# =================================================================== #
replace_in_shape(slides[21], 7,
    "Conformite DCP / RGPD (Loi CI 2013-450)\n"
    "Notice ARTCI affichee avant collecte | Consentement explicite obligatoire | "
    "Procedure de droit a l'oubli operee par le DPO | "
    "Journal d'audit horodate (utilisateur, IP, action) | "
    "Audit log non modifiable pour toutes les actions critiques")

# =================================================================== #
# SLIDE 23 - Top 3 des risques
# =================================================================== #
slide23 = slides[22]
# On ajoute une zone de texte avec le top 3 (la slide n'a que le titre)
# Tente d'inserer comme un text box centre
from pptx.util import Inches as I
tb = slide23.shapes.add_textbox(
    I(2), I(2.5), I(22.5), I(10),
)
tf = tb.text_frame
tf.word_wrap = True
titles_descs = [
    ("R1 - Indisponibilite WhatsApp Cloud API",
     "Si le service de Meta tombe en panne, le canal principal d'enrolement est interrompu.\n"
     "Mesure : basculement temporaire des nouveaux sociétaires sur le chat web, communication aux agences."),
    ("R2 - Non-conformite ARTCI",
     "Un audit defavorable pourrait imposer la suspension du traitement des donnees.\n"
     "Mesure : validation prealable de la notice ARTCI par le DPO, audit blanc en recette."),
    ("R3 - Faible adoption par les sociétaires retraites",
     "Une partie des retraites n'utilise pas WhatsApp ou un smartphone.\n"
     "Mesure : maintien du canal papier en parallele pendant la phase de migration, formation des agences."),
]
for title, desc in titles_descs:
    p = tf.add_paragraph()
    run = p.add_run()
    run.text = title
    run.font.size = Pt(28)
    run.font.bold = True
    run.font.color.rgb = RGBColor(0, 0, 0)
    run.font.name = "Century Gothic"

    p2 = tf.add_paragraph()
    run2 = p2.add_run()
    run2.text = desc
    run2.font.size = Pt(20)
    run2.font.color.rgb = RGBColor(0, 0, 0)
    run2.font.name = "Open Sans"

    p3 = tf.add_paragraph()
    p3.add_run().text = ""

# =================================================================== #
# Sauvegarde
# =================================================================== #
prs.save(str(OUT))
print(f"OK  CVATL MA2E genere : {OUT}")
print(f"    Taille : {OUT.stat().st_size / 1024:.0f} Ko")
