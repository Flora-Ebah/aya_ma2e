"""OCR réel via Mindee API v2 (ClientV2) + structuration LLM Groq.

PRD §6.3 — Pipeline OCR/MRZ.
Pipeline en 2 temps :
  1) Mindee OCR (modèle générique) → texte brut de la pièce
  2) Groq LLM → structuration en champs (nom, prénoms, date_naissance, MRZ, ...)
"""
import asyncio
import json
import logging
from typing import Optional

from app.conversation import llm, llm_azure
from app.core.config import settings
from app.models import PieceFace, PieceType
from app.services.ocr_guardrails import (
    SYSTEM_PROMPT_ID_EXTRACTION,
    build_user_message,
    detect_counterfeit_markers,
    sanitize_extracted_fields,
)

logger = logging.getLogger(__name__)


def is_configured() -> bool:
    return bool(settings.mindee_api_key and settings.mindee_model_id)


def _run_mindee_sync(file_bytes: bytes, filename: str) -> str:
    """Appelle Mindee OCR v2 et retourne le texte brut complet."""
    from mindee import ClientV2, OCRParameters, OCRResponse
    try:
        from mindee.input.bytes_input import BytesInput
    except ImportError:
        BytesInput = None

    client = ClientV2(settings.mindee_api_key)
    params = OCRParameters(model_id=settings.mindee_model_id)

    if BytesInput:
        input_source = BytesInput(file_bytes, filename)
    else:
        input_source = client.source_from_bytes(file_bytes, filename)

    response = client.enqueue_and_get_result(OCRResponse, input_source, params)

    raw_text = ""
    try:
        pages = response.inference.result.pages
    except AttributeError:
        pages = []

    for page in pages:
        lines = getattr(page, "all_lines", None) or getattr(page, "lines", None)
        if lines:
            for line in lines:
                t = getattr(line, "text", None) or getattr(line, "value", None) or str(line)
                if t:
                    raw_text += t.strip() + "\n"
            continue
        words = getattr(page, "all_words", None) or getattr(page, "words", None)
        if words:
            for w in words:
                t = getattr(w, "text", None) or getattr(w, "value", None) or str(w)
                if t:
                    raw_text += t.strip() + " "
            raw_text += "\n"
            continue
        text = getattr(page, "text", None)
        if text:
            raw_text += str(text).strip() + "\n"

    return raw_text.strip()


async def _run_mindee(file_bytes: bytes, filename: str) -> str:
    return await asyncio.to_thread(_run_mindee_sync, file_bytes, filename)


async def _structure_with_llm(raw_text: str, face: PieceFace) -> dict:
    """Utilise Groq pour structurer le texte OCR en champs."""
    if not raw_text or len(raw_text.strip()) < 5:
        return {"fields": {}, "mrz": {}}

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
            '      "document_number": null, "nom": null, "prenoms": null,\n'
            '      "sexe": "M" ou "F" ou null,\n'
            '      "date_naissance_iso": "YYYY-MM-DD" ou null,\n'
            '      "date_expiration_iso": "YYYY-MM-DD" ou null,\n'
            '      "nationalite": "CIV"\n'
            "    }\n"
            "  },\n"
            '  "fields": {"adresse": null, "signature_presente": true}\n'
            "}"
        )

    # F-01 — pipeline structuré : system_prompt anti-injection immuable,
    # texte OCR encapsulé dans <ocr_text> nonce-scellé, sortie JSON forcée.
    try:
        parsed = await llm_azure.structured_output(
            system_prompt=SYSTEM_PROMPT_ID_EXTRACTION,
            user_message=build_user_message(schema_hint, raw_text),
            max_tokens=2048,
        )
    except Exception as e:
        logger.error("LLM extraction a échoué : %s", e)
        return {"fields": {}, "mrz": {}}

    try:
        # F-01 — sanitize post-extraction pour bloquer les injections qui
        # auraient franchi le filtre côté LLM.
        raw_fields = parsed.get("fields") if isinstance(parsed, dict) else {}
        clean_fields, warnings = sanitize_extracted_fields(raw_fields or {})
        if warnings:
            logger.warning("OCR sanitize warnings (%s) : %s", face.value, warnings)
        # F-03 (mitigation) — marqueurs SPECIMEN / TEST / n° trivial
        counterfeit = detect_counterfeit_markers(raw_text, clean_fields)
        if counterfeit:
            logger.warning("OCR counterfeit markers (%s) : %s", face.value, counterfeit)
        if isinstance(parsed, dict):
            parsed["fields"] = clean_fields
            parsed["_guardrails_warnings"] = warnings
            parsed["_counterfeit_markers"] = counterfeit
        return parsed
    except Exception as e:
        logger.warning("Réponse LLM non parsable : %s | parsed=%r", e, str(parsed)[:200])
        return {"fields": {}, "mrz": {}}


async def ocr_recto(file_bytes: bytes, filename: str, piece_type: PieceType) -> dict:
    raw_text = await _run_mindee(file_bytes, filename)
    logger.info("Mindee OCR recto : %d caractères extraits", len(raw_text))

    structured = await _structure_with_llm(raw_text, PieceFace.recto)
    fields = {k: v for k, v in (structured.get("fields") or {}).items() if v not in (None, "", "null")}

    confidence = 0.92
    warnings = []
    if not fields.get("numero_piece") and not fields.get("nom"):
        warnings.append("partial_extraction")
        confidence = 0.55

    logger.info("Recto → %d champs structurés, conf=%.2f", len(fields), confidence)

    return {
        "provider": "mindee/ocr/v2 + groq/llama-3.3-70b",
        "piece_type": piece_type.value,
        "face": PieceFace.recto.value,
        "confidence": confidence,
        "fields": fields,
        "raw_text": raw_text[:2000],
        "warnings": warnings,
    }


async def ocr_verso(file_bytes: bytes, filename: str, piece_type: PieceType, recto_data: Optional[dict] = None) -> dict:
    raw_text = await _run_mindee(file_bytes, filename)
    logger.info("Mindee OCR verso : %d caractères extraits", len(raw_text))

    structured = await _structure_with_llm(raw_text, PieceFace.verso)
    mrz = structured.get("mrz") or {}
    fields = {k: v for k, v in (structured.get("fields") or {}).items() if v not in (None, "", "null")}

    parsed = {k: v for k, v in (mrz.get("parsed") or {}).items() if v not in (None, "", "null")}

    coherent = True
    if recto_data and recto_data.get("fields"):
        rfields = recto_data["fields"]
        if parsed.get("document_number") and rfields.get("numero_piece") and parsed["document_number"] != rfields["numero_piece"]:
            coherent = False

    confidence = 0.93 if (mrz.get("line1") or mrz.get("line2")) else 0.7
    warnings = [] if coherent else ["incoherence_recto_verso"]

    logger.info(
        "Verso → mrz=%s parsed=%d champs=%d coherent=%s",
        "OK" if (mrz.get("line1") or mrz.get("line2")) else "NO",
        len(parsed), len(fields), coherent,
    )

    return {
        "provider": "mindee/ocr/v2 + groq/llama-3.3-70b",
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
