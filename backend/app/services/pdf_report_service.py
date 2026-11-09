"""Génération de rapports PDF (US-26 AC4).

Charte v2 (juin 2026) : minimaliste, blanc/gris/noir avec touche de vert pâle
en accent uniquement. Tout est aligné à gauche — pas de centrage, pas de droite.
Inspiration : style éditorial Apple / Notion / Linear.
"""
from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


# ────────────────────────────────────────────────────────────────────────
# Palette — blanc / gris / noir, accent vert pâle uniquement
# ────────────────────────────────────────────────────────────────────────
INK_900 = colors.HexColor("#0F172A")   # texte principal (presque noir)
INK_700 = colors.HexColor("#334155")   # texte secondaire / valeurs
INK_500 = colors.HexColor("#64748B")   # méta, légendes
INK_400 = colors.HexColor("#94A3B8")
INK_300 = colors.HexColor("#CBD5E1")   # bordures
INK_200 = colors.HexColor("#E2E8F0")   # séparateurs fins
INK_100 = colors.HexColor("#F1F5F9")   # fond alterné
INK_50 = colors.HexColor("#F8FAFC")    # fond très léger
WHITE = colors.white

ACCENT = colors.HexColor("#A6CFC5")    # vert pâle (filets, badges)
ACCENT_SOFT = colors.HexColor("#E8F2EE")  # vert ultra léger (fonds)
ACCENT_DEEP = colors.HexColor("#2D5F4F")  # vert foncé (juste pour eyebrow)

DANGER = colors.HexColor("#B91C1C")
WARN = colors.HexColor("#B45309")


def _styles():
    base = getSampleStyleSheet()
    eyebrow = ParagraphStyle(
        "ma2e_eyebrow", fontName="Helvetica-Bold", fontSize=7,
        textColor=ACCENT_DEEP, spaceAfter=4, alignment=TA_LEFT,
        leading=9,
    )
    h1 = ParagraphStyle(
        "ma2e_h1", parent=base["Heading1"], fontName="Helvetica-Bold",
        fontSize=22, leading=26, textColor=INK_900, spaceAfter=6,
        alignment=TA_LEFT,
    )
    meta = ParagraphStyle(
        "ma2e_meta", fontName="Helvetica", fontSize=9, leading=12,
        textColor=INK_500, spaceAfter=18, alignment=TA_LEFT,
    )
    h2 = ParagraphStyle(
        "ma2e_h2", parent=base["Heading2"], fontName="Helvetica-Bold",
        fontSize=11, leading=14, textColor=INK_900,
        spaceBefore=18, spaceAfter=6, alignment=TA_LEFT,
    )
    h2_eyebrow = ParagraphStyle(
        "ma2e_h2_eb", fontName="Helvetica-Bold", fontSize=7,
        textColor=ACCENT_DEEP, spaceBefore=14, spaceAfter=2, alignment=TA_LEFT,
        leading=9,
    )
    body = ParagraphStyle(
        "ma2e_body", fontName="Helvetica", fontSize=9, leading=13,
        textColor=INK_700, spaceAfter=8, alignment=TA_LEFT,
    )
    small = ParagraphStyle(
        "ma2e_small", fontName="Helvetica", fontSize=8, leading=11,
        textColor=INK_500, alignment=TA_LEFT,
    )
    footer = ParagraphStyle(
        "ma2e_footer", fontName="Helvetica", fontSize=7, leading=9,
        textColor=INK_400, alignment=TA_LEFT,
    )
    return {
        "eyebrow": eyebrow, "h1": h1, "meta": meta,
        "h2": h2, "h2_eb": h2_eyebrow,
        "body": body, "small": small, "footer": footer,
    }


def _get(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _fmt_pct(rate: float) -> str:
    return f"{rate * 100:.1f}%"


def _delta_str(deltas: Optional[dict], key: str) -> str:
    if not deltas or key not in deltas:
        return ""
    d = deltas[key]
    pct = d.get("delta_pct")
    if pct is None:
        return ""
    arrow = "↑" if pct > 0 else ("↓" if pct < 0 else "→")
    sign = "+" if pct > 0 else ""
    return f"{arrow} {sign}{pct}%"


# ────────────────────────────────────────────────────────────────────────
# Styles de tableaux génériques (réutilisés partout)
# ────────────────────────────────────────────────────────────────────────
def _table_style_header_light():
    """Header gris très clair, texte foncé, accent en bas. Tout à gauche."""
    return TableStyle([
        # Header
        ("BACKGROUND", (0, 0), (-1, 0), INK_50),
        ("TEXTCOLOR", (0, 0), (-1, 0), INK_900),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, ACCENT),
        # Body
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("TEXTCOLOR", (0, 1), (-1, -1), INK_700),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, INK_50]),
        # Tout à gauche
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        # Bordures discrètes
        ("LINEBELOW", (0, 1), (-1, -2), 0.3, INK_200),
        # Padding généreux
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ])


def render_overview_pdf(
    *,
    overview,
    channels: list,
    reasons: list,
    funnel,
    period_days: int,
) -> bytes:
    """Compose un PDF A4 portrait. Retourne les octets."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=22 * mm, rightMargin=22 * mm,
        topMargin=22 * mm, bottomMargin=20 * mm,
        title="MA2E — Tableau de bord",
        author="MA2E",
    )
    st = _styles()
    story: list = []

    # ────────────────────────────────────────────────────────────────────
    # En-tête éditorial
    # ────────────────────────────────────────────────────────────────────
    story.append(Paragraph("MA2E · TABLEAU DE BORD", st["eyebrow"]))
    story.append(Paragraph("Reporting opérationnel", st["h1"]))
    period_label = (
        f"Période analysée : {period_days} derniers jours &nbsp;·&nbsp; "
        f"Généré le {datetime.now(timezone.utc).strftime('%d/%m/%Y à %Hh%M UTC')}"
    )
    story.append(Paragraph(period_label, st["meta"]))

    # Filet vert pâle de séparation
    sep = Table([[""]], colWidths=[170 * mm], rowHeights=[0.6])
    sep.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), ACCENT)]))
    story.append(sep)
    story.append(Spacer(1, 14))

    # ────────────────────────────────────────────────────────────────────
    # KPI principaux — grille 2 colonnes, libellé + valeur + variation
    # Tout aligné à gauche, valeurs en gros mais à gauche aussi
    # ────────────────────────────────────────────────────────────────────
    story.append(Paragraph("INDICATEURS CLÉS", st["h2_eb"]))
    story.append(Paragraph("Vue d'ensemble de la période", st["h2"]))

    def _kpi_cell(label: str, value: str, delta_key: Optional[str]):
        delta = _delta_str(overview.deltas, delta_key) if delta_key else ""
        delta_color_hex = "#64748B"  # INK_500
        if delta:
            if delta.startswith("↑"):
                delta_color_hex = "#16A34A"
            elif delta.startswith("↓"):
                delta_color_hex = "#B91C1C"
        delta_html = (
            f'<br/><font size="7" color="{delta_color_hex}">'
            f'{delta} vs période précédente</font>'
        ) if delta else ""
        return Paragraph(
            f'<font size="7" color="#64748B"><b>{label.upper()}</b></font><br/>'
            f'<font size="16" color="#0F172A"><b>{value}</b></font>'
            f'{delta_html}',
            st["small"],
        )

    kpis = [
        ("Total dossiers", str(overview.total_period), "total_period"),
        ("Validés", str(overview.validated), "validated_period"),
        ("Refusés", str(overview.rejected), "rejected_period"),
        ("Taux de validation", _fmt_pct(overview.validation_rate), "validation_rate"),
        ("Temps moyen validation",
         f"{overview.avg_validation_hours} h" if overview.avg_validation_hours else "—",
         None),
        ("Auto-complétion", _fmt_pct(overview.auto_complete_rate), None),
        ("Conversations démarrées", str(overview.total_conversations), "total_conversations"),
        ("Messages échangés", str(overview.total_messages), "total_messages"),
    ]
    # 2 colonnes × 4 lignes
    grid_rows = []
    for i in range(0, len(kpis), 2):
        left = _kpi_cell(*kpis[i])
        right = _kpi_cell(*kpis[i + 1]) if i + 1 < len(kpis) else ""
        grid_rows.append([left, right])

    kpi_grid = Table(grid_rows, colWidths=[83 * mm, 83 * mm])
    kpi_grid.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("BOX", (0, 0), (-1, -1), 0.4, INK_200),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, INK_200),
        ("BACKGROUND", (0, 0), (-1, -1), WHITE),
    ]))
    story.append(kpi_grid)

    # ────────────────────────────────────────────────────────────────────
    # Alertes KPI
    # ────────────────────────────────────────────────────────────────────
    story.append(Paragraph("SURVEILLANCE", st["h2_eb"]))
    story.append(Paragraph("Alertes KPI", st["h2"]))

    if overview.alerts:
        rows = [["Indicateur", "Valeur", "Opérateur", "Seuil", "Sévérité"]]
        for a in overview.alerts:
            sev = (a.get("severity") or "warning").upper()
            rows.append([
                str(a.get("kpi") or ""),
                str(a.get("value") or ""),
                str(a.get("op", "<")),
                str(a.get("threshold") or ""),
                sev,
            ])
        alert_table = Table(
            rows,
            colWidths=[60 * mm, 28 * mm, 22 * mm, 28 * mm, 28 * mm],
        )
        style = _table_style_header_light()
        # Colorer la cellule sévérité selon le niveau
        for idx, a in enumerate(overview.alerts, start=1):
            sev = (a.get("severity") or "warning").lower()
            color = DANGER if sev == "critical" else WARN
            style.add("TEXTCOLOR", (4, idx), (4, idx), color)
            style.add("FONTNAME", (4, idx), (4, idx), "Helvetica-Bold")
        alert_table.setStyle(style)
        story.append(alert_table)
    else:
        story.append(Paragraph(
            "Aucune alerte sur la période. Tous les indicateurs sont "
            "dans les seuils configurés.",
            st["body"],
        ))

    # ────────────────────────────────────────────────────────────────────
    # Entonnoir de conversion
    # ────────────────────────────────────────────────────────────────────
    story.append(Paragraph("PARCOURS UTILISATEUR", st["h2_eb"]))
    story.append(Paragraph("Entonnoir de conversion", st["h2"]))

    funnel_rows = [
        ["Étape", "Volume", "Taux de conversion"],
        ["Conversations démarrées", str(funnel.conversations_started), "100,0 %"],
        ["Dossiers initiés", str(funnel.dossiers_created),
         f"{funnel.started_to_created_pct} %"],
        ["Soumis pour validation", str(funnel.dossiers_submitted),
         f"{funnel.created_to_submitted_pct} %"],
        ["Validés", str(funnel.dossiers_validated),
         f"{funnel.submitted_to_validated_pct} %"],
        ["Conversion globale", "", f"{funnel.overall_pct} %"],
    ]
    funnel_table = Table(funnel_rows, colWidths=[90 * mm, 38 * mm, 38 * mm])
    style = _table_style_header_light()
    # Dernière ligne mise en valeur (fond vert très pâle + bold)
    last = len(funnel_rows) - 1
    style.add("BACKGROUND", (0, last), (-1, last), ACCENT_SOFT)
    style.add("FONTNAME", (0, last), (-1, last), "Helvetica-Bold")
    style.add("TEXTCOLOR", (0, last), (-1, last), INK_900)
    style.add("LINEABOVE", (0, last), (-1, last), 0.8, ACCENT)
    funnel_table.setStyle(style)
    story.append(funnel_table)

    # ────────────────────────────────────────────────────────────────────
    # Répartition par canal
    # ────────────────────────────────────────────────────────────────────
    if channels:
        story.append(Paragraph("CANAUX", st["h2_eb"]))
        story.append(Paragraph("Répartition par canal", st["h2"]))

        ch_rows = [["Canal", "Dossiers", "Conversations", "Part"]]
        for c in channels:
            label = _get(c, "channel") or "—"
            ch_rows.append([
                str(label).capitalize(),
                str(_get(c, "dossiers", 0)),
                str(_get(c, "conversations", 0)),
                f"{_get(c, 'share_pct', 0)} %",
            ])
        ch_table = Table(
            ch_rows,
            colWidths=[48 * mm, 36 * mm, 46 * mm, 36 * mm],
        )
        ch_table.setStyle(_table_style_header_light())
        story.append(ch_table)

    # ────────────────────────────────────────────────────────────────────
    # Top motifs de refus
    # ────────────────────────────────────────────────────────────────────
    if reasons:
        story.append(Paragraph("QUALITÉ DOSSIERS", st["h2_eb"]))
        story.append(Paragraph("Principaux motifs de refus", st["h2"]))

        r_rows = [["Rang", "Motif", "Occurrences", "Part"]]
        for i, r in enumerate(reasons, 1):
            r_rows.append([
                str(i),
                _get(r, "motive") or "—",
                str(_get(r, "count", 0)),
                f"{_get(r, 'share_pct', 0)} %",
            ])
        r_table = Table(
            r_rows,
            colWidths=[14 * mm, 96 * mm, 28 * mm, 28 * mm],
        )
        r_table.setStyle(_table_style_header_light())
        story.append(r_table)

    # ────────────────────────────────────────────────────────────────────
    # Pied de page
    # ────────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 20))
    foot_sep = Table([[""]], colWidths=[170 * mm], rowHeights=[0.4])
    foot_sep.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), INK_200)]))
    story.append(foot_sep)
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "MA2E · Mutuelle des Agents de l'Eau et de l'Électricité — Groupe GS2E. "
        "Document généré automatiquement par la plateforme d'identification. "
        "Diffusion interne uniquement.",
        st["footer"],
    ))

    doc.build(story)
    buf.seek(0)
    return buf.getvalue()
