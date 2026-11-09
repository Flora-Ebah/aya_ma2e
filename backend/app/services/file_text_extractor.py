"""Extraction de texte depuis fichiers PDF / DOCX / XLSX / TXT.

Point d'entrée unique : ``extract_text(filename, data) -> str``. Les
dépendances optionnelles (``pypdfium2``, ``python-docx``, ``openpyxl``) sont
importées paresseusement pour que l'ImportError éventuel ne bloque pas le
boot du service pour les autres formats.
"""
from __future__ import annotations

import io
import logging
from pathlib import Path

log = logging.getLogger(__name__)


class ExtractionError(ValueError):
    """Le fichier est illisible ou le format n'est pas pris en charge."""


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".txt", ".md", ".csv"}


def extract_text(filename: str, data: bytes) -> str:
    """Dispatch par extension et retourne le texte en UTF-8 (lignes séparées par \\n).

    Lève ``ExtractionError`` si l'extension n'est pas supportée ou que le
    contenu est illisible.
    """
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return _extract_pdf(data)
    if ext == ".docx":
        return _extract_docx(data)
    if ext == ".xlsx":
        return _extract_xlsx(data)
    if ext in {".txt", ".md", ".csv"}:
        return _extract_plain(data)
    raise ExtractionError(
        f"Format {ext or '(inconnu)'} non pris en charge. "
        f"Formats acceptés : {', '.join(sorted(SUPPORTED_EXTENSIONS))}."
    )


def _extract_pdf(data: bytes) -> str:
    import pypdfium2 as pdfium  # type: ignore

    try:
        pdf = pdfium.PdfDocument(data)
    except Exception as exc:
        raise ExtractionError(f"PDF illisible : {exc}") from exc
    out: list[str] = []
    for i, page in enumerate(pdf):
        try:
            tp = page.get_textpage()
            text = tp.get_text_range()
        except Exception as exc:
            log.warning("PDF page %s : échec extraction (%s)", i, exc)
            continue
        if text:
            out.append(text)
    return "\n\n".join(out).strip()


def _extract_docx(data: bytes) -> str:
    try:
        from docx import Document  # type: ignore
    except ImportError as exc:
        raise ExtractionError(
            "La prise en charge DOCX n'est pas disponible (python-docx manquant)."
        ) from exc
    try:
        doc = Document(io.BytesIO(data))
    except Exception as exc:
        raise ExtractionError(f"DOCX illisible : {exc}") from exc
    parts: list[str] = []
    for p in doc.paragraphs:
        if p.text.strip():
            parts.append(p.text)
    # Tables
    for tbl in doc.tables:
        for row in tbl.rows:
            cells = [c.text.strip() for c in row.cells if c.text.strip()]
            if cells:
                parts.append(" | ".join(cells))
    return "\n".join(parts).strip()


def _extract_xlsx(data: bytes) -> str:
    from openpyxl import load_workbook

    try:
        wb = load_workbook(io.BytesIO(data), data_only=True, read_only=True)
    except Exception as exc:
        raise ExtractionError(f"XLSX illisible : {exc}") from exc
    out: list[str] = []
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        out.append(f"[Feuille : {sheet_name}]")
        for row in ws.iter_rows(values_only=True):
            cells = [str(c).strip() for c in row if c is not None and str(c).strip()]
            if cells:
                out.append(" | ".join(cells))
    return "\n".join(out).strip()


def _extract_plain(data: bytes) -> str:
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            return data.decode(enc).strip()
        except UnicodeDecodeError:
            continue
    raise ExtractionError("Fichier texte illisible (encodage inconnu).")
