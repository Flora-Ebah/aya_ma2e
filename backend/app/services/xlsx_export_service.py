"""Génération de fichiers Excel `.xlsx` stylés (US-25).

Charte : blanc/gris/noir, accent vert pâle uniquement, tout aligné à gauche.
Utilise openpyxl (déjà en dépendance pour l'importer).
"""
from __future__ import annotations

import io
from datetime import datetime
from typing import Any, Iterable

from openpyxl import Workbook
from openpyxl.styles import (
    Alignment,
    Border,
    Font,
    PatternFill,
    Side,
)
from openpyxl.utils import get_column_letter


# ────────────────────────────────────────────────────────────────────────
# Palette (alignée sur le PDF — blanc / gris / accent vert pâle)
# ────────────────────────────────────────────────────────────────────────
INK_900 = "FF0F172A"   # texte principal
INK_700 = "FF334155"   # texte body
INK_500 = "FF64748B"   # méta
INK_200 = "FFE2E8F0"   # bordures
INK_50 = "FFF8FAFC"    # zébré
WHITE = "FFFFFFFF"
ACCENT_DEEP = "FF2D5F4F"   # vert foncé pour eyebrow
ACCENT = "FFA6CFC5"        # vert pâle (filets)
ACCENT_SOFT = "FFE8F2EE"   # vert ultra léger (fond header)


# Styles réutilisables
LEFT_ALIGN = Alignment(horizontal="left", vertical="center", wrap_text=False)
LEFT_ALIGN_WRAP = Alignment(horizontal="left", vertical="top", wrap_text=True)
TITLE_FONT = Font(name="Calibri", size=18, bold=True, color=INK_900)
EYEBROW_FONT = Font(name="Calibri", size=8, bold=True, color=ACCENT_DEEP)
META_FONT = Font(name="Calibri", size=10, color=INK_500)
HEADER_FONT = Font(name="Calibri", size=10, bold=True, color=INK_900)
BODY_FONT = Font(name="Calibri", size=10, color=INK_700)
BODY_FONT_STRONG = Font(name="Calibri", size=10, bold=True, color=INK_900)

HEADER_FILL = PatternFill("solid", fgColor=ACCENT_SOFT)
ZEBRA_FILL = PatternFill("solid", fgColor=INK_50)

THIN_BORDER_BOTTOM = Border(bottom=Side(style="thin", color=INK_200))
ACCENT_BORDER_BOTTOM = Border(bottom=Side(style="medium", color=ACCENT))


def _apply_left_align(cell, *, strong: bool = False, wrap: bool = False) -> None:
    cell.alignment = LEFT_ALIGN_WRAP if wrap else LEFT_ALIGN
    cell.font = BODY_FONT_STRONG if strong else BODY_FONT


def _autosize_columns(ws, max_widths: dict[int, int] | None = None) -> None:
    """Ajuste la largeur des colonnes au contenu (cap raisonnable)."""
    widths: dict[int, int] = {}
    for row in ws.iter_rows(values_only=False):
        for cell in row:
            if cell.value is None:
                continue
            text = str(cell.value)
            w = len(text) + 2
            widths[cell.column] = max(widths.get(cell.column, 10), w)
    cap_default = 45
    for col_idx, w in widths.items():
        cap = (max_widths or {}).get(col_idx, cap_default)
        ws.column_dimensions[get_column_letter(col_idx)].width = min(w, cap)


def render_dossiers_xlsx(
    rows: list[dict],
    *,
    period_label: str = "Tous statuts",
    filters_summary: str = "",
) -> bytes:
    """Construit un classeur Excel stylé des dossiers exportés.

    `rows` est une liste de dict avec les clés des colonnes (cf. export_dossiers).
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Sociétaires MA2E"

    # Couleur d'onglet (vert pâle)
    ws.sheet_properties.tabColor = "A6CFC5"

    # ─── En-tête éditorial (lignes 1 → 4) ─────────────────────────────
    ws["A1"] = "MA2E · EXPORT SOCIÉTAIRES"
    ws["A1"].font = EYEBROW_FONT
    ws["A1"].alignment = LEFT_ALIGN
    ws.row_dimensions[1].height = 16

    ws["A2"] = "Liste des dossiers identifiés"
    ws["A2"].font = TITLE_FONT
    ws["A2"].alignment = LEFT_ALIGN
    ws.row_dimensions[2].height = 26

    meta = (
        f"{period_label} · Généré le "
        f"{datetime.utcnow().strftime('%d/%m/%Y à %Hh%M UTC')}"
    )
    if filters_summary:
        meta += f" · Filtres : {filters_summary}"
    ws["A3"] = meta
    ws["A3"].font = META_FONT
    ws["A3"].alignment = LEFT_ALIGN
    ws.row_dimensions[3].height = 14

    # Ligne 4 = filet vert pâle
    ws.row_dimensions[4].height = 4
    for col in range(1, 18):
        c = ws.cell(row=4, column=col)
        c.fill = PatternFill("solid", fgColor=ACCENT)

    # ─── Header de tableau (ligne 6) ──────────────────────────────────
    HEADER_ROW = 6
    headers = [
        "N° sociétaire",
        "N° dossier",
        "Nom",
        "Prénoms",
        "Date naissance",
        "N° CNI",
        "Société",
        "Matricule",
        "Fonction",
        "Ancienneté (années)",
        "Situation familiale",
        "Ayants droit",
        "Téléphone",
        "Email",
        "Date soumission",
        "Date validation",
        "Statut",
    ]
    for col_idx, h in enumerate(headers, start=1):
        c = ws.cell(row=HEADER_ROW, column=col_idx, value=h)
        c.font = HEADER_FONT
        c.fill = HEADER_FILL
        c.alignment = LEFT_ALIGN
        c.border = ACCENT_BORDER_BOTTOM
    ws.row_dimensions[HEADER_ROW].height = 22

    # ─── Lignes de données (ligne 7 →) ────────────────────────────────
    keys = [
        "numero_societaire",
        "numero_dossier",
        "nom",
        "prenoms",
        "date_naissance",
        "numero_cni",
        "societe_code",
        "matricule",
        "fonction",
        "anciennete_annees",
        "situation_familiale",
        "nombre_ayants_droit",
        "telephone",
        "email",
        "date_soumission",
        "date_validation",
        "statut",
    ]
    for r_idx, row in enumerate(rows, start=HEADER_ROW + 1):
        zebra = (r_idx - HEADER_ROW) % 2 == 0
        for c_idx, key in enumerate(keys, start=1):
            value = row.get(key, "")
            cell = ws.cell(row=r_idx, column=c_idx, value=value)
            cell.alignment = LEFT_ALIGN
            # Première colonne (N° sociétaire) en gras pour repère visuel
            cell.font = BODY_FONT_STRONG if c_idx == 1 else BODY_FONT
            cell.border = THIN_BORDER_BOTTOM
            if zebra:
                cell.fill = ZEBRA_FILL
        ws.row_dimensions[r_idx].height = 18

    # ─── Mise en forme finale ─────────────────────────────────────────
    # Auto-fit colonnes, avec cap par colonne (l'email peut être long, etc.)
    _autosize_columns(ws, max_widths={
        3: 28, 4: 32, 14: 35, 9: 30, 11: 22,
    })

    # Fige les en-têtes (titre + header tableau)
    ws.freeze_panes = "A7"

    # Filtre auto sur les colonnes (clic sur la flèche dans Excel)
    last_col = get_column_letter(len(headers))
    last_row = HEADER_ROW + len(rows)
    ws.auto_filter.ref = f"A{HEADER_ROW}:{last_col}{max(last_row, HEADER_ROW)}"

    # Export bytes
    out = io.BytesIO()
    wb.save(out)
    out.seek(0)
    return out.getvalue()
