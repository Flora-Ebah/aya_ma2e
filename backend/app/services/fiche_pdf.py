"""Génération de la Fiche d'inscription sociétaire par overlay sur le template PDF.

Le template vierge (app/assets/fiche_template.pdf) n'est JAMAIS modifié.
On construit un calque transparent via reportlab, puis on le fusionne sur le
template avec pypdf. Les coordonnées (x, y) sont en points PDF natifs
(origine bas-gauche) et ont été relevées directement sur le template.

Règle d'or : si une donnée manque en base, on laisse la case vide.
"""
from __future__ import annotations

import io
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import letter  # noqa: F401 — placeholder pour cohérence
from reportlab.pdfgen import canvas

from app.models import Dossier

logger = logging.getLogger(__name__)

TEMPLATE_PATH = Path(__file__).resolve().parents[1] / "assets" / "fiche_template.pdf"
PAGE_WIDTH = 695.0
PAGE_HEIGHT = 842.0

# Configuration des positions. Chaque entrée : (x, y, max_width).
# y = ligne de base du texte en coordonnées PDF (0 = bas) : c'est EXACTEMENT la
# ligne de base du libellé correspondant dans le template (relevée avec PyMuPDF),
# pour que valeur et libellé soient alignés comme sur la fiche Perfect Vision
# de référence. Les x (141 / 464 / 326) sont ceux de cette fiche de référence.
LEFT_X = 141.0
LEFT_W = 195.0
RIGHT_X = 464.0
RIGHT_W = 220.0
TABLE_X = 326.0
TABLE_W = 355.0
FONT_SIZE = 10.0          # même corps que les libellés du template
OBS_LINE_HEIGHT = 12.6    # interligne des observations multi-lignes (fiche de référence)

# Champ → (x, y, max_w)
POSITIONS: dict[str, tuple[float, float, float]] = {
    # En-tête (coin haut droit) — à droite des libellés « Imprimé le : » etc.
    "imprime_le":    (507, 813.6, 180),
    "imprime_par":   (507, 801.6, 180),
    "journee":       (507, 789.6, 180),

    # Code / Numéro manuel (ligne du dessus)
    "code":          (140, 736.7, 250),
    "numero_manuel": (507, 736.7, 180),

    # Colonne gauche
    "type_client":     (LEFT_X, 708.7, LEFT_W),
    "civilite":        (LEFT_X, 686.7, LEFT_W),
    "nom":             (LEFT_X, 664.7, LEFT_W),
    "prenoms":         (LEFT_X, 642.7, LEFT_W),
    "situation_matri": (LEFT_X, 620.7, LEFT_W),
    "date_naissance":  (LEFT_X, 598.7, LEFT_W),
    "lieu_naissance":  (LEFT_X, 576.7, LEFT_W),
    "piece_identite":  (LEFT_X, 554.7, LEFT_W),
    "num_piece":       (LEFT_X, 532.7, LEFT_W),
    "domicile":        (LEFT_X, 510.7, LEFT_W),
    "boite_postale":   (LEFT_X, 488.7, LEFT_W),
    "telephone":       (LEFT_X, 466.7, LEFT_W),
    "email":           (LEFT_X, 444.7, LEFT_W),
    "situation_geo":   (LEFT_X, 422.7, LEFT_W),
    "distance_agence": (LEFT_X, 400.7, LEFT_W),
    "profession":      (LEFT_X, 378.7, LEFT_W),
    "nom_conjoint":    (LEFT_X, 356.7, LEFT_W),
    "nom_prevenir":    (LEFT_X, 334.7, LEFT_W),

    # Colonne droite
    "num_compte":      (RIGHT_X, 581.7, RIGHT_W),
    "adr_prevenir":    (RIGHT_X, 561.7, RIGHT_W),
    "beneficiaire":    (RIGHT_X, 538.7, RIGHT_W),
    "tuteur":          (RIGHT_X, 515.7, RIGHT_W),
    "ayant_droit":     (RIGHT_X, 492.7, RIGHT_W),
    "nb_signatures":   (RIGHT_X, 470.7, RIGHT_W),
    "date_inscription":(RIGHT_X, 428.7, RIGHT_W),
    "gestionnaire":    (RIGHT_X, 406.7, RIGHT_W),
    "nom_tuteur":      (RIGHT_X, 384.7, RIGHT_W),
    "observations":    (RIGHT_X, 360.7, RIGHT_W),   # jusqu'à 2 lignes (voir _text_multiline)

    # Table Attribut / Valeur
    "cat_val":         (TABLE_X, 278.7, TABLE_W),
    "emp_val":         (TABLE_X, 258.7, TABLE_W),
    "cons_val":        (TABLE_X, 238.7, TABLE_W),
    "mere_val":        (TABLE_X, 218.7, TABLE_W),
}
HEADER_KEYS = {"imprime_le", "imprime_par", "journee"}  # restent en 9 pt comme l'en-tête du template

# Zone photo (encadré) : x=[455..680], y=[620..720] approximativement
# Cadre photo du template : x=441, y=632, 101 x 88 (relevé avec PyMuPDF) → 2 pt de marge intérieure.
# (L'ancienne zone 455/620/100x100 débordait du cadre à droite et en bas.)
PHOTO_BOX = (443, 634, 97, 84)  # x, y, w, h

# Cadre bas du template : x=143..532, y=57..145, coupé en deux (VISA | Date et signature du client).
# Zone signature = moitié droite, sous le libellé (l'ancienne zone y=50 sortait sous le cadre).
SIGNATURE_BOX = (342, 60, 186, 68)


def _fit(c: canvas.Canvas, s: str, max_w: float, font_size: float) -> str:
    """Tronque avec « … » si le texte dépasse la largeur max (évite de déborder sur la colonne voisine)."""
    while c.stringWidth(s, "Helvetica", font_size) > max_w and len(s) > 4:
        s = s[:-2] + "…"
    return s


def _text(c: canvas.Canvas, key: str, value: Optional[str], font_size: Optional[float] = None) -> None:
    """Écrit un texte à la position du champ, en respectant la largeur max."""
    if value is None:
        return
    s = str(value).strip()
    if not s:
        return
    pos = POSITIONS.get(key)
    if not pos:
        logger.warning("fiche_pdf: position inconnue pour '%s'", key)
        return
    x, y, max_w = pos
    size = font_size or (9.0 if key in HEADER_KEYS else FONT_SIZE)
    c.setFont("Helvetica", size)
    c.drawString(x, y, _fit(c, s, max_w, size))


def _text_multiline(c: canvas.Canvas, key: str, value: Optional[str], max_lines: int = 2) -> None:
    """Comme `_text` mais retourne à la ligne (par mots) sous la position, `max_lines` max."""
    s = str(value or "").strip()
    if not s:
        return
    x, y, max_w = POSITIONS[key]
    c.setFont("Helvetica", FONT_SIZE)
    lines: list[str] = []
    cur = ""
    for word in s.split():
        cand = f"{cur} {word}".strip()
        if c.stringWidth(cand, "Helvetica", FONT_SIZE) <= max_w or not cur:
            cur = cand
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines - 1] + [" ".join(lines[max_lines - 1:])]
    for i, line in enumerate(lines):
        c.drawString(x, y - i * OBS_LINE_HEIGHT, _fit(c, line, max_w, FONT_SIZE))


_SITUATION_LABELS = {
    "celibataire": "Célibataire", "c": "Célibataire",
    "marie": "Marié(e)", "m": "Marié(e)",
    "divorce": "Divorcé(e)", "d": "Divorcé(e)",
    "veuf": "Veuf(ve)", "v": "Veuf(ve)",
}


def _situation_label(v: Optional[str]) -> str:
    """Code stocké (« marie ») → libellé de la fiche de référence (« Marié(e) »)."""
    if not v:
        return ""
    return _SITUATION_LABELS.get(str(v).strip().lower(), str(v))


def _fmt_date(v: Optional[str]) -> str:
    """ISO « 1981-10-14 » (format OCR) → « 14/10/1981 » ; tout autre format est laissé tel quel."""
    if not v:
        return ""
    s = str(v).strip()
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return s


def _ocr_fields(dossier: Dossier) -> dict:
    """Champs lus par l'OCR sur la pièce (recto, puis MRZ du verso en complément).

    Sert de repli quand l'usager n'a pas saisi son identité lui-même (parcours
    réduit) : sans cela nom, prénoms, date de naissance et n° de pièce restaient
    vides sur la fiche alors que l'OCR les avait lus.
    """
    out: dict = {}
    pieces = list(getattr(dossier, "pieces", None) or [])
    for p in pieces:
        face = getattr(p.face, "value", p.face)
        data = p.ocr_data or {}
        if face == "recto":
            for k, v in (data.get("fields") or {}).items():
                if v and k not in out:
                    out[k] = v
            out.setdefault("_piece_type", getattr(p.piece_type, "value", p.piece_type))
    for p in pieces:
        if getattr(p.face, "value", p.face) == "verso":
            parsed = ((p.ocr_data or {}).get("mrz") or {}).get("parsed") or {}
            for src, dst in (("nom", "nom"), ("prenoms", "prenoms"),
                             ("document_number", "numero_piece"), ("date_naissance_iso", "date_naissance")):
                if parsed.get(src) and dst not in out:
                    out[dst] = parsed[src]
    return out


def _piece_label(t: Optional[str]) -> str:
    if not t:
        return ""
    low = t.lower()
    if "cni" in low or "carte" in low:
        return "Carte d'identité nationale"
    if "pass" in low:
        return "Passeport"
    if "attest" in low:
        return "Attestation d'identité"
    return t


def _fetch_image_bytes(url: str) -> Optional[bytes]:
    """Récupère une image depuis une URL présignée MinIO (http)."""
    try:
        import httpx
        with httpx.Client(timeout=5.0) as client:
            r = client.get(url)
            if r.status_code == 200:
                return r.content
    except Exception as e:
        logger.warning("fiche_pdf: fetch image échoué %s (%s)", url[:80], e)
    return None


def _draw_image(c: canvas.Canvas, url: Optional[str], box: tuple[float, float, float, float]) -> None:
    if not url or not url.startswith(("http://", "https://")):
        return
    data = _fetch_image_bytes(url)
    if not data:
        return
    try:
        from reportlab.lib.utils import ImageReader
        img = ImageReader(io.BytesIO(data))
        x, y, w, h = box
        c.drawImage(img, x, y, w, h, preserveAspectRatio=True, mask="auto")
    except Exception as e:
        logger.warning("fiche_pdf: drawImage échoué (%s)", e)


def generate_fiche_pdf(
    dossier: Dossier,
    imprime_par: str,
    photo_url: Optional[str] = None,
    signature_url: Optional[str] = None,
) -> bytes:
    """Construit le PDF rempli en superposant les valeurs sur le template vierge."""
    extra = (dossier.donnees_pro.extra if dossier.donnees_pro else {}) or {}
    donnees = dossier.donnees_pro
    end_user = dossier.end_user if hasattr(dossier, "end_user") else None

    # Décomposition nom/prénoms (end_user.name = "PRENOM1 PRENOM2 NOM")
    full_name = (end_user.name or "").strip() if end_user else ""
    parts = full_name.split()
    nom = parts[-1] if parts else ""
    prenoms = " ".join(parts[:-1]) if len(parts) > 1 else ""

    # Repli sur l'OCR de la pièce quand l'usager n'a pas saisi son identité
    ocr = _ocr_fields(dossier)
    if not nom and not prenoms:
        nom = str(ocr.get("nom") or "")
        prenoms = str(ocr.get("prenoms") or "")

    # Observations : comme la fiche de référence, on y reporte la date d'embauche
    observations = extra.get("observations") or (
        f"date d'embauche : {extra['date_embauche']}" if extra.get("date_embauche") else ""
    )

    now = datetime.now()

    values = {
        "imprime_le":      now.strftime("%d/%m/%Y %H:%M"),
        "imprime_par":     imprime_par,
        "journee":         now.strftime("%d/%m/%Y"),

        "code":            dossier.numero_societaire or dossier.dossier_number or "",
        "numero_manuel":   dossier.matricule or "",

        # Type client = employeur, comme sur la fiche Perfect Vision de référence
        "type_client":     extra.get("type_client") or dossier.employeur_code or "",
        "civilite":        extra.get("civilite", ""),
        "nom":             nom,
        "prenoms":         prenoms,
        "situation_matri": _situation_label(donnees.situation_familiale if donnees else ""),
        "date_naissance":  _fmt_date(extra.get("date_naissance") or ocr.get("date_naissance")),
        "lieu_naissance":  extra.get("lieu_naissance", ""),
        "piece_identite":  _piece_label(extra.get("type_piece") or ocr.get("_piece_type")),
        "num_piece":       extra.get("numero_piece") or ocr.get("numero_piece") or "",
        "domicile":        extra.get("domicile") or extra.get("adresse_domicile", ""),
        "boite_postale":   extra.get("boite_postale_choisie") or extra.get("boite_postale", ""),
        "telephone":       (end_user.phone if end_user else "") or "",
        "email":           ((end_user.extra or {}).get("email") if end_user else "") or "",
        "situation_geo":   extra.get("situation_geographique", ""),
        "distance_agence": extra.get("distance_agence", ""),
        "profession":      (donnees.fonction if donnees else "") or "",
        "nom_conjoint":    extra.get("nom_conjoint", ""),
        "nom_prevenir":    extra.get("personne_a_prevenir", ""),

        "num_compte":      extra.get("numero_compte", ""),
        "adr_prevenir":    extra.get("contact_prevenir_1", ""),
        "beneficiaire":    extra.get("beneficiaire", ""),
        "tuteur":          extra.get("tuteur", ""),
        "ayant_droit":     extra.get("ayants_droit", ""),
        "nb_signatures":   extra.get("nombre_signatures", ""),
        "date_inscription":dossier.created_at.strftime("%d/%m/%Y") if dossier.created_at else "",
        "gestionnaire":    extra.get("gestionnaire") or "",
        "nom_tuteur":      extra.get("nom_tuteur", ""),

        "cat_val":         extra.get("categorie", ""),
        "emp_val":         dossier.employeur_code or "",
        "cons_val":        "OUI" if any(
            c.decision.value == "accepte" for c in (dossier.consentements or [])
        ) else "",
        "mere_val":        extra.get("nom_mere", ""),
    }

    # Crée l'overlay
    overlay_buf = io.BytesIO()
    c = canvas.Canvas(overlay_buf, pagesize=(PAGE_WIDTH, PAGE_HEIGHT))

    for key, val in values.items():
        _text(c, key, val)
    _text_multiline(c, "observations", observations)

    # Photo (recto pièce) + signature
    _draw_image(c, photo_url, PHOTO_BOX)
    _draw_image(c, signature_url, SIGNATURE_BOX)

    c.showPage()
    c.save()
    overlay_buf.seek(0)

    # Fusionne overlay + template.
    # La page doit appartenir au writer AVANT merge_page : pypdf 7 a supprimé
    # la fusion sur une page « orpheline » (ancienne approche → HTTP 500).
    overlay = PdfReader(overlay_buf)
    writer = PdfWriter(clone_from=str(TEMPLATE_PATH))
    writer.pages[0].merge_page(overlay.pages[0])

    out_buf = io.BytesIO()
    writer.write(out_buf)
    return out_buf.getvalue()
