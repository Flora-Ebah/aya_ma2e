"""Champs manquants d'un dossier (colonne « Champs manquants » de la liste des dossiers).

Un champ est « manquant » quand la fiche d'inscription ne peut pas l'imprimer : ni saisi
(`donnees_pro`, `end_user`), ni lu par l'OCR de la pièce d'identité. Pur calcul, aucun accès base.
"""
from __future__ import annotations

from typing import Any, Optional

from app.services.fiche_pdf import _ocr_fields

# (clé, libellé affiché) — les champs que la fiche d'inscription doit contenir
CHAMPS_REQUIS: list[tuple[str, str]] = [
    ("telephone", "Téléphone"),
    ("date_naissance", "Date de naissance"),
    ("lieu_naissance", "Lieu de naissance"),
    ("numero_piece", "N° de pièce"),
    ("domicile", "Domicile"),
    ("fonction", "Fonction"),
    ("situation_familiale", "Situation familiale"),
    ("personne_a_prevenir", "Personne à prévenir"),
]


def _vide(v: Any) -> bool:
    return v is None or (isinstance(v, str) and not v.strip())


def champs_manquants(dossier: Any, end_user: Optional[Any] = None) -> list[str]:
    """Libellés des champs requis absents (liste vide = dossier complet)."""
    dp = getattr(dossier, "donnees_pro", None)
    extra = dict(getattr(dp, "extra", None) or {})
    eu_extra = dict(getattr(end_user, "extra", None) or {})
    ocr = _ocr_fields(dossier)

    valeurs = {
        "telephone": getattr(end_user, "phone", None) or eu_extra.get("telephone"),
        "date_naissance": extra.get("date_naissance") or ocr.get("date_naissance"),
        "lieu_naissance": extra.get("lieu_naissance") or ocr.get("lieu_naissance"),
        "numero_piece": extra.get("numero_piece") or ocr.get("numero_piece"),
        "domicile": extra.get("domicile") or extra.get("adresse_domicile"),
        "fonction": getattr(dp, "fonction", None),
        "situation_familiale": getattr(dp, "situation_familiale", None),
        "personne_a_prevenir": extra.get("personne_a_prevenir"),
    }
    return [label for key, label in CHAMPS_REQUIS if _vide(valeurs[key])]
