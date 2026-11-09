"""
Modifie le PPTX MA2E_CVATL_v1 :
- Slide 15 : tableau RAM/CPU/Disques/OS rempli avec specs MA2E
- Slide 16 : matrice des flux MA2E (HTTPS, PostgreSQL/Redis/MinIO, SSH)
- Slide 19 : image DCP regénérée avec design orange/crème + contenu MA2E

Sauvegarde dans MA2E_CVATL_v2.pptx
"""
from pathlib import Path
from copy import deepcopy

from pptx import Presentation
from pptx.util import Emu, Pt
from pptx.dml.color import RGBColor

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

ROOT = Path(__file__).parent
SRC = ROOT / "MA2E_CVATL_v1.pptx"
DST = ROOT / "MA2E_CVATL_v2.pptx"
IMG_DCP = ROOT / "slide19_dcp_ma2e.png"


# =================================================================
# Helpers : modifier une cellule en préservant le formatage du run 0
# =================================================================
def set_cell_text(cell, text, *, bold=None, color=None, size_emu=None):
    """
    Modifie le texte d'une cellule en gardant le formatage existant
    (ou applique le formatage donné si la cellule était vide).
    """
    tf = cell.text_frame
    # On retient le formatage du premier run existant s'il y en a un
    existing_font = None
    if tf.paragraphs and tf.paragraphs[0].runs:
        existing_font = tf.paragraphs[0].runs[0].font

    # Si plusieurs lignes, on les sépare par \n et on crée des paragraphes
    lines = text.split("\n")

    # Vider le text_frame mais garder le 1er paragraphe
    tf.clear()
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = lines[0]
    if existing_font and existing_font.size:
        run.font.size = existing_font.size
    elif size_emu:
        run.font.size = Emu(size_emu)
    if bold is not None:
        run.font.bold = bold
    if color is not None:
        run.font.color.rgb = color

    for line in lines[1:]:
        p2 = tf.add_paragraph()
        r2 = p2.add_run()
        r2.text = line
        if existing_font and existing_font.size:
            r2.font.size = existing_font.size
        elif size_emu:
            r2.font.size = Emu(size_emu)
        if bold is not None:
            r2.font.bold = bold
        if color is not None:
            r2.font.color.rgb = color


# =================================================================
# Étape 1 — Génère l'image DCP MA2E (style orange / crème)
# =================================================================
def generate_dcp_image():
    HDR = "#E78A2D"          # orange foncé header
    BAND = "#FDE9D4"         # crème (band rows)
    BAND_ALT = "#FAD9B3"     # orange clair (band alt)
    TXT = "#1A1A1A"
    BORDER = "#E78A2D"

    headers = ["Source", "Destination", "Données (DCP)", "Finalités"]

    rows = [
        # Sociétaire onboarding
        ("Sociétaire\n(WhatsApp / Web)", "API MA2E\n(PostgreSQL)", [
            "Nom, Prénoms",
            "Date de naissance",
            "Email, Téléphone",
            "Matricule",
            "Numéro CNI",
            "Photo CNI recto / verso",
            "Consentement ARTCI",
        ], [
            "Identification du sociétaire",
            "Création du dossier d'enrôlement",
            "Vérification éligibilité matricule",
            "Authentification par OTP",
            "Traçabilité conforme ARTCI",
        ]),
        # Agent MA2E
        ("Agent MA2E", "API MA2E\n(PostgreSQL)", [
            "Login / Mot de passe (hash)",
            "Nom, Prénoms",
            "Email professionnel",
            "Rôle, Statut",
            "AD login ERANOVE",
        ], [
            "Authentification agent",
            "Gestion des comptes utilisateurs",
            "Validation des dossiers sociétaires",
            "Traçabilité des actions (audit)",
        ]),
        # Export Perfect Vision
        ("API MA2E", "Perfect Vision\n(groupe ERANOVE)", [
            "Numéro sociétaire MA2E",
            "Nom, Prénoms",
            "Matricule, Société",
            "Date de validation",
        ], [
            "Export du dossier validé",
            "Enregistrement définitif côté groupe",
            "Synchronisation des sociétaires actifs",
        ]),
        # OCR / IA Azure
        ("API MA2E", "Azure AI\n(OCR + LLM)", [
            "Photos CNI recto / verso",
            "Contenu des conversations",
        ], [
            "Extraction automatique des données CNI",
            "Assistance conversationnelle (RAG)",
            "Détection des pièces non conformes",
        ]),
        # Administrateur
        ("Administrateur", "API MA2E,\nPostgreSQL, Redis, MinIO", [
            "Login / Mot de passe",
            "Email, Nom, Prénoms",
            "Données d'audit\n(IP, horodatage, actions)",
        ], [
            "Accès et configuration des systèmes",
            "Gestion des référentiels",
            "Consultation du journal d'audit",
            "Anonymisation / droit à l'oubli",
        ]),
    ]

    # Largeurs proportionnelles
    col_w = [0.18, 0.18, 0.30, 0.34]

    # Calcul hauteur dynamique
    row_heights = []
    HEADER_H = 0.50
    for src, dst, dcp, fin in rows:
        n_dcp = sum(1 for d in dcp)
        n_fin = sum(1 for f in fin)
        n_lines = max(n_dcp, n_fin,
                      len(src.split("\n")), len(dst.split("\n")))
        row_heights.append(0.32 * max(n_lines, 2) + 0.20)

    total_h = HEADER_H + sum(row_heights)
    fig_w = 16
    fig_h = total_h * 1.4
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.set_xlim(0, 1); ax.set_ylim(0, total_h)
    ax.set_aspect('auto'); ax.axis('off')
    fig.patch.set_facecolor('white')

    # Header
    x = 0.0
    y_top = total_h
    for i, h in enumerate(headers):
        w = col_w[i]
        ax.add_patch(mpatches.Rectangle((x, y_top - HEADER_H), w, HEADER_H,
            facecolor=HDR, edgecolor=BORDER, linewidth=1.5))
        ax.text(x + w/2, y_top - HEADER_H/2, h,
            fontsize=14, fontweight='bold', color='white',
            ha='center', va='center')
        x += w

    # Rows
    y = y_top - HEADER_H
    for ri, (src, dst, dcp, fin) in enumerate(rows):
        rh = row_heights[ri]
        x = 0.0
        bg = BAND if ri % 2 == 0 else BAND_ALT
        for i, content in enumerate([src, dst, dcp, fin]):
            w = col_w[i]
            ax.add_patch(mpatches.Rectangle((x, y - rh), w, rh,
                facecolor=bg, edgecolor=BORDER, linewidth=1.0))

            if isinstance(content, list):
                txt = "\n".join(f"• {item}" for item in content)
                ax.text(x + 0.012, y - 0.18, txt,
                    fontsize=10, color=TXT, ha='left', va='top')
            else:
                ax.text(x + w/2, y - rh/2, content,
                    fontsize=11, color=TXT,
                    ha='center', va='center', fontweight='bold')
            x += w
        y -= rh

    plt.savefig(IMG_DCP, dpi=200, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f"OK  Image DCP générée : {IMG_DCP}")


# =================================================================
# Étape 2 — Modifie le PPTX
# =================================================================
def modify_pptx():
    p = Presentation(str(SRC))

    # ---------- Slide 15 : Synthèse RAM/CPU/Disques/OS ----------
    slide = p.slides[14]
    for shape in slide.shapes:
        if not shape.has_table:
            continue
        tbl = shape.table
        # 5 lignes x 6 cols (header + 4 lignes de données)
        # Col 0 (Couche) déjà rempli : Front Web / Back Office / API / Batch
        data = [
            # (couche, users, ram, cpu, disque, os)  — row 1..4
            ("Front Web\n(Next.js)",       "200 simultanés",   "4 Go",  "2 vCPU", "30 Go SSD",  "Ubuntu 22.04 LTS"),
            ("Back Office\n(Next.js)",     "30 agents",        "2 Go",  "2 vCPU", "20 Go SSD",  "Ubuntu 22.04 LTS"),
            ("API\n(FastAPI)",             "300 req/min",      "8 Go",  "4 vCPU", "50 Go SSD",  "Ubuntu 22.04 LTS"),
            ("Batch\n(Workers OCR/IA/Sync)", "N/A (asynchrone)", "8 Go",  "4 vCPU", "100 Go SSD", "Ubuntu 22.04 LTS"),
        ]
        for r in range(1, 5):
            for c in range(6):
                set_cell_text(tbl.cell(r, c), data[r-1][c])
        print("OK  Slide 15 (RAM/CPU/Disques/OS) modifié")

    # ---------- Slide 16 : Matrice des flux ----------
    slide = p.slides[15]
    for shape in slide.shapes:
        if not shape.has_table:
            continue
        tbl = shape.table
        # 4 lignes x 4 cols (header + 3 lignes de données)
        flux = [
            ("Sociétaire / Agent MA2E",
             "Load Balancer | Web | API MA2E\n→ api.ma2e.ci",
             "TCP/443 (HTTPS)",
             "Accès interface web sociétaire + API MA2E\nWebhooks WhatsApp Cloud API (Meta)"),
            ("API MA2E",
             "PostgreSQL 16 + pgvector\nRedis 7\nMinIO / S3",
             "TCP/5432\nTCP/6379\nTCP/443",
             "Accès aux données métier (BD principale),\ncache + sessions, stockage chiffré des CNI"),
            ("Administrateur",
             "PostgreSQL, Redis, MinIO,\nServeurs Web + API + Workers",
             "TCP/22 (SSH)",
             "Accès aux systèmes via SSH\npour administration et maintenance"),
        ]
        for r in range(1, 4):
            for c in range(4):
                set_cell_text(tbl.cell(r, c), flux[r-1][c])
        print("OK  Slide 16 (Matrice des flux) modifié")

    # ---------- Slide 19 : Image DCP ----------
    slide = p.slides[18]
    for shape in list(slide.shapes):
        if shape.shape_type == 13:  # PICTURE
            # Sauvegarder la position et la taille
            left, top, width, height = shape.left, shape.top, shape.width, shape.height
            # Supprimer l'ancienne image
            sp = shape._element
            sp.getparent().remove(sp)
            # Insérer la nouvelle image à la même position
            slide.shapes.add_picture(str(IMG_DCP),
                left=left, top=top, width=width, height=height)
            print("OK  Slide 19 (image DCP) remplacée")
            break

    p.save(str(DST))
    print(f"\nOK  Fichier sauvegardé : {DST}")


# =================================================================
# Main
# =================================================================
if __name__ == "__main__":
    generate_dcp_image()
    modify_pptx()
