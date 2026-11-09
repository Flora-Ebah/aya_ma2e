"""Genere les schemas N&B (PNG) utilises dans les documents Word.
Style : noir et blanc strict, lignes nettes, Times New Roman.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = Path(__file__).parent
plt.rcParams["font.family"] = "Times New Roman"
plt.rcParams["font.size"] = 10


def box(ax, x, y, w, h, text, fontsize=10, bold=False):
    ax.add_patch(
        FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.02",
            linewidth=1.2,
            edgecolor="black",
            facecolor="white",
        )
    )
    ax.text(
        x + w / 2, y + h / 2, text,
        ha="center", va="center",
        fontsize=fontsize, color="black",
        fontweight="bold" if bold else "normal",
    )


def arrow(ax, x1, y1, x2, y2, text=None, fontsize=8, text_offset=0.15):
    a = FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle="-|>",
        mutation_scale=12,
        linewidth=1.0,
        color="black",
    )
    ax.add_patch(a)
    if text:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        ax.text(
            mx, my + text_offset, text,
            ha="center", va="bottom",
            fontsize=fontsize, color="black",
            style="italic",
        )


# ----------------------------------------------------------------- #
# 1. Architecture macro (couches utilisateur + applicatif + donnees)
# ----------------------------------------------------------------- #
def make_archi_macro():
    fig, ax = plt.subplots(figsize=(10, 6.5))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 9)
    ax.set_axis_off()

    ax.text(6, 8.6, "Architecture macro de la plateforme MA2E",
            ha="center", fontsize=12, fontweight="bold")

    # Utilisateurs (haut)
    box(ax, 0.5, 7.0, 2.2, 0.9, "Sociétaire\n(WhatsApp)", bold=True)
    box(ax, 4.9, 7.0, 2.2, 0.9, "Sociétaire\n(Navigateur web)", bold=True)
    box(ax, 9.3, 7.0, 2.2, 0.9, "Agent MA2E\n(Back-office)", bold=True)

    # Canaux (intermediaire)
    box(ax, 0.5, 5.4, 2.2, 0.8, "WhatsApp\nCloud API")
    box(ax, 4.9, 5.4, 2.2, 0.8, "Site web\nMA2E")
    box(ax, 9.3, 5.4, 2.2, 0.8, "Application\nback-office")

    # Couche applicative
    box(ax, 2.0, 3.4, 8.0, 1.2,
        "Plateforme applicative MA2E\n"
        "Conversation - Extraction CNI - Validation - Notifications - Audit",
        bold=True)

    # Donnees
    box(ax, 0.5, 1.4, 3.0, 1.2, "Base de données\nMA2E", bold=True)
    box(ax, 4.5, 1.4, 3.0, 1.2, "Espace de stockage\ndes pièces", bold=True)
    box(ax, 8.5, 1.4, 3.0, 1.2, "Journal d'audit\n(non modifiable)", bold=True)

    # Fleches
    arrow(ax, 1.6, 7.0, 1.6, 6.2)
    arrow(ax, 6.0, 7.0, 6.0, 6.2)
    arrow(ax, 10.4, 7.0, 10.4, 6.2)

    arrow(ax, 1.6, 5.4, 4.0, 4.6)
    arrow(ax, 6.0, 5.4, 6.0, 4.6)
    arrow(ax, 10.4, 5.4, 8.0, 4.6)

    arrow(ax, 4.0, 3.4, 2.0, 2.6)
    arrow(ax, 6.0, 3.4, 6.0, 2.6)
    arrow(ax, 8.0, 3.4, 10.0, 2.6)

    plt.tight_layout()
    fig.savefig(OUT / "diagram_archi_macro.png", dpi=180, bbox_inches="tight",
                facecolor="white")
    plt.close(fig)


# ----------------------------------------------------------------- #
# 2. Flux onboarding WhatsApp (sequence simplifiee)
# ----------------------------------------------------------------- #
def make_flux_onboarding():
    fig, ax = plt.subplots(figsize=(11, 7.5))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 11)
    ax.set_axis_off()

    ax.text(6.5, 10.5, "Parcours d'enrôlement d'un sociétaire via WhatsApp",
            ha="center", fontsize=12, fontweight="bold")

    # Acteurs en haut (lignes de vie)
    actors = [
        (1.2, "Sociétaire"),
        (4.0, "Assistante AYA\n(WhatsApp)"),
        (7.0, "Plateforme\nMA2E"),
        (9.8, "Service\nd'extraction\nde la CNI"),
        (12.4, "Agent\nMA2E"),
    ]
    for x, name in actors:
        ax.text(x, 9.8, name, ha="center", fontsize=9.5, fontweight="bold")
        ax.plot([x, x], [0.5, 9.4], color="black", linewidth=0.7,
                linestyle="--")

    # Sequences (y descend)
    steps = [
        (9.0, 1.2, 4.0, "Premier message"),
        (8.6, 4.0, 7.0, "Création de la session"),
        (8.2, 7.0, 4.0, "Demande de consentement"),
        (7.8, 4.0, 1.2, "Notice ARTCI"),
        (7.4, 1.2, 4.0, "J'accepte"),
        (6.8, 4.0, 7.0, "Consentement enregistré"),
        (6.4, 7.0, 4.0, "Demande des photos CNI"),
        (6.0, 4.0, 1.2, "Recto puis verso"),
        (5.4, 1.2, 4.0, "Envoi des photos"),
        (5.0, 4.0, 7.0, "Stockage chiffré"),
        (4.6, 7.0, 9.8, "Demande d'extraction"),
        (4.2, 9.8, 7.0, "Données extraites + score"),
        (3.6, 7.0, 4.0, "Validation des données"),
        (3.2, 4.0, 1.2, "Confirmation au sociétaire"),
        (2.6, 1.2, 4.0, "Confirme / corrige"),
        (2.2, 4.0, 7.0, "Dossier en attente de validation"),
        (1.6, 7.0, 12.4, "Mise en file d'attente agent"),
        (1.0, 12.4, 4.0, "Décision (validé / refusé)", "italic"),
    ]
    for s in steps:
        y, x1, x2, txt = s[:4]
        arrow(ax, x1, y, x2, y, txt, fontsize=8)

    plt.tight_layout()
    fig.savefig(OUT / "diagram_flux_onboarding.png", dpi=180,
                bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ----------------------------------------------------------------- #
# 3. Topologie de deploiement Azure
# ----------------------------------------------------------------- #
def make_topologie():
    fig, ax = plt.subplots(figsize=(11, 7.5))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 10)
    ax.set_axis_off()

    ax.text(6.5, 9.6, "Topologie de déploiement de la plateforme MA2E",
            ha="center", fontsize=12, fontweight="bold")

    # Internet / utilisateurs
    box(ax, 5.5, 8.2, 2.0, 0.7, "Internet")

    # Passerelle entree
    box(ax, 4.0, 7.0, 5.0, 0.8,
        "Passerelle d'entrée Azure\n(filtrage, pare-feu applicatif, chiffrement HTTPS)",
        bold=True)

    # Zone Azure
    ax.add_patch(mpatches.Rectangle(
        (0.4, 1.2), 12.2, 5.2,
        linewidth=1.1, edgecolor="black",
        facecolor="white", linestyle="--"))
    ax.text(0.6, 6.1,
            "Environnement Microsoft Azure (région France Centre)",
            fontsize=9, style="italic")

    # Services applicatifs
    box(ax, 0.8, 4.0, 3.0, 1.4,
        "Site web MA2E\n(application sociétaire\net back-office agent)",
        bold=True)
    box(ax, 4.8, 4.0, 3.4, 1.4,
        "Application serveur MA2E\n(API métier, conversation,\nextraction, audit)",
        bold=True)
    box(ax, 9.2, 4.0, 3.0, 1.4,
        "Service de notifications\n(envoi email + WhatsApp,\ncodes OTP)",
        bold=True)

    # Couche donnees
    box(ax, 1.0, 1.6, 3.2, 1.6,
        "Base de données\nrelationnelle managée\n(données métier MA2E)",
        bold=True)
    box(ax, 5.0, 1.6, 3.2, 1.6,
        "Espace de stockage\nsécurisé\n(photos CNI, exports)",
        bold=True)
    box(ax, 9.0, 1.6, 3.2, 1.6,
        "Coffre-fort de secrets\n(clés, mots de passe,\njetons d'API)",
        bold=True)

    # Fleches
    arrow(ax, 6.5, 8.2, 6.5, 7.8)
    arrow(ax, 5.0, 7.0, 2.3, 5.4)
    arrow(ax, 6.5, 7.0, 6.5, 5.4)
    arrow(ax, 8.0, 7.0, 10.7, 5.4)

    arrow(ax, 6.5, 4.0, 2.6, 3.2)
    arrow(ax, 6.5, 4.0, 6.5, 3.2)
    arrow(ax, 6.5, 4.0, 10.5, 3.2)

    plt.tight_layout()
    fig.savefig(OUT / "diagram_topologie.png", dpi=180,
                bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ----------------------------------------------------------------- #
# 4. Pyramide de tests
# ----------------------------------------------------------------- #
def make_pyramide_tests():
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 8)
    ax.set_axis_off()

    ax.text(5, 7.5, "Pyramide de tests de la plateforme MA2E",
            ha="center", fontsize=12, fontweight="bold")

    levels = [
        (0.5, 5.5, 9.0, 1.0, "Tests unitaires (≈ 450 tests)",
         "exécutés à chaque modification du code"),
        (1.6, 4.3, 6.8, 1.0, "Tests d'intégration (≈ 80 tests)",
         "vérification des interactions entre modules"),
        (2.7, 3.1, 4.6, 1.0, "Tests end-to-end (≈ 15 parcours)",
         "simulation d'un utilisateur réel"),
        (3.5, 1.9, 3.0, 1.0, "Tests de performance (5 scénarios)",
         "mesure de la tenue à la charge"),
        (4.1, 0.7, 1.8, 1.0, "Sécurité + recette UAT",
         "validation finale par la métier"),
    ]
    for x, y, w, h, title, desc in levels:
        ax.add_patch(mpatches.Rectangle(
            (x, y), w, h, linewidth=1.2, edgecolor="black",
            facecolor="white"))
        ax.text(x + w / 2, y + h * 0.6, title,
                ha="center", fontsize=10, fontweight="bold")
        ax.text(x + w / 2, y + h * 0.25, desc,
                ha="center", fontsize=8, style="italic")

    plt.tight_layout()
    fig.savefig(OUT / "diagram_pyramide_tests.png", dpi=180,
                bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ----------------------------------------------------------------- #
# 5. Pipeline de mise en production
# ----------------------------------------------------------------- #
def make_cicd():
    fig, ax = plt.subplots(figsize=(13, 5.5))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 6)
    ax.set_axis_off()

    ax.text(8, 5.6, "Chaîne de mise en production",
            ha="center", fontsize=12, fontweight="bold")

    steps = [
        ("Modification\ndu code"),
        ("Contrôles\nautomatiques\nde qualité"),
        ("Exécution\ndes tests\nautomatisés"),
        ("Préparation\ndu paquet\nd'installation"),
        ("Déploiement\nen recette"),
        ("Validation\npar le métier"),
        ("Mise en\nproduction"),
    ]
    n = len(steps)
    w = 1.85
    h = 1.6
    gap = 0.25
    total = n * w + (n - 1) * gap
    start_x = (16 - total) / 2
    y = 2.2

    centers = []
    for i, label in enumerate(steps):
        x = start_x + i * (w + gap)
        box(ax, x, y, w, h, label, fontsize=9)
        centers.append(x + w / 2)

    for i in range(n - 1):
        x1 = centers[i] + w / 2
        x2 = centers[i + 1] - w / 2
        arrow(ax, x1, y + h / 2, x2, y + h / 2)

    # Annotation sous le pipeline
    ax.text(
        8, 1.0,
        "Les étapes 2 à 4 sont automatisées. Les étapes 5 et 7 sont déclenchées sur validation explicite.",
        ha="center", fontsize=9, style="italic",
    )

    plt.tight_layout()
    fig.savefig(OUT / "diagram_cicd.png", dpi=180,
                bbox_inches="tight", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    make_archi_macro()
    make_flux_onboarding()
    make_topologie()
    make_pyramide_tests()
    make_cicd()
    print("OK  Schemas generes dans", OUT)
