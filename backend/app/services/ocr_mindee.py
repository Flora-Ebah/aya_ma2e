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

from app.conversation import llm
from app.core.config import settings
from app.models import PieceFace, PieceType

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
        prompt = (
            "Voici le texte OCR du RECTO d'une pièce d'identité africaine "
            "(probablement une CNI ivoirienne UEMOA, ou une carte consulaire / résident).\n\n"
            f"```\n{raw_text}\n```\n\n"
            "Extrais les champs en JSON STRICT. Format de réponse OBLIGATOIRE :\n"
            '{\n'
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
            '  }\n'
            '}\n\n'
            "Règles strictes :\n"
            "- Ne retourne RIEN d'autre que le JSON.\n"
            "- Dates au format ISO YYYY-MM-DD obligatoire.\n"
            "- N'invente RIEN ; si un champ est absent ou illisible → null.\n"
            "- Le 'nom' est le nom de famille, les 'prenoms' sont les prénoms.\n"
        )
    else:
        prompt = (
            "Voici le texte OCR du VERSO d'une pièce d'identité (souvent avec une zone MRZ — "
            "lignes de codes en bas selon ICAO 9303).\n\n"
            f"```\n{raw_text}\n```\n\n"
            "Extrais MRZ et autres champs en JSON STRICT :\n"
            '{\n'
            '  "mrz": {\n'
            '    "line1": "..." ou "",\n'
            '    "line2": "..." ou "",\n'
            '    "line3": "..." ou "",\n'
            '    "parsed": {\n'
            '      "document_type": "I",\n'
            '      "issuing_country": "CIV" ou ...,\n'
            '      "document_number": "..." ou null,\n'
            '      "nom": "..." ou null,\n'
            '      "prenoms": "..." ou null,\n'
            '      "sexe": "M" ou "F" ou null,\n'
            '      "date_naissance_iso": "YYYY-MM-DD" ou null,\n'
            '      "date_expiration_iso": "YYYY-MM-DD" ou null,\n'
            '      "nationalite": "CIV" ou ...\n'
            '    }\n'
            '  },\n'
            '  "fields": {\n'
            '    "adresse": "..." ou null,\n'
            '    "signature_presente": true\n'
            '  }\n'
            '}\n\n'
            "Règles strictes :\n"
            "- Ne retourne RIEN d'autre que le JSON.\n"
            "- Les lignes MRZ sont sur 1 à 3 lignes ; copie-les telles quelles.\n"
            "- N'invente rien ; si un champ manque → null ou ''."
        )

    system = (
        "Tu es un extracteur d'identité strict. Tu reçois un texte OCR brut "
        "et tu retournes UNIQUEMENT un objet JSON valide, sans aucun commentaire."
    )

    try:
        raw = await llm.chat_complete(system_prompt=system, user_message=prompt)
    except Exception as e:
        logger.error("LLM extraction a échoué : %s", e)
        return {"fields": {}, "mrz": {}}

    try:
        start = raw.find("{")
        end = raw.rfind("}")
        if start < 0 or end <= start:
            return {"fields": {}, "mrz": {}}
        parsed = json.loads(raw[start : end + 1])
        return parsed
    except json.JSONDecodeError as e:
        logger.warning("Réponse LLM non parsable : %s | raw=%r", e, raw[:200])
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
