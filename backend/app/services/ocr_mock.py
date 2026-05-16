"""Mock OCR service simulant Mindee API.

PRD §6.3 — Pipeline OCR/MRZ.
Le mock retourne des champs réalistes après un délai paramétrable
pour reproduire fidèlement l'expérience utilisateur de Mindee.

Production (Sprint 2 PRD) : remplacement par Mindee API + fallback Tesseract V2.
"""
import asyncio
import random
from datetime import date, timedelta
from typing import Optional

from app.models import PieceFace, PieceType

_PRENOMS_F = ["Awa", "Aïcha", "Mariam", "Fatim", "Adjoua", "Affoué", "Akissi", "Bintou"]
_PRENOMS_M = ["Yao", "Kouassi", "Konan", "Aboubacar", "Mamadou", "Sékou", "Drissa", "Souleymane"]
_NOMS = ["OUATTARA", "KOUAKOU", "TOURÉ", "DIABATÉ", "KONÉ", "TRAORÉ", "DIALLO", "BAMBA", "KOUADIO"]
_VILLES_NAISSANCE = ["Abidjan", "Bouaké", "Daloa", "San-Pédro", "Yamoussoukro", "Korhogo", "Man", "Gagnoa"]


def _gen_cni_number() -> str:
    return f"CI{random.randint(100000000, 999999999)}"


def _gen_birth_date() -> str:
    today = date.today()
    age_days = random.randint(25 * 365, 60 * 365)
    d = today - timedelta(days=age_days)
    return d.isoformat()


def _gen_mrz_line(nom: str, prenom: str, cni: str, dob: str, sexe: str) -> tuple[str, str]:
    """Génère 2 lignes MRZ TD1 simplifiées (ICAO 9303)."""
    line1 = f"I<CIV{cni:<9}<<<<<<<<<<<<<<<<".ljust(30, "<")[:30]
    yymmdd = dob.replace("-", "")[2:]
    expiry = "350101"
    line2 = f"{yymmdd}1{sexe}{expiry}0CIV<<<<<<<<<<<".ljust(30, "<")[:30]
    return line1, line2


async def mock_ocr_recto(piece_type: PieceType, delay_seconds: float = 8.0) -> dict:
    """Simule l'OCR recto. Retourne un payload type Mindee."""
    await asyncio.sleep(delay_seconds)

    sexe = random.choice(["M", "F"])
    prenom = random.choice(_PRENOMS_F if sexe == "F" else _PRENOMS_M)
    nom = random.choice(_NOMS)
    dob = _gen_birth_date()
    cni_number = _gen_cni_number()

    return {
        "provider": "mock-mindee",
        "piece_type": piece_type.value,
        "face": PieceFace.recto.value,
        "confidence": round(random.uniform(0.86, 0.99), 3),
        "fields": {
            "numero_piece": cni_number,
            "nom": nom,
            "prenoms": prenom,
            "sexe": sexe,
            "date_naissance": dob,
            "lieu_naissance": random.choice(_VILLES_NAISSANCE),
            "nationalite": "Ivoirienne",
            "date_delivrance": "2022-03-15",
            "date_expiration": "2032-03-15",
        },
        "warnings": [],
    }


async def mock_ocr_verso(piece_type: PieceType, recto_data: Optional[dict] = None, delay_seconds: float = 6.0) -> dict:
    """Simule l'OCR verso avec parsing MRZ ICAO 9303."""
    await asyncio.sleep(delay_seconds)

    if recto_data and recto_data.get("fields"):
        f = recto_data["fields"]
        nom = f.get("nom", "OUATTARA")
        prenom = f.get("prenoms", "Yao")
        cni = f.get("numero_piece", _gen_cni_number())
        dob = f.get("date_naissance", _gen_birth_date())
        sexe = f.get("sexe", "M")
    else:
        nom = random.choice(_NOMS)
        prenom = random.choice(_PRENOMS_M)
        cni = _gen_cni_number()
        dob = _gen_birth_date()
        sexe = "M"

    mrz1, mrz2 = _gen_mrz_line(nom, prenom, cni, dob, sexe)
    coherent = recto_data is None or recto_data.get("fields", {}).get("numero_piece") == cni

    return {
        "provider": "mock-mindee",
        "piece_type": piece_type.value,
        "face": PieceFace.verso.value,
        "confidence": round(random.uniform(0.91, 0.99), 3),
        "mrz": {
            "line1": mrz1,
            "line2": mrz2,
            "parsed": {
                "document_type": "I",
                "issuing_country": "CIV",
                "document_number": cni,
                "nom": nom,
                "prenoms": prenom,
                "sexe": sexe,
                "date_naissance_iso": dob,
                "date_expiration_iso": "2032-03-15",
                "nationalite": "CIV",
            },
        },
        "fields": {
            "adresse": "Cocody, Abidjan, Côte d'Ivoire",
            "signature_presente": True,
        },
        "warnings": [] if coherent else ["incoherence_recto_verso"],
    }


def is_ocr_quality_acceptable(ocr_result: dict, min_confidence: float = 0.75) -> bool:
    return (
        ocr_result.get("confidence", 0) >= min_confidence
        and "incoherence_recto_verso" not in ocr_result.get("warnings", [])
    )
