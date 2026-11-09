"""Schemas additionnels pour le CVATL MA2E.
Style strict : noir et blanc, carres et traits, Times New Roman.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch

OUT = Path(__file__).parent
plt.rcParams["font.family"] = "Times New Roman"
plt.rcParams["font.size"] = 10


def box(ax, x, y, w, h, text, fontsize=10, bold=False, dashed=False):
    rect = mpatches.Rectangle(
        (x, y), w, h,
        linewidth=1.3, edgecolor="black", facecolor="white",
        linestyle="--" if dashed else "-",
    )
    ax.add_patch(rect)
    ax.text(
        x + w / 2, y + h / 2, text,
        ha="center", va="center",
        fontsize=fontsize, color="black",
        fontweight="bold" if bold else "normal",
    )


def line(ax, x1, y1, x2, y2, arrow=True, label=None, label_offset=0.15, label_fs=9):
    if arrow:
        a = FancyArrowPatch(
            (x1, y1), (x2, y2),
            arrowstyle="-|>",
            mutation_scale=12,
            linewidth=1.0, color="black",
        )
        ax.add_patch(a)
    else:
        ax.plot([x1, x2], [y1, y2], color="black", linewidth=1.0)
    if label:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        ax.text(mx, my + label_offset, label,
                ha="center", va="bottom",
                fontsize=label_fs, color="black", style="italic")


# =================================================================== #
# 1. Top 5 entites metier (modele simplifie)
# =================================================================== #
def make_entites_metier():
    fig, ax = plt.subplots(figsize=(12, 7))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 8)
    ax.set_axis_off()

    ax.text(7, 7.5, "Top 5 des entites metier de la plateforme MA2E",
            ha="center", fontsize=12, fontweight="bold")

    # Entite centrale : SOCIETAIRE
    box(ax, 5.5, 3.5, 3.0, 2.0, "SOCIETAIRE\n\n- Nom, prenoms\n- Date de naissance\n- CNI, email\n- Societe affiliee",
        fontsize=9, bold=True)

    # Entites peripheriques (4 autres)
    box(ax, 0.5, 5.0, 3.0, 1.8, "CONVERSATION\n\n- Canal\n- Etat machine\n- Historique",
        fontsize=9, bold=True)
    box(ax, 10.5, 5.0, 3.0, 1.8, "DOSSIER\n\n- Statut\n- Numero MA2E\n- Date validation",
        fontsize=9, bold=True)
    box(ax, 0.5, 1.0, 3.0, 1.8, "PIECE D'IDENTITE\n\n- Recto, verso\n- Donnees extraites\n- Score OCR",
        fontsize=9, bold=True)
    box(ax, 10.5, 1.0, 3.0, 1.8, "CONSENTEMENT\n\n- Signature HMAC\n- Horodatage\n- Texte signe",
        fontsize=9, bold=True)

    # Liaisons
    line(ax, 3.5, 5.5, 5.5, 4.8, label="initie", arrow=False)
    line(ax, 8.5, 4.8, 10.5, 5.5, label="constitue", arrow=False)
    line(ax, 3.5, 2.2, 5.5, 4.0, label="fournit", arrow=False)
    line(ax, 8.5, 4.0, 10.5, 2.2, label="donne", arrow=False)

    plt.tight_layout()
    fig.savefig(OUT / "diagram_entites_metier.png", dpi=180,
                bbox_inches="tight", facecolor="white")
    plt.close(fig)


# =================================================================== #
# 2. Architecture logicielle 1/2 : couches
# =================================================================== #
def make_archi_log_1():
    fig, ax = plt.subplots(figsize=(12, 7))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 8)
    ax.set_axis_off()

    ax.text(7, 7.5, "Architecture logicielle - couches applicatives",
            ha="center", fontsize=12, fontweight="bold")

    # 4 couches empilees (sans connecteurs visuels, l'empilement suffit)
    box(ax, 1.0, 5.5, 12.0, 1.1,
        "Couche presentation\nApplication web MA2E (Next.js) + back-office agent",
        fontsize=10, bold=True)
    box(ax, 1.0, 4.0, 12.0, 1.1,
        "Couche metier\nApplication serveur MA2E (FastAPI) : conversation, extraction, validation, audit",
        fontsize=10, bold=True)
    box(ax, 1.0, 2.5, 12.0, 1.1,
        "Couche services techniques\nService de notifications, service de signature des consentements",
        fontsize=10, bold=True)
    box(ax, 1.0, 1.0, 12.0, 1.1,
        "Couche persistance\nBase de donnees PostgreSQL + stockage Azure Blob + coffre-fort Azure Key Vault",
        fontsize=10, bold=True)

    plt.tight_layout()
    fig.savefig(OUT / "diagram_archi_log_1.png", dpi=180,
                bbox_inches="tight", facecolor="white")
    plt.close(fig)


# =================================================================== #
# 3. Architecture logicielle 2/2 : modules internes
# =================================================================== #
def make_archi_log_2():
    fig, ax = plt.subplots(figsize=(12, 7))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 8)
    ax.set_axis_off()

    ax.text(7, 7.5, "Architecture logicielle - modules internes",
            ha="center", fontsize=12, fontweight="bold")

    # Cadre englobant
    box(ax, 0.5, 0.8, 13.0, 5.8,
        "", dashed=True)
    ax.text(0.7, 6.3, "Application serveur MA2E",
            fontsize=10, style="italic", fontweight="bold")

    # 8 modules sur 2 rangees, separation claire
    modules = [
        (1.2, 4.5, "Conversation",
         "dialogue sociétaire\net état du parcours"),
        (4.5, 4.5, "Extraction CNI",
         "lecture automatique\nde la pièce d'identité"),
        (7.8, 4.5, "Consentement",
         "recueil et signature\ndu consentement"),
        (11.0, 4.5, "Assistant AYA",
         "réponses aux\nquestions courantes"),
        (1.2, 1.4, "Validation",
         "traitement du dossier\npar l'agent"),
        (4.5, 1.4, "Notifications",
         "envoi des messages\net codes OTP"),
        (7.8, 1.4, "Administration",
         "utilisateurs, sociétés\net modèles"),
        (11.0, 1.4, "Audit",
         "journal non modifiable\ndes actions sensibles"),
    ]
    for x, y, name, desc in modules:
        box(ax, x, y, 2.2, 1.5, f"{name}\n\n{desc}", fontsize=9, bold=False)

    plt.tight_layout()
    fig.savefig(OUT / "diagram_archi_log_2.png", dpi=180,
                bbox_inches="tight", facecolor="white")
    plt.close(fig)


# =================================================================== #
# 4. Architecture logicielle 3 : services externes
# =================================================================== #
def make_archi_log_3():
    fig, ax = plt.subplots(figsize=(12, 7))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 8)
    ax.set_axis_off()

    ax.text(7, 7.5, "Architecture logicielle - integrations externes",
            ha="center", fontsize=12, fontweight="bold")

    # Application serveur MA2E au centre
    box(ax, 5.0, 3.5, 4.0, 1.6,
        "Application serveur MA2E",
        fontsize=11, bold=True)

    # Services externes autour
    box(ax, 0.5, 5.5, 3.0, 1.2, "WhatsApp Cloud API\n(Meta)", fontsize=9, bold=True)
    box(ax, 10.5, 5.5, 3.0, 1.2, "Service d'extraction\nde la CNI", fontsize=9, bold=True)
    box(ax, 0.5, 1.5, 3.0, 1.2, "Service d'envoi\nd'emails", fontsize=9, bold=True)
    box(ax, 10.5, 1.5, 3.0, 1.2, "Modele de langage\n(assistant AYA)", fontsize=9, bold=True)
    box(ax, 5.0, 0.4, 4.0, 1.0, "Active Directory ERANOVE\n(authentification agents)",
        fontsize=9, bold=True)

    # Liaisons centre - peripherie (lignes simples)
    line(ax, 5.0, 4.7, 3.5, 6.1, label="messages")
    line(ax, 9.0, 4.7, 10.5, 6.1, label="OCR")
    line(ax, 5.0, 3.8, 3.5, 2.1, label="emails")
    line(ax, 9.0, 3.8, 10.5, 2.1, label="Q & R")
    line(ax, 7.0, 3.5, 7.0, 1.4, label="connexions")

    plt.tight_layout()
    fig.savefig(OUT / "diagram_archi_log_3.png", dpi=180,
                bbox_inches="tight", facecolor="white")
    plt.close(fig)


# =================================================================== #
# 5. Mode de deploiement
# =================================================================== #
def make_mode_deploiement():
    fig, ax = plt.subplots(figsize=(12, 7))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 8)
    ax.set_axis_off()

    ax.text(7, 7.5, "Mode de deploiement - conteneurs Docker portables",
            ha="center", fontsize=12, fontweight="bold")

    # Conteneurs Docker au centre haut
    box(ax, 4.5, 5.0, 5.0, 1.2, "Conteneurs Docker MA2E\n(site web + serveur applicatif + service notifications)",
        fontsize=10, bold=True)

    # Deux destinations possibles (lignes pointillees = alternatives)
    box(ax, 0.5, 1.5, 6.0, 2.5,
        "Environnement principal\n\nMicrosoft Azure\n(region France Centre)\n- App Service\n- Base PostgreSQL managee\n- Stockage Blob + Key Vault",
        fontsize=10, bold=True)
    box(ax, 7.5, 1.5, 6.0, 2.5,
        "Environnement alternatif\n\nData Center GS2E\n(sur sol ivoirien)\n- Serveurs internes\n- Active Directory ERANOVE\n- Stockage interne",
        fontsize=10, bold=True)

    line(ax, 6.0, 5.0, 3.5, 4.0, label="deploiement principal")
    line(ax, 8.0, 5.0, 10.5, 4.0, label="repli local possible")

    plt.tight_layout()
    fig.savefig(OUT / "diagram_mode_deploiement.png", dpi=180,
                bbox_inches="tight", facecolor="white")
    plt.close(fig)


# =================================================================== #
# 6. Planning macro
# =================================================================== #
def make_planning():
    fig, ax = plt.subplots(figsize=(13, 6))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 7)
    ax.set_axis_off()

    ax.text(7, 6.5, "Macro planning du projet MA2E",
            ha="center", fontsize=12, fontweight="bold")

    # 7 phases en sequence horizontale
    phases = [
        ("Cadrage", "Mars 2026"),
        ("Conception", "Avril 2026"),
        ("Developpement", "Mai - Sept. 2026"),
        ("Recette", "Octobre 2026"),
        ("Pilote 50 societaires", "Novembre 2026"),
        ("Elargissement", "Dec. 2026 - Janv. 2027"),
        ("Mise en service", "Fevrier 2027"),
    ]
    n = len(phases)
    w = 1.7
    gap = 0.15
    total = n * w + (n - 1) * gap
    start_x = (14 - total) / 2
    y = 3.5
    h = 1.5

    centers = []
    for i, (title, date) in enumerate(phases):
        x = start_x + i * (w + gap)
        box(ax, x, y, w, h, f"{title}\n\n{date}", fontsize=9, bold=True)
        centers.append(x + w / 2)

    for i in range(n - 1):
        x1 = centers[i] + w / 2
        x2 = centers[i + 1] - w / 2
        line(ax, x1, y + h / 2, x2, y + h / 2)

    # Jalon de mise en service grand format en dessous
    ax.text(7, 1.8,
            "Demonstration au comite : 15 mai 2026 (point d'avancement projet)",
            ha="center", fontsize=10, style="italic")

    plt.tight_layout()
    fig.savefig(OUT / "diagram_planning.png", dpi=180,
                bbox_inches="tight", facecolor="white")
    plt.close(fig)


# =================================================================== #
# 7. Evaluation PRI : matrice de risques B&W
# =================================================================== #
def make_pri():
    fig, ax = plt.subplots(figsize=(12, 7.5))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 9)
    ax.set_axis_off()

    ax.text(7, 8.5, "Evaluation des risques projet (matrice probabilite x impact)",
            ha="center", fontsize=12, fontweight="bold")

    # Cadre grille 3x3 (centree, taille raisonnable)
    cell = 1.9
    ox = 4.0
    oy = 1.3
    grid_w = 3 * cell
    grid_h = 3 * cell

    # Lignes / colonnes
    for i in range(4):
        line(ax, ox, oy + i * cell, ox + grid_w, oy + i * cell, arrow=False)
        line(ax, ox + i * cell, oy, ox + i * cell, oy + grid_h, arrow=False)

    # Labels axes Y (Probabilite)
    for j, lab in enumerate(["Faible", "Moyen", "Eleve"]):
        ax.text(ox - 0.3, oy + (j + 0.5) * cell, lab,
                ha="right", va="center", fontsize=10)
    ax.text(ox - 1.4, oy + grid_h / 2, "Probabilite",
            ha="center", va="center", fontsize=11,
            rotation=90, fontweight="bold")

    # Labels axes X (Impact)
    for j, lab in enumerate(["Faible", "Moyen", "Eleve"]):
        ax.text(ox + (j + 0.5) * cell, oy - 0.3, lab,
                ha="center", va="top", fontsize=10)
    ax.text(ox + grid_w / 2, oy - 1.0, "Impact",
            ha="center", va="center", fontsize=11, fontweight="bold")

    # Placement des risques (case = (col_impact, ligne_proba))
    risks = [
        (2, 1, "R1"),       # WhatsApp : impact eleve, proba moyenne
        (1, 0, "R2"),       # Adoption retraites : impact moyen, proba faible
        (2, 2, "R3"),       # Conformite ARTCI : impact eleve, proba eleve
        (1, 1, "R4"),       # OCR CNI : impact moyen, proba moyenne
        (0, 2, "R5"),       # Delai : impact faible, proba eleve
    ]
    for col, lig, label in risks:
        cx = ox + col * cell + cell / 2
        cy = oy + lig * cell + cell / 2
        sz = 0.7
        ax.add_patch(mpatches.Rectangle(
            (cx - sz / 2, cy - sz / 2), sz, sz,
            linewidth=1.3, edgecolor="black", facecolor="white"))
        ax.text(cx, cy, label, ha="center", va="center",
                fontsize=10, fontweight="bold")

    # Legende a droite
    legend_x = ox + grid_w + 0.8
    legend_y = oy + grid_h - 0.3
    ax.text(legend_x, legend_y, "Legende des risques",
            ha="left", va="top", fontsize=10, fontweight="bold")
    legend = [
        "R1 : Indisponibilite WhatsApp Cloud API",
        "R2 : Faible adoption par les retraites",
        "R3 : Retard de conformite ARTCI",
        "R4 : Erreurs d'extraction de la CNI",
        "R5 : Glissement du planning projet",
    ]
    for i, txt in enumerate(legend):
        ax.text(legend_x, legend_y - 0.5 - i * 0.4, txt,
                ha="left", va="top", fontsize=9)

    plt.tight_layout()
    fig.savefig(OUT / "diagram_pri.png", dpi=180,
                bbox_inches="tight", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    make_entites_metier()
    make_archi_log_1()
    make_archi_log_2()
    make_archi_log_3()
    make_mode_deploiement()
    make_planning()
    make_pri()
    print("OK  7 schemas CVATL generes")
