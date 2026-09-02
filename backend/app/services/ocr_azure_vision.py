"""Wrapper Azure AI Vision — extraction de texte (OCR) via la Read API.

Pipeline en 2 temps (identique à l'ancien Mindee → Groq) :
  1) Azure AI Vision (Read API) → texte brut extrait de l'image
  2) Azure OpenAI (gpt-5.4-mini) → structuration en champs JSON

Endpoint Azure AI Vision attendu :
    https://<resource>.cognitiveservices.azure.com/

L'URL appelée est :
    {endpoint}computervision/imageanalysis:analyze?features=read&api-version=2024-02-01
"""
from __future__ import annotations

import json
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

# Version stable de la Read API (computer vision v4)
VISION_API_VERSION = "2024-02-01"


def is_configured() -> bool:
    return bool(
        settings.azure_ai_vision_endpoint and settings.azure_ai_vision_api_key
    )


async def _read_text(file_bytes: bytes) -> str:
    """Appelle la Read API et retourne le texte brut extrait."""
    base = settings.azure_ai_vision_endpoint.rstrip("/")
    url = f"{base}/computervision/imageanalysis:analyze?features=read&api-version={VISION_API_VERSION}"

    headers = {
        "Ocp-Apim-Subscription-Key": settings.azure_ai_vision_api_key,
        "Content-Type": "application/octet-stream",
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, headers=headers, content=file_bytes)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        logger.error("Azure Vision HTTP %s : %s", e.response.status_code, e.response.text[:500])
        raise RuntimeError(f"Azure Vision erreur {e.response.status_code}") from e
    except httpx.HTTPError as e:
        logger.error("Azure Vision appel échoué : %s", e)
        raise RuntimeError(str(e)) from e

    # La Read API retourne : { "readResult": { "blocks": [ { "lines": [{"text":...}] } ] } }
    lines = []
    read_result = data.get("readResult") or {}
    for block in read_result.get("blocks", []):
        for line in block.get("lines", []):
            text = line.get("text")
            if text:
                lines.append(text.strip())
    return "\n".join(lines)


async def _structure_with_llm(raw_text: str, face: PieceFace) -> dict:
    """Demande au LLM Azure de structurer le texte OCR en champs typés."""
    if not raw_text or len(raw_text.strip()) < 5:
        return {"fields": {}, "mrz": {}}

    # F-01 — le schéma est décrit en TEXTE dans le user_message avant le bloc
    # <ocr_text>. Toutes les CONSIGNES de sécurité et de comportement sont
    # DÉPLACÉES dans le system_prompt (immuable). Le texte OCR est encapsulé
    # dans une balise <ocr_text> avec un nonce imprévisible.
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
            '    "line1": "" , "line2": "" , "line3": "",\n'
            '    "parsed": {\n'
            '      "document_type": "I",\n'
            '      "issuing_country": "CIV",\n'
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

    user_message = build_user_message(schema_hint, raw_text)
    structured = await llm_azure.structured_output(
        system_prompt=SYSTEM_PROMPT_ID_EXTRACTION,
        user_message=user_message,
        max_tokens=2048,
    )

    # F-01 — nettoie les champs retournés : bloque toute prompt injection qui
    # aurait franchi le filtre côté LLM. Les warnings sont accumulés.
    raw_fields = structured.get("fields") if isinstance(structured, dict) else {}
    clean_fields, warnings = sanitize_extracted_fields(raw_fields or {})
    if warnings:
        logger.warning("OCR sanitize warnings (%s) : %s", face.value, warnings)
    structured["fields"] = clean_fields
    structured["_guardrails_warnings"] = warnings

    # F-03 (mitigation) — détecte les marqueurs de contrefaçon triviaux
    # (SPECIMEN, TEST, numéro de pièce composé de zéros, etc.). En attendant
    # l'intégration d'un référentiel officiel, ces marqueurs remontent en
    # priority_review pour blocage humain systématique.
    counterfeit = detect_counterfeit_markers(raw_text, clean_fields)
    if counterfeit:
        logger.warning("OCR counterfeit markers (%s) : %s", face.value, counterfeit)
    structured["_counterfeit_markers"] = counterfeit
    return structured


async def ocr_recto(file_bytes: bytes, filename: str, piece_type: PieceType) -> dict:
    """OCR recto : Azure Vision + structuration LLM Azure."""
    raw_text = await _read_text(file_bytes)
    logger.info("Azure Vision recto : %d caractères extraits", len(raw_text))

    structured = await _structure_with_llm(raw_text, PieceFace.recto)
    fields = {
        k: v for k, v in (structured.get("fields") or {}).items()
        if v not in (None, "", "null")
    }

    confidence = 0.92
    warnings = []
    if not fields.get("numero_piece") and not fields.get("nom"):
        warnings.append("partial_extraction")
        confidence = 0.55

    logger.info("Recto → %d champs structurés, conf=%.2f", len(fields), confidence)
    return {
        "provider": "azure-vision-read + azure-openai/gpt-5.4-mini",
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
    """OCR verso : Azure Vision + MRZ + cross-check avec recto."""
    raw_text = await _read_text(file_bytes)
    logger.info("Azure Vision verso : %d caractères extraits", len(raw_text))

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

    # Cohérence recto/verso — vérif d'identité (nom + prénom), pas du n° document.
    # Sur la CNI ivoirienne, NNI recto ≠ n° document MRZ : ancien check faux positif.
    from app.services.ocr_ocrspace import _check_identity_coherence
    coherent = _check_identity_coherence(parsed, recto_data)

    confidence = 0.93 if (mrz.get("line1") or mrz.get("line2")) else 0.7
    warnings = [] if coherent else ["incoherence_recto_verso"]

    logger.info(
        "Verso → mrz=%s parsed=%d champs=%d coherent=%s",
        "OK" if (mrz.get("line1") or mrz.get("line2")) else "NO",
        len(parsed), len(fields), coherent,
    )
    return {
        "provider": "azure-vision-read + azure-openai/gpt-5.4-mini",
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
