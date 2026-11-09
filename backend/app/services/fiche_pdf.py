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
# y correspond à la ligne de base du texte en coordonnées PDF (0 = bas).
LEFT_X = 135.0
LEFT_W = 210.0
RIGHT_X = 462.0
RIGHT_W = 220.0

# Champ → (x, y, max_w)
POSITIONS: dict[str, tuple[float, float, float]] = {
    # En-tête (coin haut droit)
    "imprime_le":    (505, 814, 180),
    "imprime_par":   (505, 802, 180),
    "journee":       (505, 790, 180),

    # Code / Numéro manuel (ligne du dessus)
    "code":          (90,  739, 290),
    "numero_manuel": (480, 739, 200),

    # Colonne gauche (labels à x≈26, valeurs à partir de 135)
    "type_client":     (LEFT_X, 709, LEFT_W),
    "civilite":        (LEFT_X, 688, LEFT_W),
    "nom":             (LEFT_X, 666, LEFT_W),
    "prenoms":         (LEFT_X, 644, LEFT_W),
    "situation_matri": (LEFT_X, 622, LEFT_W),
    "date_naissance":  (LEFT_X, 600, LEFT_W),
    "lieu_naissance":  (LEFT_X, 578, LEFT_W),
    "piece_identite":  (LEFT_X, 556, LEFT_W),
    "num_piece":       (LEFT_X, 533, LEFT_W),
    "domicile":        (LEFT_X, 512, LEFT_W),
    "boite_postale":   (LEFT_X, 489, LEFT_W),
    "telephone":       (LEFT_X, 467, LEFT_W),
    "email":           (LEFT_X, 446, LEFT_W),
    "situation_geo":   (LEFT_X, 422, LEFT_W),
    "distance_agence": (LEFT_X, 400, LEFT_W),
    "profession":      (LEFT_X, 380, LEFT_W),
    "nom_conjoint":    (LEFT_X, 357, LEFT_W),
    "nom_prevenir":    (LEFT_X, 334, LEFT_W),

    # Colonne droite (labels à x≈350, valeurs à partir de 462)
    "num_compte":      (RIGHT_X, 582, RIGHT_W),
    "adr_prevenir":    (RIGHT_X, 561, RIGHT_W),
    "beneficiaire":    (RIGHT_X, 540, RIGHT_W),
    "tuteur":          (RIGHT_X, 517, RIGHT_W),
    "ayant_droit":     (RIGHT_X, 492, RIGHT_W),
    "nb_signatures":   (RIGHT_X, 467, RIGHT_W),
    "date_inscription":(RIGHT_X, 428, RIGHT_W),
    "gestionnaire":    (RIGHT_X, 408, RIGHT_W),
    "nom_tuteur":      (RIGHT_X, 386, RIGHT_W),
    "observations":    (RIGHT_X, 362, RIGHT_W),

    # Table Attribut / Valeur (colonne Valeur à partir de x≈350, y des lignes)
    "cat_val":         (350, 280, 330),
    "emp_val":         (350, 260, 330),
    "cons_val":        (350, 240, 330),
    "mere_val":        (350, 220, 330),
}

# Zone photo (encadré) : x=[455..680], y=[620..720] approximativement
PHOTO_BOX = (455, 620, 100, 100)  # x, y, w, h

# Zone signature (cadre droit sous VISA)
SIGNATURE_BOX = (382, 50, 112, 75)


def _text(c: canvas.Canvas, key: str, value: Optional[str], font_size: float = 9.0) -> None:
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
    c.setFont("Helvetica", font_size)
    # Tronque si dépasse la largeur max (évite les débordements sur les colonnes voisines)
    truncated = s
    while c.stringWidth(truncated, "Helvetica", font_size) > max_w and len(truncated) > 4:
        truncated = truncated[:-2] + "…"
    c.drawString(x, y, truncated)


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

    now = datetime.now()

    values = {
        "imprime_le":      now.strftime("%d/%m/%Y %H:%M"),
        "imprime_par":     imprime_par,
        "journee":         now.strftime("%d/%m/%Y"),

        "code":            dossier.numero_societaire or dossier.dossier_number or "",
        "numero_manuel":   dossier.matricule or "",

        "type_client":     extra.get("type_client", ""),
        "civilite":        extra.get("civilite", ""),
        "nom":             nom,
        "prenoms":         prenoms,
        "situation_matri": (donnees.situation_familiale if donnees else "") or "",
        "date_naissance":  extra.get("date_naissance", ""),
        "lieu_naissance":  extra.get("lieu_naissance", ""),
        "piece_identite":  _piece_label(extra.get("type_piece")),
        "num_piece":       extra.get("numero_piece", ""),
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
        "observations":    extra.get("observations", ""),

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

    # Photo (recto pièce) + signature
    _draw_image(c, photo_url, PHOTO_BOX)
    _draw_image(c, signature_url, SIGNATURE_BOX)

    c.showPage()
    c.save()
    overlay_buf.seek(0)

    # Fusionne overlay + template
    template = PdfReader(str(TEMPLATE_PATH))
    overlay = PdfReader(overlay_buf)
    writer = PdfWriter()
    base_page = template.pages[0]
    base_page.merge_page(overlay.pages[0])
    writer.add_page(base_page)

    out_buf = io.BytesIO()
    writer.write(out_buf)
    return out_buf.getvalue()
