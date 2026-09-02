"""Wrapper OCR.space — fournisseur gratuit utilisé pour les recettes MA2E.

Free tier : 25 000 req/mois, 500 req/jour/IP, 1 MB max par fichier.
Inscription : https://ocr.space/ocrapi → "Register for free API key"

Pipeline en 2 temps (identique à Azure Vision / Mindee) :
  1) OCR.space → texte brut extrait de l'image
  2) Azure OpenAI (gpt-5.4-mini) → structuration en champs JSON

Compression automatique avant envoi : photos téléphone (3-10 MB) sont
redimensionnées + recompressées en JPEG pour passer sous la limite 1 MB
d'OCR.space sans perte de précision OCR notable (Mindee/Vision recommandent
eux-mêmes ~2000 px de large pour la lecture documentaire).
"""
from __future__ import annotations

import io
import logging
from typing import Optional

import httpx

from app.conversation import llm_azure
from app.core.config import settings
from app.models import PieceFace, PieceType
from app.services.ocr_guardrails import (
    SYSTEM_PROMPT_ID_EXTRACTION,
    build_user_message,
    detect_counterfeit_markers,
    sanitize_extracted_fields,
)

logger = logging.getLogger(__name__)

# Limite imposée par OCR.space free tier : 1 MB. On vise 950 KB pour
# garder une marge (la base64 d'un multipart ajoute un peu d'overhead).
MAX_FILE_BYTES = 950 * 1024

# OCREngine 2 (LSTM) : meilleur pour les images de pièce d'identité.
# 1 = legacy, 3 = handwriting, 5 = latest LSTM v3.
DEFAULT_OCR_ENGINE = 2


def is_configured() -> bool:
    return bool(settings.ocr_space_api_key)


def _normalize_for_match(s: Optional[str]) -> str:
    """Normalise un nom pour comparaison anti-fraude : sans accents/espaces, majuscules."""
    if not s:
        return ""
    import unicodedata
    nfkd = unicodedata.normalize("NFKD", str(s))
    ascii_only = "".join(c for c in nfkd if not unicodedata.combining(c))
    return "".join(ch for ch in ascii_only.upper() if ch.isalnum())


def _check_identity_coherence(mrz_parsed: dict, recto_data: Optional[dict]) -> bool:
    """Vraie détection anti-fraude : nom OU prénom lisibles des deux côtés ET différents
    après normalisation → carte suspecte (recto + verso de 2 pièces distinctes).

    Retourne True (cohérent) tant qu'on n'a pas la preuve d'une divergence forte —
    les faux positifs sont plus coûteux qu'un faux négatif (l'agent valide en second).
    """
    if not recto_data or not recto_data.get("fields"):
        return True
    rfields = recto_data["fields"]
    for mrz_key, recto_key in (("surname", "nom"), ("given_names", "prenoms")):
        mrz_val = _normalize_for_match(mrz_parsed.get(mrz_key))
        rec_val = _normalize_for_match(rfields.get(recto_key))
        if mrz_val and rec_val and mrz_val != rec_val:
            # Le MRZ tronque à 30 chars — accepte le préfixe commun.
            if not (mrz_val.startswith(rec_val) or rec_val.startswith(mrz_val)):
                return False
    return True


def _compress_image(file_bytes: bytes, max_bytes: int = MAX_FILE_BYTES) -> tuple[bytes, str]:
    """Redimensionne + recompresse une image pour passer sous max_bytes.

    Retourne (bytes_compressés, "image/jpeg"). Si le fichier est un PDF
    ou un Word, on le renvoie tel quel sans toucher (Pillow ne sait pas
    les compresser de manière utile pour OCR.space).
    """
    # Magic bytes : si PDF / DOCX / DOC → on n'y touche pas
    if file_bytes[:4] == b"%PDF":
        return file_bytes, "application/pdf"
    if file_bytes[:4] == b"PK\x03\x04":
        return file_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if file_bytes[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        return file_bytes, "application/msword"

    try:
        from PIL import Image, ImageOps
    except ImportError as e:
        logger.warning("Pillow non installé — pas de compression : %s", e)
        return file_bytes, "image/jpeg"

    try:
        img = Image.open(io.BytesIO(file_bytes))
        # Corrige l'orientation EXIF (téléphones)
        img = ImageOps.exif_transpose(img)
        # Réduit à 2048 px côté long (suffisant pour OCR documentaire)
        img.thumbnail((2048, 2048), Image.Resampling.LANCZOS)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
    except Exception as e:
        logger.warning("Pillow ne sait pas ouvrir ce format (%s) — envoi tel quel", e)
        return file_bytes, "image/jpeg"

    # Essaie plusieurs qualités JPEG pour rester sous max_bytes
    for quality in (85, 75, 65, 55, 45):
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        size = buf.tell()
        if size <= max_bytes:
            logger.info(
                "OCR.space : image compressée %d → %d bytes (quality=%d)",
                len(file_bytes), size, quality,
            )
            return buf.getvalue(), "image/jpeg"

    # Si même quality=45 ne suffit pas, on retourne quand même (OCR.space rejettera)
    logger.warning(
        "OCR.space : image toujours trop grosse après compression (%d bytes)",
        buf.tell(),
    )
    return buf.getvalue(), "image/jpeg"


async def _read_text(file_bytes: bytes, filename: str) -> str:
    """Appelle OCR.space /parse/image et retourne le texte brut concaténé."""
    compressed, content_type = _compress_image(file_bytes)

    # Inférence du nom de fichier transmis à OCR.space (utile pour les logs côté eux)
    name = filename or "image.jpg"
    if content_type == "image/jpeg" and not name.lower().endswith((".jpg", ".jpeg")):
        name = "image.jpg"

    data = {
        "apikey": settings.ocr_space_api_key,
        # Français — capture les CNI ivoiriennes & passeports UEMOA
        "language": "fre",
        "OCREngine": str(DEFAULT_OCR_ENGINE),
        "isOverlayRequired": "false",
        "detectOrientation": "true",
        "scale": "true",
        "isTable": "false",
    }
    files = {"file": (name, compressed, content_type)}

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(settings.ocr_space_endpoint, data=data, files=files)
            resp.raise_for_status()
            payload = resp.json()
    except httpx.HTTPStatusError as e:
        logger.error("OCR.space HTTP %s : %s", e.response.status_code, e.response.text[:500])
        raise RuntimeError(f"OCR.space erreur {e.response.status_code}") from e
    except httpx.HTTPError as e:
        logger.error("OCR.space appel échoué : %s", e)
        raise RuntimeError(str(e)) from e

    # OCR.space renvoie IsErroredOnProcessing=True en cas de souci côté serveur
    if payload.get("IsErroredOnProcessing"):
        msg = payload.get("ErrorMessage") or ["unknown OCR.space error"]
        msg_str = "; ".join(msg) if isinstance(msg, list) else str(msg)
        logger.error("OCR.space erreur de traitement : %s", msg_str)
        raise RuntimeError(f"OCR.space : {msg_str}")

    parsed_results = payload.get("ParsedResults") or []
    texts = []
    for r in parsed_results:
        t = r.get("ParsedText")
        if t:
            texts.append(t.strip())
    return "\n".join(texts)


async def _structure_with_llm(raw_text: str, face: PieceFace) -> dict:
    """Structuration via Azure OpenAI — identique au wrapper Azure Vision."""
    if not raw_text or len(raw_text.strip()) < 5:
        return {"fields": {}, "mrz": {}}

    # F-01 — mêmes guardrails que ocr_azure_vision. Prompt séparé (system
    # immuable ↔ user avec le texte OCR sous <ocr_text> nonce-scellé).
    if face == PieceFace.recto:
        schema_hint = (
            "{\n"
            '  "fields": {\n'
            '    "numero_piece": "..." ou null,\n'
            '    "nom": "..." ou null,\n'
            '    "prenoms": "..." ou null,\n'
            '    "sexe": "M" ou "F" ou null,\n'
            '    "date_naissance": "YYYY-MM-DD" ou null,\n'
            '    "lieu_naissance": "..." ou null,\n'
            '    "nationalite": "Ivoirienne" ou autre,\n'
            '    "date_delivrance": "YYYY-MM-DD" ou null,\n'
            '    "date_expiration": "YYYY-MM-DD" ou null\n'
            "  }\n"
            "}"
        )
    else:
        schema_hint = (
            "{\n"
            '  "mrz": {\n'
            '    "line1": "", "line2": "", "line3": "",\n'
            '    "parsed": {\n'
            '      "document_type": "I", "issuing_country": "CIV",\n'
            '      "document_number": null,\n'
            '      "nom": null, "prenoms": null,\n'
            '      "sexe": "M" ou "F" ou null,\n'
            '      "date_naissance_iso": "YYYY-MM-DD" ou null,\n'
            '      "date_expiration_iso": "YYYY-MM-DD" ou null,\n'
            '      "nationalite": "CIV"\n'
            "    }\n"
            "  },\n"
            '  "fields": {"adresse": null, "signature_presente": true}\n'
            "}"
        )

    try:
        structured = await llm_azure.structured_output(
            system_prompt=SYSTEM_PROMPT_ID_EXTRACTION,
            user_message=build_user_message(schema_hint, raw_text),
            max_tokens=2048,
        )
    except Exception as e:
        logger.warning("Structuration LLM échouée : %s", e)
        return {"fields": {}, "mrz": {}}

    raw_fields = structured.get("fields") if isinstance(structured, dict) else {}
    clean_fields, warnings = sanitize_extracted_fields(raw_fields or {})
    if warnings:
        logger.warning("OCR sanitize warnings (%s) : %s", face.value, warnings)
    structured["fields"] = clean_fields
    structured["_guardrails_warnings"] = warnings

    # F-03 (mitigation) — détection de marqueurs de contrefaçon triviaux.
    counterfeit = detect_counterfeit_markers(raw_text, clean_fields)
    if counterfeit:
        logger.warning("OCR counterfeit markers (%s) : %s", face.value, counterfeit)
    structured["_counterfeit_markers"] = counterfeit
    return structured


PROVIDER_LABEL = "ocr.space + azure-openai/gpt-5.4-mini"


async def ocr_recto(file_bytes: bytes, filename: str, piece_type: PieceType) -> dict:
    """OCR recto via OCR.space + structuration LLM Azure."""
    raw_text = await _read_text(file_bytes, filename)
    logger.info("OCR.space recto : %d caractères extraits", len(raw_text))

    structured = await _structure_with_llm(raw_text, PieceFace.recto)
    fields = {
        k: v for k, v in (structured.get("fields") or {}).items()
        if v not in (None, "", "null")
    }

    confidence = 0.85  # OCR.space gratuit légèrement moins bon que Vision
    warnings = []
    if not fields.get("numero_piece") and not fields.get("nom"):
        warnings.append("partial_extraction")
        confidence = 0.5

    logger.info("Recto → %d champs structurés, conf=%.2f", len(fields), confidence)
    return {
        "provider": PROVIDER_LABEL,
        "piece_type": piece_type.value,
        "face": PieceFace.recto.value,
        "confidence": confidence,
        "fields": fields,
        "raw_text": raw_text[:2000],
        "warnings": warnings,
    }


async def ocr_verso(
    file_bytes: bytes,
    filename: str,
    piece_type: PieceType,
    recto_data: Optional[dict] = None,
) -> dict:
    """OCR verso via OCR.space + MRZ + cross-check avec recto."""
    raw_text = await _read_text(file_bytes, filename)
    logger.info("OCR.space verso : %d caractères extraits", len(raw_text))

    structured = await _structure_with_llm(raw_text, PieceFace.verso)
    mrz = structured.get("mrz") or {}
    fields = {
        k: v for k, v in (structured.get("fields") or {}).items()
        if v not in (None, "", "null")
    }
    parsed = {
        k: v for k, v in (mrz.get("parsed") or {}).items()
        if v not in (None, "", "null")
    }

    # Cohérence recto/verso : on compare nom + prénom (identité), pas le n° document.
    # Sur la CNI ivoirienne, le NNI imprimé (recto) et le n° document MRZ (verso)
    # sont légitimement différents → ancien check faux positif.
    coherent = _check_identity_coherence(parsed, recto_data)

    confidence = 0.88 if (mrz.get("line1") or mrz.get("line2")) else 0.65
    warnings = [] if coherent else ["incoherence_recto_verso"]

    logger.info(
        "Verso → mrz=%s parsed=%d champs=%d coherent=%s",
        "OK" if (mrz.get("line1") or mrz.get("line2")) else "NO",
        len(parsed), len(fields), coherent,
    )
    return {
        "provider": PROVIDER_LABEL,
        "piece_type": piece_type.value,
        "face": PieceFace.verso.value,
        "confidence": confidence,
        "mrz": {
            "line1": mrz.get("line1", "") or "",
            "line2": mrz.get("line2", "") or "",
            "line3": mrz.get("line3", "") or "",
            "parsed": parsed,
        },
        "fields": fields,
        "raw_text": raw_text[:2000],
        "warnings": warnings,
    }
