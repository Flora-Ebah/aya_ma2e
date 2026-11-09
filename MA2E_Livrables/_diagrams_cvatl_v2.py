"""Schemas CVATL MA2E version 2 - calques sur les exemples SODECI.
Style strict : noir, blanc, gris clair. Pas de couleurs.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch

OUT = Path(__file__).parent
plt.rcParams["font.family"] = "Times New Roman"
plt.rcParams["font.size"] = 9

LIGHT_GRAY = "#E8E8E8"
DASH_GRAY = "#888888"


def box(ax, x, y, w, h, text, fontsize=9, bold=False, dashed=False, fill="white"):
    rect = mpatches.Rectangle(
        (x, y), w, h,
        linewidth=1.3, edgecolor="black", facecolor=fill,
        linestyle="--" if dashed else "-",
    )
    ax.add_patch(rect)
    ax.text(
        x + w / 2, y + h / 2, text,
        ha="center", va="center",
        fontsize=fontsize, color="black",
        fontweight="bold" if bold else "normal",
    )


def rounded_box(ax, x, y, w, h, text, fontsize=9, bold=False, fill="white"):
    rect = mpatches.FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.01,rounding_size=0.15",
        linewidth=1.3, edgecolor="black", facecolor=fill,
    )
    ax.add_patch(rect)
    ax.text(
        x + w / 2, y + h / 2, text,
        ha="center", va="center",
        fontsize=fontsize, color="black",
        fontweight="bold" if bold else "normal",
    )


def container(ax, x, y, w, h, label=None, dashed=True):
    """Cadre conteneur avec etiquette en haut."""
    style = "--" if dashed else "-"
    rect = mpatches.Rectangle(
        (x, y), w, h,
        linewidth=1.2, edgecolor="black", facecolor="none", linestyle=style,
    )
    ax.add_patch(rect)
    if label:
        # Etiquette dans une petite bande grise
        ax.add_patch(mpatches.Rectangle(
            (x + 0.1, y + h - 0.4), len(label) * 0.13 + 0.4, 0.35,
            linewidth=0, facecolor=LIGHT_GRAY))
        ax.text(x + 0.3, y + h - 0.22, label,
                ha="left", va="center", fontsize=8.5,
                fontweight="bold", color="black")


def arrow(ax, x1, y1, x2, y2, label=None, label_fs=8, dashed=False, label_bg=False):
    style = "--" if dashed else "-"
    a = FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle="-|>",
        mutation_scale=10,
        linewidth=1.0, color="black", linestyle=style,
    )
    ax.add_patch(a)
    if label:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        bbox = dict(facecolor="white", edgecolor="none", pad=1.5) if label_bg else None
        ax.text(mx, my, label, ha="center", va="center",
                fontsize=label_fs, color="black", bbox=bbox)


def line(ax, x1, y1, x2, y2, dashed=False):
    style = "--" if dashed else "-"
    ax.plot([x1, x2], [y1, y2], color="black", linewidth=1.0, linestyle=style)


def cylinder(ax, cx, y, w, h, label, fontsize=8, bold=False):
    """Cylindre style base de donnees."""
    # Corps
    ax.add_patch(mpatches.Rectangle(
        (cx - w / 2, y + h * 0.1), w, h * 0.8,
        linewidth=1.3, edgecolor="black", facecolor="white"))
    # Ellipse haut
    ax.add_patch(mpatches.Ellipse(
        (cx, y + h * 0.9), w, h * 0.2,
        linewidth=1.3, edgecolor="black", facecolor="white"))
    # Ellipse bas (juste arc visible)
    ax.add_patch(mpatches.Ellipse(
        (cx, y + h * 0.1), w, h * 0.2,
        linewidth=1.3, edgecolor="black", facecolor="white"))
    ax.text(cx, y + h * 0.5, label,
            ha="center", va="center", fontsize=fontsize,
            color="black", fontweight="bold" if bold else "normal")


# =================================================================== #
# 1. Architecture fonctionnelle MA2E (style SODECI)
# =================================================================== #
def make_archi_fonctionnelle():
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 10)
    ax.set_axis_off()

    # ---- Ligne d'acteurs ----
    ax.text(0.5, 9.3, "ACTEURS", fontsize=9, fontweight="bold", va="center")
    ax.text(4.0, 9.3, "ACTEUR SOCIÉTAIRE", ha="center", fontsize=9, fontweight="bold")
    ax.text(8.0, 9.3, "ACTEUR AGENT MA2E", ha="center", fontsize=9, fontweight="bold")

    # ---- Bande superieure decorative ----
    ax.add_patch(mpatches.Rectangle((1.5, 8.6), 11.0, 0.15,
                                     linewidth=0, facecolor=LIGHT_GRAY))

    # ---- Couche presentation ----
    ax.text(0.5, 7.7, "COUCHE\nPRESENTATION", fontsize=8.5,
            fontweight="bold", va="center")
    box(ax, 2.5, 7.2, 3.0, 1.0, "APPLICATION SOCIÉTAIRE\n(WhatsApp + Web Chat)",
        fontsize=9, bold=True, dashed=True, fill=LIGHT_GRAY)
    box(ax, 6.5, 7.2, 3.0, 1.0, "ADMIN BACK-OFFICE\n(agents MA2E)",
        fontsize=9, bold=True, fill=LIGHT_GRAY)

    # ---- Couche API ----
    box(ax, 1.5, 5.7, 11.0, 0.7, "COUCHE API",
        fontsize=11, bold=True, dashed=True)

    # Fleches presentation -> API
    arrow(ax, 4.0, 7.2, 4.0, 6.4)
    arrow(ax, 8.0, 7.2, 8.0, 6.4)

    # ---- Couche business ----
    ax.text(0.5, 3.7, "COUCHE BUSINESS\nSERVICE", fontsize=8.5,
            fontweight="bold", va="center")

    # Conteneur business (gauche)
    container(ax, 1.5, 1.7, 5.5, 3.7, dashed=True)
    box(ax, 2.0, 3.0, 4.5, 1.5, "COUCHE BUSINESS\n(orchestration)",
        fontsize=10, bold=True, fill=LIGHT_GRAY)

    # 6 modules a droite
    modules = [
        "MODULE AUTHENTIFICATION",
        "MODULE ONBOARDING SOCIÉTAIRE",
        "MODULE EXTRACTION CNI",
        "MODULE VALIDATION DOSSIER",
        "MODULE NOTIFICATIONS",
        "MODULE AUDIT & CONFORMITÉ",
    ]
    mod_x = 7.5
    mod_w = 4.5
    mod_h = 0.55
    mod_gap = 0.05
    total_h = len(modules) * mod_h + (len(modules) - 1) * mod_gap
    mod_y0 = 1.7 + (3.7 - total_h) / 2
    for i, m in enumerate(modules):
        y = mod_y0 + (len(modules) - 1 - i) * (mod_h + mod_gap)
        box(ax, mod_x, y, mod_w, mod_h, m, fontsize=8.5, bold=True)
        # Petite fleche bidirectionnelle vers la couche business
        line(ax, 6.5, y + mod_h / 2, mod_x, y + mod_h / 2)

    # Fleche API -> business
    arrow(ax, 4.0, 5.7, 4.0, 4.5)
    arrow(ax, 4.0, 4.5, 4.0, 5.7)  # bidirectionnel

    # ---- Base de donnees ----
    ax.text(0.5, 0.7, "BASE DE\nDONNÉES", fontsize=8.5, fontweight="bold", va="center")
    cylinder(ax, 4.0, 0.2, 1.4, 1.2, "", fontsize=9)
    ax.text(4.0, 0.8, "PostgreSQL", ha="center", va="center",
            fontsize=8.5, fontweight="bold")
    # Fleche business -> BD
    arrow(ax, 4.0, 1.7, 4.0, 1.4)
    arrow(ax, 4.0, 1.4, 4.0, 1.7)

    # ---- Systeme externe (colonne droite) ----
    box(ax, 12.7, 1.0, 3.0, 8.0, "", dashed=False, fill=LIGHT_GRAY)
    ax.text(14.2, 8.6, "SYSTÈME EXTERNE",
            ha="center", va="center", fontsize=10, fontweight="bold")

    # Services externes dans la colonne
    ext_services = [
        "WhatsApp Cloud API",
        "Service OCR",
        "Modèle IA (AYA)",
        "SMTP transactionnel",
        "Active Directory",
        "Stockage Azure Blob",
    ]
    ext_y0 = 1.6
    ext_h = 0.7
    ext_gap = 0.2
    for i, name in enumerate(ext_services):
        y = ext_y0 + (len(ext_services) - 1 - i) * (ext_h + ext_gap)
        box(ax, 13.0, y, 2.4, ext_h, name, fontsize=8.5, bold=True, fill="white")

    plt.tight_layout()
    fig.savefig(OUT / "diagram_archi_fonctionnelle.png", dpi=180,
                bbox_inches="tight", facecolor="white")
    plt.close(fig)


# =================================================================== #
# 2. ERD MA2E - Top 5 entites
# =================================================================== #
def make_erd():
    fig, ax = plt.subplots(figsize=(15, 9))
    ax.set_xlim(0, 18)
    ax.set_ylim(0, 11)
    ax.set_axis_off()
    plt.rcParams["font.family"] = "Times New Roman"

    def erd_table(ax, x, y, w, name, attrs):
        """attrs = liste de (nom_col, type, [PK|FK|NN|''])"""
        header_h = 0.35
        row_h = 0.28
        total_h = header_h + len(attrs) * row_h
        # Cadre
        ax.add_patch(mpatches.Rectangle(
            (x, y - total_h), w, total_h,
            linewidth=1.3, edgecolor="black", facecolor="white"))
        # Header (gris)
        ax.add_patch(mpatches.Rectangle(
            (x, y - header_h), w, header_h,
            linewidth=1.3, edgecolor="black", facecolor=LIGHT_GRAY))
        ax.text(x + w / 2, y - header_h / 2, name,
                ha="center", va="center", fontsize=10.5,
                fontweight="bold", color="black")
        # Lignes de separation et attributs
        for i, (col, typ, flag) in enumerate(attrs):
            ry = y - header_h - (i + 1) * row_h
            if i > 0:
                line(ax, x, ry + row_h, x + w, ry + row_h)
            # Colonne gauche : nom + marker PK/FK
            mark = ""
            if "PK" in flag:
                mark = " *"
            elif "FK" in flag:
                mark = " +"
            ax.text(x + 0.1, ry + row_h / 2, f"{col}{mark}",
                    ha="left", va="center", fontsize=8.5,
                    fontweight="bold" if "PK" in flag else "normal")
            # Colonne droite : type
            ax.text(x + w - 0.1, ry + row_h / 2, typ,
                    ha="right", va="center", fontsize=8, style="italic",
                    color="#555555")
        return (x, y - total_h, x + w, y)  # bbox

    ax.text(9, 10.5, "Top 5 des entités métier de MA2E (modèle relationnel)",
            ha="center", fontsize=12, fontweight="bold")
    ax.text(0.3, 9.6, "* = clé primaire   +  = clé étrangère",
            ha="left", fontsize=8.5, style="italic")

    # Table 1 : societaire (centre-haut)
    b1 = erd_table(ax, 7.0, 9.4, 3.6, "societaire", [
        ("id_societaire", "uuid", "PK"),
        ("numero_ma2e", "varchar(20)", ""),
        ("nom", "varchar(80)", "NN"),
        ("prenoms", "varchar(120)", "NN"),
        ("date_naissance", "date", "NN"),
        ("cni_numero", "varchar(20)", ""),
        ("email", "varchar(120)", "NN"),
        ("telephone", "varchar(20)", ""),
        ("id_societe", "int", "FK"),
        ("matricule", "varchar(20)", "NN"),
        ("date_embauche", "date", ""),
        ("statut", "varchar(20)", "NN"),
    ])

    # Table 2 : conversation (gauche-haut)
    b2 = erd_table(ax, 1.0, 9.0, 3.4, "conversation", [
        ("id_conversation", "uuid", "PK"),
        ("id_societaire", "uuid", "FK"),
        ("canal", "varchar(20)", "NN"),
        ("etat_machine", "varchar(40)", "NN"),
        ("contexte", "jsonb", ""),
        ("date_creation", "timestamp", "NN"),
        ("date_dernier_message", "timestamp", ""),
    ])

    # Table 3 : dossier (droite)
    b3 = erd_table(ax, 12.5, 9.4, 3.6, "dossier", [
        ("id_dossier", "uuid", "PK"),
        ("id_societaire", "uuid", "FK"),
        ("statut", "varchar(20)", "NN"),
        ("motif_refus", "varchar(80)", ""),
        ("id_agent_validateur", "uuid", "FK"),
        ("date_soumission", "timestamp", "NN"),
        ("date_validation", "timestamp", ""),
        ("score_extraction", "decimal(4,2)", ""),
    ])

    # Table 4 : piece_identite (gauche-bas)
    b4 = erd_table(ax, 1.5, 4.6, 3.4, "piece_identite", [
        ("id_piece", "uuid", "PK"),
        ("id_dossier", "uuid", "FK"),
        ("type", "varchar(10)", "NN"),
        ("url_stockage", "varchar(200)", "NN"),
        ("donnees_extraites", "jsonb", ""),
        ("score_ocr", "decimal(4,2)", ""),
        ("date_upload", "timestamp", "NN"),
    ])

    # Table 5 : consentement (droite-bas)
    b5 = erd_table(ax, 12.0, 4.6, 3.6, "consentement", [
        ("id_consentement", "uuid", "PK"),
        ("id_societaire", "uuid", "FK"),
        ("texte_signe", "text", "NN"),
        ("signature_hmac", "varchar(64)", "NN"),
        ("horodatage", "timestamp", "NN"),
        ("canal_recueil", "varchar(20)", ""),
    ])

    # Table 6 (bonus) : audit_log (bas centre)
    b6 = erd_table(ax, 7.0, 4.6, 3.6, "audit_log", [
        ("id_audit", "uuid", "PK"),
        ("id_utilisateur", "uuid", "FK"),
        ("action", "varchar(40)", "NN"),
        ("id_objet", "uuid", ""),
        ("ip_source", "varchar(45)", ""),
        ("horodatage", "timestamp", "NN"),
        ("hash_chaine", "varchar(64)", ""),
    ])

    # Liens entre tables (lignes simples, pas de fleches)
    # societaire <-> conversation
    line(ax, 4.4, 8.0, 7.0, 8.0)
    # societaire <-> dossier
    line(ax, 10.6, 8.0, 12.5, 8.0)
    # societaire <-> consentement (lien long via courbe simple)
    line(ax, 9.5, 6.0, 9.5, 5.8)
    line(ax, 9.5, 5.8, 12.0, 5.8)
    line(ax, 9.5, 6.5, 9.5, 6.0)
    # dossier <-> piece_identite
    line(ax, 13.0, 6.0, 13.0, 5.5)
    line(ax, 13.0, 5.5, 4.9, 5.5)
    line(ax, 4.9, 5.5, 4.9, 4.6)
    # societaire <-> audit_log
    line(ax, 8.8, 6.0, 8.8, 4.6)

    plt.tight_layout()
    fig.savefig(OUT / "diagram_entites_metier.png", dpi=180,
                bbox_inches="tight", facecolor="white")
    plt.close(fig)


# =================================================================== #
# 3. Architecture logicielle 1/2 MA2E (style SODECI)
# =================================================================== #
def make_archi_log_1_v2():
    fig, ax = plt.subplots(figsize=(15, 8.5))
    ax.set_xlim(0, 18)
    ax.set_ylim(0, 10)
    ax.set_axis_off()

    # ---- Acteurs (gauche) ----
    box(ax, 0.3, 8.4, 1.6, 0.7, "Administrateur", fontsize=9, bold=True)
    box(ax, 0.3, 5.4, 1.6, 0.7, "Sociétaire", fontsize=9, bold=True)
    box(ax, 0.3, 1.8, 1.6, 0.7, "Agent MA2E", fontsize=9, bold=True)

    # ---- Cas d'utilisation (rounded boxes) ----
    # Administrateur
    rounded_box(ax, 2.5, 8.6, 2.4, 0.6, "Authentification", fontsize=9)
    rounded_box(ax, 2.5, 7.7, 2.4, 0.6, "Gestion utilisateurs\nrôles et sociétés", fontsize=8)
    line(ax, 1.9, 8.7, 2.5, 8.9, dashed=True)
    line(ax, 1.9, 8.7, 2.5, 8.0, dashed=True)

    # Sociétaire
    rounded_box(ax, 2.5, 6.0, 2.4, 0.6, "Onboarding via\nWhatsApp / Web", fontsize=8)
    rounded_box(ax, 2.5, 5.1, 2.4, 0.6, "Questions à AYA", fontsize=9)
    rounded_box(ax, 2.5, 4.2, 2.4, 0.6, "Upload CNI +\nconsentement", fontsize=8)
    line(ax, 1.9, 5.7, 2.5, 6.3, dashed=True)
    line(ax, 1.9, 5.7, 2.5, 5.4, dashed=True)
    line(ax, 1.9, 5.7, 2.5, 4.5, dashed=True)

    # Agent MA2E
    rounded_box(ax, 2.5, 2.4, 2.4, 0.6, "Validation\ndes dossiers", fontsize=8)
    rounded_box(ax, 2.5, 1.5, 2.4, 0.6, "Reporting +\nexports", fontsize=8)
    line(ax, 1.9, 2.1, 2.5, 2.7, dashed=True)
    line(ax, 1.9, 2.1, 2.5, 1.8, dashed=True)

    # ---- Etiquettes HTTPS / JSON ----
    for y in [8.9, 8.0, 6.3, 5.4, 4.5, 2.7, 1.8]:
        ax.text(5.6, y, "HTTPS / JSON",
                ha="center", va="center", fontsize=7,
                bbox=dict(facecolor=LIGHT_GRAY, edgecolor="none", pad=1.5))

    # ---- Conteneur COUCHE METIER ----
    container(ax, 6.6, 1.0, 3.0, 8.5, label="COUCHE METIER")

    # Service Authentification JWT
    rounded_box(ax, 6.9, 8.5, 2.4, 0.6, "Authentification\nJWT + Active Directory",
                fontsize=8)

    # Web Service REST
    container(ax, 6.8, 1.7, 2.7, 6.4, label="Web Service REST")
    services = [
        "Service Conversation",
        "Service Extraction CNI",
        "Service Consentement",
        "Service Validation",
        "Service Notifications",
        "Service Audit",
        "Service Reporting",
    ]
    sv_y0 = 2.1
    sv_h = 0.5
    sv_gap = 0.25
    for i, sv in enumerate(services):
        y = sv_y0 + (len(services) - 1 - i) * (sv_h + sv_gap)
        rounded_box(ax, 6.95, y, 2.4, sv_h, sv, fontsize=8)

    # Fleches usecases -> services
    for sy in [8.9, 8.0, 6.3, 5.4, 4.5, 2.7, 1.8]:
        arrow(ax, 4.9, sy, 6.95, sy if sy < 8.8 else 8.8)

    # ---- Conteneur MODELE DE DONNEE ----
    container(ax, 10.0, 1.0, 2.4, 8.5, label="MODELE DE DONNEE")
    entities = [
        "Utilisateurs",
        "Sociétaires",
        "Conversations",
        "Dossiers",
        "Pièces d'identité",
        "Consentements",
        "Audit log",
    ]
    en_y0 = 1.5
    en_h = 1.0
    en_gap = 0.1
    for i, en in enumerate(entities):
        y = en_y0 + (len(entities) - 1 - i) * (en_h + en_gap)
        cylinder(ax, 11.2, y, 1.6, en_h, en, fontsize=8.5, bold=True)

    # ---- Conteneur BASE DE DONNEES ----
    container(ax, 12.9, 2.0, 3.5, 5.0, label="BASE DE DONNEES")
    cylinder(ax, 13.7, 4.0, 1.4, 1.6, "PostgreSQL\nMaître",
             fontsize=8, bold=True)
    cylinder(ax, 15.5, 4.0, 1.4, 1.6, "PostgreSQL\nRéplica",
             fontsize=8, bold=True)
    # Etiquette replication
    ax.text(14.6, 4.85, "Réplication",
            ha="center", va="center", fontsize=7,
            bbox=dict(facecolor=LIGHT_GRAY, edgecolor="none", pad=1.5))
    line(ax, 14.4, 4.5, 14.8, 4.5)

    # Fleches entites -> BD
    for i in range(len(entities)):
        y = en_y0 + (len(entities) - 1 - i) * (en_h + en_gap) + en_h / 2
        arrow(ax, 12.0, y, 13.0, 4.5)

    # ---- API EXTERNES (colonne droite-bas) ----
    container(ax, 12.9, 0.2, 3.5, 1.4, label="API EXTERNES")
    box(ax, 13.1, 0.4, 1.5, 0.7, "WhatsApp\nCloud API",
        fontsize=7.5, bold=True)
    box(ax, 14.7, 0.4, 1.5, 0.7, "Service OCR\n+ Modèle IA",
        fontsize=7.5, bold=True)

    plt.tight_layout()
    fig.savefig(OUT / "diagram_archi_log_1.png", dpi=180,
                bbox_inches="tight", facecolor="white")
    plt.close(fig)


# =================================================================== #
# 4. Architecture technique 1/2 MA2E (style SODECI : LB + serveurs)
# =================================================================== #
def make_archi_tech_v2():
    fig, ax = plt.subplots(figsize=(14, 9))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 11)
    ax.set_axis_off()

    # ---- Acteurs en haut ----
    box(ax, 1.0, 9.6, 2.8, 0.9, "Sociétaires\n(WhatsApp + Web)",
        fontsize=9, bold=True, fill=LIGHT_GRAY)
    box(ax, 6.0, 9.6, 2.8, 0.9, "Agents MA2E\n(back-office)",
        fontsize=9, bold=True, fill=LIGHT_GRAY)
    box(ax, 11.5, 9.6, 3.0, 0.9, "Service WhatsApp\nCloud API (Meta)",
        fontsize=9, bold=True)

    # Etiquettes de flux
    ax.text(2.4, 9.0, "HTTPS", ha="center", fontsize=8,
            bbox=dict(facecolor=LIGHT_GRAY, edgecolor="none", pad=1.5))
    ax.text(7.4, 9.0, "HTTPS", ha="center", fontsize=8,
            bbox=dict(facecolor=LIGHT_GRAY, edgecolor="none", pad=1.5))
    ax.text(13.0, 9.0, "HTTPS webhook", ha="center", fontsize=8,
            bbox=dict(facecolor=LIGHT_GRAY, edgecolor="none", pad=1.5))

    # ---- Cadre SITE DE PRODUCTION ----
    container(ax, 0.5, 0.5, 15.0, 8.0, label="SITE DE PRODUCTION (Microsoft Azure - région France Centre)")

    # ---- Passerelle d'entree (Load Balancer equivalent) ----
    box(ax, 4.5, 7.2, 6.5, 0.8,
        "Passerelle d'entrée Azure (Application Gateway)\nrépartition de charge + pare-feu applicatif + chiffrement HTTPS",
        fontsize=8.5, bold=True, fill=LIGHT_GRAY)
    ax.text(11.4, 7.6, "1", fontsize=10, fontweight="bold")

    # Fleches acteurs -> passerelle
    arrow(ax, 2.4, 9.6, 5.5, 8.0)
    arrow(ax, 7.4, 9.6, 7.7, 8.0)
    arrow(ax, 13.0, 9.6, 10.5, 8.0)

    # ---- 2 instances Site Web MA2E ----
    box(ax, 1.5, 5.4, 3.8, 1.0, "Site web MA2E (instance 1)\nNext.js conteneurisé",
        fontsize=8.5, bold=True)
    box(ax, 6.0, 5.4, 3.8, 1.0, "Site web MA2E (instance 2)\nNext.js conteneurisé",
        fontsize=8.5, bold=True)
    ax.text(5.3, 6.4, "2", fontsize=10, fontweight="bold")

    # Fleches passerelle -> sites web
    arrow(ax, 6.5, 7.2, 3.4, 6.4)
    arrow(ax, 8.5, 7.2, 7.9, 6.4)

    # ---- Service de notifications ----
    box(ax, 11.0, 5.4, 4.0, 1.0,
        "Service de notifications\n(envoi email + WhatsApp)",
        fontsize=8.5, bold=True)
    ax.text(13.0, 6.4, "3", fontsize=10, fontweight="bold")
    arrow(ax, 11.0, 7.2, 13.0, 6.4)

    # Etiquettes JSON entre couches
    ax.text(3.4, 5.0, "JSON / HTTPS", ha="center", fontsize=7.5,
            bbox=dict(facecolor=LIGHT_GRAY, edgecolor="none", pad=1.5))
    ax.text(7.9, 5.0, "JSON / HTTPS", ha="center", fontsize=7.5,
            bbox=dict(facecolor=LIGHT_GRAY, edgecolor="none", pad=1.5))

    # ---- 2 instances Application serveur MA2E ----
    box(ax, 2.5, 3.5, 4.5, 1.0,
        "Application serveur MA2E (instance 1)\nFastAPI conteneurisée",
        fontsize=8.5, bold=True)
    box(ax, 8.0, 3.5, 4.5, 1.0,
        "Application serveur MA2E (instance 2)\nFastAPI conteneurisée",
        fontsize=8.5, bold=True)
    ax.text(7.2, 4.5, "4", fontsize=10, fontweight="bold")

    arrow(ax, 3.4, 5.4, 4.5, 4.5)
    arrow(ax, 7.9, 5.4, 10.0, 4.5)

    # ---- Base de donnees PostgreSQL Maitre ----
    box(ax, 4.0, 1.7, 4.5, 1.0,
        "Serveur BD Maître PostgreSQL\n(lectures + écritures)",
        fontsize=8.5, bold=True, fill=LIGHT_GRAY)
    ax.text(8.6, 2.7, "5", fontsize=10, fontweight="bold")

    arrow(ax, 4.0, 3.5, 5.0, 2.7)
    arrow(ax, 9.5, 3.5, 7.0, 2.7)

    # Etiquettes socket
    ax.text(4.5, 3.1, "TCP / 5432", ha="center", fontsize=7.5,
            bbox=dict(facecolor=LIGHT_GRAY, edgecolor="none", pad=1.5))
    ax.text(8.0, 3.1, "TCP / 5432", ha="center", fontsize=7.5,
            bbox=dict(facecolor=LIGHT_GRAY, edgecolor="none", pad=1.5))

    # ---- Replica + stockage ----
    box(ax, 9.5, 1.7, 4.0, 1.0,
        "Serveur BD Réplica PostgreSQL\n(lecture seule + sauvegarde)",
        fontsize=8.5, bold=True, fill=LIGHT_GRAY)
    arrow(ax, 8.5, 2.2, 9.5, 2.2)
    ax.text(9.0, 2.45, "Réplication", ha="center", fontsize=7.5)

    # Stockage Azure Blob (sous les serveurs app)
    box(ax, 1.0, 1.7, 2.6, 1.0,
        "Stockage Azure Blob\n(photos CNI, exports)",
        fontsize=8, bold=True, fill=LIGHT_GRAY)
    arrow(ax, 2.5, 3.5, 2.3, 2.7)

    plt.tight_layout()
    fig.savefig(OUT / "diagram_topologie.png", dpi=180,
                bbox_inches="tight", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    make_archi_fonctionnelle()
    make_erd()
    make_archi_log_1_v2()
    make_archi_tech_v2()
    print("OK  4 schemas CVATL v2 generes (style SODECI N&B)")
