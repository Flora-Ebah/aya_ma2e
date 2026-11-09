"""Génère un compte-rendu hebdomadaire MA2E au format Excel stylé.

Charte : blanc / gris / accent vert pâle, tout aligné à gauche.
"""
from __future__ import annotations
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter


# ─── Palette ───────────────────────────────────────────────────────────
INK_900 = "FF0F172A"
INK_700 = "FF334155"
INK_500 = "FF64748B"
INK_200 = "FFE2E8F0"
INK_50 = "FFF8FAFC"
ACCENT_DEEP = "FF2D5F4F"
ACCENT = "FFA6CFC5"
ACCENT_SOFT = "FFE8F2EE"

LEFT_TOP = Alignment(horizontal="left", vertical="top", wrap_text=True)
LEFT_CENTER = Alignment(horizontal="left", vertical="center", wrap_text=False)

TITLE_FONT = Font(name="Calibri", size=18, bold=True, color=INK_900)
EYEBROW_FONT = Font(name="Calibri", size=8, bold=True, color=ACCENT_DEEP)
META_FONT = Font(name="Calibri", size=10, color=INK_500)
HEADER_FONT = Font(name="Calibri", size=10, bold=True, color=INK_900)
DAY_FONT = Font(name="Calibri", size=11, bold=True, color=INK_900)
BODY_FONT = Font(name="Calibri", size=10, color=INK_700)

HEADER_FILL = PatternFill("solid", fgColor=ACCENT_SOFT)
DAY_FILL = PatternFill("solid", fgColor=INK_50)
ACCENT_FILL = PatternFill("solid", fgColor=ACCENT)

THIN_BOTTOM = Border(bottom=Side(style="thin", color=INK_200))
ACCENT_BOTTOM = Border(bottom=Side(style="medium", color=ACCENT))


# ─── Données : semaine du 15 au 19 juin 2026 ───────────────────────────
SEMAINE = [
    {
        "date": "Lundi 15 juin 2026",
        "categorie": "Architecture & livrables",
        "taches": [
            ("Diagrammes d'architecture",
             "Régénération des diagrammes BPMN, Architecture Fonctionnelle, "
             "Architecture Logicielle 1/2 et 2/2, Architecture Technique 1/2 et 2/2 "
             "avec contraintes visuelles (flèches droites, libellés français, bordures carrées)."),
            ("Diagramme entités métier",
             "Modélisation du TOP 5 des entités : sociétaires, dossiers, conversations, "
             "utilisateurs, employeurs avec relations FK et tables de référence."),
            ("Cahier des charges v1",
             "Mise à jour du cahier des charges MA2E_Cahier_des_Charges_v1.docx "
             "avec les exigences fonctionnelles et non-fonctionnelles consolidées."),
        ],
    },
    {
        "date": "Mardi 16 juin 2026",
        "categorie": "Workflow conversationnel dynamique",
        "taches": [
            ("Suppression workflow hardcodé",
             "Retrait complet du state_machine.py et intent_router.py. "
             "Bascule sur le moteur workflow_executor.py lisant les étapes depuis la BDD."),
            ("Refonte workflow inscription",
             "Restructuration du parcours d'inscription pour intégrer les 23 champs "
             "du formulaire officiel MA2E (migrate_inscription_23_fields.py)."),
            ("Sous-flux de correction",
             "Création du sous-flux correction (ask_what_to_correct + 4 étapes correct_*) "
             "permettant au sociétaire de modifier ses données après extraction OCR."),
            ("Fix workflow manual_review",
             "Correction du bug où manual_review enchaînait à tort sur 'inscription validée'. "
             "Rendu terminal (type=message, next=None)."),
        ],
    },
    {
        "date": "Mercredi 17 juin 2026",
        "categorie": "Intégrations IA & OCR",
        "taches": [
            ("Intégration Azure OpenAI",
             "Branchement du chat conversationnel sur Azure OpenAI (modèle gpt-5.4-mini) "
             "avec gestion des erreurs et fallback en mode dégradé."),
            ("OCR multi-provider",
             "Pipeline OCR dynamique : Azure AI Vision en production, OCR.space en recette, "
             "compression Pillow préalable (limite 1 Mo OCR.space). Configurable depuis l'admin."),
            ("Action create_real_dossier",
             "Implémentation de l'action workflow qui crée réellement le dossier en BDD "
             "avec attachement des PieceIdentite (recto_media_url + verso_media_url) et "
             "résolution employeur via digit → code."),
            ("Notifications email + WhatsApp",
             "Branchement SMTP réel + WhatsApp Cloud API pour notifier le sociétaire à "
             "chaque étape clé (soumission, complément, validation, rejet)."),
            ("Initial commit backend",
             "Premier commit du backend autonome sur le repo dédié (FastAPI, workflow "
             "dynamique, OCR, conformité ARTCI)."),
        ],
    },
    {
        "date": "Jeudi 18 juin 2026",
        "categorie": "RBAC & déploiement",
        "taches": [
            ("Rôle viewer (lecture seule)",
             "Création du rôle viewer avec migration enum user_role + user de démo "
             "viewer@ma2e.ci. Permissions : read=True sur tous les modules."),
            ("Filtrage sidebar par permission",
             "Sidebar dynamique : requête /api/me au montage, filtrage des NavGroup selon "
             "permissions.module.read. Un agent sans accès reporting ne voit plus ce module."),
            ("Endpoint /api/me",
             "Création de l'endpoint qui renvoie le profil + les permissions agrégées du "
             "user courant (super_admin/tenant_admin/viewer/agent)."),
            ("Dockerisation frontend",
             "Création du Dockerfile multi-stage (deps/builder/runner) avec output:standalone "
             "et NEXT_PUBLIC_API_URL en build-arg."),
            ("Seed automatisé",
             "Script seed_all.py orchestrant 18 étapes (12 migrations + seed principal + "
             "3 restructures workflow + migration viewer + user viewer). Idempotent."),
            ("Push initial backend + frontend",
             "Push initial sur les repos Azure DevOps backend et frontend, avec "
             ".gitignore par sous-dossier pour ne pas exposer les .env."),
        ],
    },
    {
        "date": "Vendredi 19 juin 2026",
        "categorie": "Exports, sécurité webhook & polish UI",
        "taches": [
            ("Refonte design PDF reporting",
             "Refonte complète du PDF /api/stats/overview.pdf : charte blanc/gris/vert pâle, "
             "tout aligné à gauche, KPI en grille 2×4, headers de tableau légers."),
            ("Nouvel export Excel stylé",
             "Création de /api/dossiers/export.xlsx en remplacement du CSV brut. "
             "Mise en forme openpyxl : header vert pâle, zébré, auto-filtre, en-tête figé, "
             "première colonne en gras (xlsx_export_service.py)."),
            ("Token JWT en query string",
             "Modification de get_auth_context pour accepter ?token= en fallback du header "
             "Authorization. Indispensable pour les téléchargements ouverts via <a href>."),
            ("Fix alertes reporting fantômes",
             "stats_service.py : skip silencieux des alertes KPI 'taux' quand le "
             "dénominateur = 0 (évite les CRITIQUE sur base vide)."),
            ("Configuration nginx HTTPS",
             "Ajout du bloc location /webhooks/ dans la config nginx Azure pour router "
             "Meta WhatsApp vers le backend port 8000 au lieu du frontend (404 résolu)."),
            ("Validation webhook Meta",
             "Test bout-en-bout du verify token WhatsApp : URL HTTPS validée par Meta "
             "for Developers, abonnement aux events 'messages' activé."),
            ("Login épuré + anti-autofill",
             "Vidage des champs identifiants par défaut, bouton AD désactivé en bordure "
             "pointillée (badge 'bientôt'), 3 couches anti-autofill (honeypots + "
             "data-lpignore + autoComplete=new-password)."),
            ("Chat page redesign",
             "Réduction à 2 cards (M'identifier + Vérification) centrées verticalement, "
             "suppression Aide rapide, input compact (28px), icône upload personnalisée, "
             "bouton fermer rouge en mode chat, messages naturels (Bonjour, je souhaite...) "
             "au lieu des commandes /identification."),
            ("Push final + déploiement Azure",
             "Push backend + frontend, rebuild des containers Docker côté DevOps avec "
             "NEXT_PUBLIC_API_URL=https://ma2e.swedencentral.cloudapp.azure.com."),
        ],
    },
]


def build_compte_rendu(output_path: Path) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "Semaine 15-19 juin 2026"
    ws.sheet_properties.tabColor = "A6CFC5"

    # ─── En-tête éditorial ────────────────────────────────────────────
    ws["A1"] = "MA2E · COMPTE-RENDU HEBDOMADAIRE"
    ws["A1"].font = EYEBROW_FONT
    ws["A1"].alignment = LEFT_CENTER
    ws.row_dimensions[1].height = 16

    ws["A2"] = "Semaine du 15 au 19 juin 2026"
    ws["A2"].font = TITLE_FONT
    ws["A2"].alignment = LEFT_CENTER
    ws.row_dimensions[2].height = 26

    ws["A3"] = (
        "Plateforme MA2E — Mutuelle des Agents de l'Eau et de l'Électricité · "
        "Groupe GS2E · Phase POC"
    )
    ws["A3"].font = META_FONT
    ws["A3"].alignment = LEFT_CENTER
    ws.row_dimensions[3].height = 14

    # Filet vert pâle (ligne 4)
    ws.row_dimensions[4].height = 4
    for col in range(1, 5):
        ws.cell(row=4, column=col).fill = ACCENT_FILL

    # ─── Header tableau (ligne 6) ─────────────────────────────────────
    HEADER_ROW = 6
    headers = ["Jour", "Catégorie", "Tâche", "Description"]
    widths = [22, 30, 35, 75]
    for col_idx, (h, w) in enumerate(zip(headers, widths), start=1):
        c = ws.cell(row=HEADER_ROW, column=col_idx, value=h)
        c.font = HEADER_FONT
        c.fill = HEADER_FILL
        c.alignment = LEFT_CENTER
        c.border = ACCENT_BOTTOM
        ws.column_dimensions[get_column_letter(col_idx)].width = w
    ws.row_dimensions[HEADER_ROW].height = 22

    # ─── Lignes de données ────────────────────────────────────────────
    current_row = HEADER_ROW + 1
    for jour in SEMAINE:
        first_row = current_row
        for i, (tache, description) in enumerate(jour["taches"]):
            # Colonne 1 : Jour (seulement sur la 1re ligne du bloc)
            if i == 0:
                cell = ws.cell(row=current_row, column=1, value=jour["date"])
                cell.font = DAY_FONT
                cell.fill = DAY_FILL
                cell.alignment = LEFT_TOP
                # Colonne 2 : catégorie (seulement sur la 1re ligne)
                cat = ws.cell(row=current_row, column=2, value=jour["categorie"])
                cat.font = Font(name="Calibri", size=10, bold=True, color=ACCENT_DEEP)
                cat.fill = DAY_FILL
                cat.alignment = LEFT_TOP
            else:
                # Cellules vides pour les lignes suivantes du bloc
                ws.cell(row=current_row, column=1).fill = DAY_FILL
                ws.cell(row=current_row, column=2).fill = DAY_FILL

            # Colonne 3 : Tâche
            t = ws.cell(row=current_row, column=3, value=tache)
            t.font = Font(name="Calibri", size=10, bold=True, color=INK_900)
            t.alignment = LEFT_TOP
            t.border = THIN_BOTTOM

            # Colonne 4 : Description
            d = ws.cell(row=current_row, column=4, value=description)
            d.font = BODY_FONT
            d.alignment = LEFT_TOP
            d.border = THIN_BOTTOM

            ws.row_dimensions[current_row].height = max(38, 16 + len(description) // 5)
            current_row += 1

        # Bordure basse renforcée pour séparer les jours
        last_row = current_row - 1
        for col in range(1, 5):
            c = ws.cell(row=last_row, column=col)
            c.border = Border(bottom=Side(style="medium", color=ACCENT))

    # Fusionner verticalement les cellules "Jour" et "Catégorie" pour la lisibilité
    current_row = HEADER_ROW + 1
    for jour in SEMAINE:
        n = len(jour["taches"])
        if n > 1:
            ws.merge_cells(
                start_row=current_row, start_column=1,
                end_row=current_row + n - 1, end_column=1,
            )
            ws.merge_cells(
                start_row=current_row, start_column=2,
                end_row=current_row + n - 1, end_column=2,
            )
        current_row += n

    # Geler les en-têtes
    ws.freeze_panes = f"A{HEADER_ROW + 1}"

    # ─── Pied : récapitulatif ─────────────────────────────────────────
    summary_row = current_row + 2
    total_taches = sum(len(j["taches"]) for j in SEMAINE)

    ws.cell(row=summary_row, column=1, value="RÉCAPITULATIF").font = EYEBROW_FONT
    ws.cell(row=summary_row + 1, column=1, value=f"Jours travaillés : 5").font = META_FONT
    ws.cell(row=summary_row + 2, column=1, value=f"Tâches livrées : {total_taches}").font = META_FONT
    ws.cell(row=summary_row + 3, column=1, value="Catégories : Architecture, Workflow, IA/OCR, RBAC, Déploiement, UX").font = META_FONT
    ws.cell(row=summary_row + 4, column=1, value="État : Plateforme opérationnelle en recette Azure — webhooks WhatsApp validés Meta.").font = META_FONT

    wb.save(output_path)
    return output_path


if __name__ == "__main__":
    out = Path(__file__).parent / "MA2E_Compte_Rendu_Semaine_15-19_juin_2026.xlsx"
    saved = build_compte_rendu(out)
    print(f"Fichier généré : {saved}")
    print(f"Taille : {saved.stat().st_size} octets")
