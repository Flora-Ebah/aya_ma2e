"""Helpers OCR partagés par les actions de workflow.

Wraps `services/ocr_azure_vision.py` avec :
- détection du type de fichier via magic bytes (évite les .bin WhatsApp)
- téléchargement depuis MinIO via media_url
- gestion d'erreur unifiée via `OCRError`

Migration : Mindee → Azure AI Vision (Read API) + structuration LLM via
Azure OpenAI (gpt-5.4-mini). L'interface (`run_ocr_recto`, `run_ocr_verso`)
reste identique côté action workflow.
"""
from __future__ import annotations

import logging
from typing import Optional

from uuid import UUID

from app.core import storage
from app.models import PieceType
from app.services import ocr_azure_vision, ocr_ocrspace

logger = logging.getLogger(__name__)


# ─── Sélection dynamique du provider selon le setting services.ocr_provider ──
async def _resolve_provider(tenant_id: Optional[UUID]):
    """Retourne le module wrapper à utiliser (azure_vision, ocrspace ou None pour mock).

    Lit `services.ocr_provider` côté tenant. Défaut : ocr_space (recettes).
    Si la lecture échoue, fallback sur le premier provider configuré.
    """
    provider = "ocr_space"  # défaut sécurisé pour recette
    if tenant_id is not None:
        try:
            from app.services import settings_service
            from app.core.database import async_session
            async with async_session() as db:
                val = await settings_service.get_value(db, tenant_id, "services", "ocr_provider")
                if val:
                    provider = str(val)
        except Exception as e:
            logger.debug("Lecture services.ocr_provider impossible (%s), défaut=%s", e, provider)

    if provider == "azure_vision":
        if ocr_azure_vision.is_configured():
            return ocr_azure_vision, "azure_vision"
        logger.warning("Provider azure_vision sélectionné mais pas configuré → fallback ocr_space")
        provider = "ocr_space"

    if provider == "ocr_space":
        if ocr_ocrspace.is_configured():
            return ocr_ocrspace, "ocr_space"
        logger.warning("Provider ocr_space sélectionné mais pas configuré → fallback azure_vision")
        if ocr_azure_vision.is_configured():
            return ocr_azure_vision, "azure_vision"

    return None, "mock"


class OCRError(Exception):
    """Erreur dans le pipeline OCR (config manquante, fichier illisible, etc.)."""


def detect_filename_by_magic(data: bytes, fallback: str = "image.jpg") -> str:
    """Détecte le type de fichier via les magic bytes et retourne un filename correct.

    Les fichiers WhatsApp arrivent souvent avec extension `.bin` que Mindee rejette.
    Formats supportés par Mindee : image (JPG/PNG/WEBP/TIFF/HEIC) et PDF.
    Word (DOCX/DOC) est détecté mais ne passera pas par Mindee — l'agent devra
    le consulter manuellement depuis le back-office.
    """
    if not data or len(data) < 12:
        return fallback
    if data[:3] == b"\xff\xd8\xff":
        return "image.jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image.png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image.webp"
    if data[:4] in (b"II*\x00", b"MM\x00*"):
        return "image.tiff"
    if data[:4] == b"%PDF":
        return "document.pdf"
    if data[:8] in (b"ftypheic", b"ftypheix") or data[4:12] == b"ftypheic":
        return "image.heic"
    # DOCX = ZIP avec marqueur "[Content_Types].xml" ; .doc legacy = compound doc
    if data[:4] == b"PK\x03\x04":
        # Heuristique : un .docx contient "word/" dans les premières dizaines de Ko
        if b"word/" in data[:4096]:
            return "document.docx"
        return "document.zip"
    if data[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        return "document.doc"
    return fallback


def is_ocr_compatible(filename: str) -> bool:
    """True si le fichier peut être traité par Mindee (image ou PDF).

    Les Word (.doc/.docx) sont stockés tels quels mais nécessitent une revue
    manuelle côté agent.
    """
    fn = filename.lower()
    return fn.endswith((".jpg", ".jpeg", ".png", ".webp", ".tiff", ".tif", ".heic", ".pdf"))


async def run_ocr_recto(
    media_url: str,
    piece_type: PieceType,
    tenant_id: Optional[UUID] = None,
) -> dict:
    """OCR du recto avec dispatch sur le provider configuré.

    Lit `services.ocr_provider` (côté tenant) pour choisir entre OCR.space,
    Azure AI Vision ou mock. Fallback gracieux si le provider sélectionné
    n'est pas configuré.
    """
    if not media_url or not media_url.startswith("minio://"):
        raise OCRError(f"media_url invalide : {media_url!r}")

    provider_mod, provider_name = await _resolve_provider(tenant_id)
    if provider_mod is None:
        raise OCRError(
            "Aucun fournisseur OCR configuré. "
            "Renseignez OCR_SPACE_API_KEY ou AZURE_AI_VISION_API_KEY dans .env."
        )

    file_bytes, original_filename = storage.get_object_bytes_from_url(media_url)
    filename = detect_filename_by_magic(file_bytes, fallback=original_filename or "image.jpg")
    logger.info(
        "OCR recto : provider=%s, %d bytes, filename=%s, piece=%s",
        provider_name, len(file_bytes), filename, piece_type.value,
    )
    try:
        return await provider_mod.ocr_recto(file_bytes, filename, piece_type)
    except Exception as e:
        logger.error("OCR recto (%s) a échoué : %s", provider_name, e)
        raise OCRError(str(e)) from e


async def run_ocr_verso(
    media_url: str,
    piece_type: PieceType,
    recto_data: Optional[dict],
    tenant_id: Optional[UUID] = None,
) -> dict:
    """OCR du verso avec dispatch sur le provider configuré + cross-check MRZ."""
    if not media_url or not media_url.startswith("minio://"):
        raise OCRError(f"media_url invalide : {media_url!r}")

    provider_mod, provider_name = await _resolve_provider(tenant_id)
    if provider_mod is None:
        raise OCRError(
            "Aucun fournisseur OCR configuré. "
            "Renseignez OCR_SPACE_API_KEY ou AZURE_AI_VISION_API_KEY dans .env."
        )

    file_bytes, original_filename = storage.get_object_bytes_from_url(media_url)
    filename = detect_filename_by_magic(file_bytes, fallback=original_filename or "image.jpg")
    logger.info(
        "OCR verso : provider=%s, %d bytes, filename=%s",
        provider_name, len(file_bytes), filename,
    )
    try:
        return await provider_mod.ocr_verso(
            file_bytes, filename, piece_type, recto_data=recto_data,
        )
    except Exception as e:
        logger.error("OCR verso (%s) a échoué : %s", provider_name, e)
        raise OCRError(str(e)) from e
