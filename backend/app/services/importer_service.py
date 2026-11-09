"""Service d'import en masse des référentiels (US-37).

Cibles supportées :
- `employeurs` : code (str), name (str), is_active (bool, default true)

Garantie transactionnelle : la totalité du fichier est validée AVANT toute
insertion. En cas d'erreur de validation sur ≥1 ligne, AUCUNE ligne n'est
insérée (US-37 règle métier).

Format attendu :
- CSV UTF-8 avec séparateur `;` OU `,` (auto-détecté)
- Excel `.xlsx` (sheet 1, première ligne = en-têtes)
- Taille max 10 Mo (vérifiée côté API)

Retour : rapport d'import structuré avec lignes acceptées/rejetées.
"""
from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass, field
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Collaborateur, Employeur

logger = logging.getLogger(__name__)

SUPPORTED_TARGETS = {"employeurs", "collaborateurs"}
MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 Mo


@dataclass
class ImportRow:
    line_number: int
    data: dict
    error: Optional[str] = None


@dataclass
class ImportReport:
    target: str
    total_lines: int = 0
    accepted: int = 0
    rejected: int = 0
    errors: list[dict] = field(default_factory=list)  # {line, error, data}
    inserted_ids: list[str] = field(default_factory=list)

    def add_error(self, line: int, message: str, data: dict) -> None:
        self.errors.append({"line": line, "error": message, "data": data})
        self.rejected += 1


# ====================================================================== #
# Public API
# ====================================================================== #
async def import_referential(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    target: str,
    filename: str,
    raw_bytes: bytes,
) -> ImportReport:
    """Entrée unique pour tous les imports.

    Lève ValueError si target invalide ou fichier trop gros / format non supporté.
    """
    if target not in SUPPORTED_TARGETS:
        raise ValueError(
            f"Référentiel non supporté : {target}. "
            f"Supportés : {sorted(SUPPORTED_TARGETS)}"
        )
    if len(raw_bytes) > MAX_FILE_BYTES:
        raise ValueError(f"Fichier trop volumineux ({len(raw_bytes)} > {MAX_FILE_BYTES} octets)")

    rows = _parse_file(filename, raw_bytes)

    report = ImportReport(target=target, total_lines=len(rows))

    if target == "employeurs":
        await _import_employeurs(db, tenant_id, rows, report)
    elif target == "collaborateurs":
        await _import_collaborateurs(db, tenant_id, rows, report)

    return report


# ====================================================================== #
# Parsers (CSV / XLSX)
# ====================================================================== #
def _parse_file(filename: str, raw: bytes) -> list[dict]:
    """Retourne une liste de dicts (clé = en-tête normalisée)."""
    lower = filename.lower()
    if lower.endswith(".csv") or lower.endswith(".txt"):
        return _parse_csv(raw)
    if lower.endswith(".xlsx") or lower.endswith(".xls"):
        return _parse_xlsx(raw)
    raise ValueError(
        "Format non supporté. Utilisez CSV (UTF-8) ou Excel (.xlsx)."
    )


def _parse_csv(raw: bytes) -> list[dict]:
    # Décodage tolérant : UTF-8 → UTF-8-sig → cp1252
    text: Optional[str] = None
    for enc in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise ValueError("Encodage du CSV non reconnu (attendu UTF-8).")

    # Auto-détection du délimiteur
    first_line = text.splitlines()[0] if text else ""
    delim = ";" if first_line.count(";") >= first_line.count(",") else ","

    reader = csv.DictReader(io.StringIO(text), delimiter=delim)
    return [{_norm_key(k): (v.strip() if isinstance(v, str) else v) for k, v in row.items()} for row in reader]


def _parse_xlsx(raw: bytes) -> list[dict]:
    try:
        from openpyxl import load_workbook
    except ImportError:
        raise ValueError(
            "Le module openpyxl n'est pas installé. "
            "Utilisez le format CSV ou contactez votre administrateur."
        )
    wb = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []
    headers = [_norm_key(str(h or "")) for h in rows[0]]
    out: list[dict] = []
    for raw_row in rows[1:]:
        if all(c is None or (isinstance(c, str) and not c.strip()) for c in raw_row):
            continue  # ligne vide
        out.append({
            headers[i]: (raw_row[i].strip() if isinstance(raw_row[i], str) else raw_row[i])
            for i in range(len(headers))
            if i < len(raw_row)
        })
    return out


def _norm_key(k: str) -> str:
    return (k or "").strip().lower().replace(" ", "_").replace("-", "_")


def _truthy(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if v is None:
        return True  # default : actif
    s = str(v).strip().lower()
    return s in ("1", "true", "vrai", "yes", "oui", "actif", "active", "")


# ====================================================================== #
# Import : employeurs
# ====================================================================== #
async def _import_employeurs(
    db: AsyncSession,
    tenant_id: UUID,
    rows: list[dict],
    report: ImportReport,
) -> None:
    """En-têtes attendues : code, name (alias : nom), is_active (optionnel)."""

    # 1) Validation TOUTES les lignes AVANT toute insertion (US-37 atomicité)
    cleaned: list[dict] = []
    seen_codes: set[str] = set()
    seen_names: set[str] = set()

    for i, row in enumerate(rows, start=2):  # ligne 1 = en-tête
        code = (row.get("code") or "").strip().upper()
        name = (row.get("name") or row.get("nom") or "").strip()
        if not code:
            report.add_error(i, "Colonne 'code' obligatoire", row); continue
        if not name:
            report.add_error(i, "Colonne 'name' (ou 'nom') obligatoire", row); continue
        if len(code) > 32:
            report.add_error(i, "Code trop long (max 32 caractères)", row); continue
        if len(name) > 255:
            report.add_error(i, "Nom trop long (max 255 caractères)", row); continue
        if code in seen_codes:
            report.add_error(i, f"Doublon de code dans le fichier : {code}", row); continue
        if name.lower() in seen_names:
            report.add_error(i, f"Doublon de nom dans le fichier : {name}", row); continue

        is_active = _truthy(row.get("is_active") or row.get("actif"))
        cleaned.append({"code": code, "name": name, "is_active": is_active, "line": i})
        seen_codes.add(code); seen_names.add(name.lower())

    # 2) Vérif unicité contre la BD (code et name déjà existants)
    if cleaned:
        codes = [r["code"] for r in cleaned]
        existing_codes_rows = (
            await db.execute(
                select(Employeur.code).where(
                    Employeur.tenant_id == tenant_id,
                    func.upper(Employeur.code).in_([c.upper() for c in codes]),
                )
            )
        ).all()
        existing_codes = {r[0].upper() for r in existing_codes_rows}

        names = [r["name"] for r in cleaned]
        existing_names_rows = (
            await db.execute(
                select(Employeur.name).where(
                    Employeur.tenant_id == tenant_id,
                    func.lower(Employeur.name).in_([n.lower() for n in names]),
                )
            )
        ).all()
        existing_names = {r[0].lower() for r in existing_names_rows}

        for r in list(cleaned):
            if r["code"].upper() in existing_codes:
                report.add_error(r["line"], f"Le code {r['code']} existe déjà en base", r)
                cleaned.remove(r); continue
            if r["name"].lower() in existing_names:
                report.add_error(r["line"], f"Le nom {r['name']} existe déjà en base", r)
                cleaned.remove(r); continue

    # 3) Si AU MOINS une erreur, on n'insère RIEN (US-37 règle métier atomicité)
    if report.rejected > 0:
        logger.info("Import employeurs : %d erreurs, annulation", report.rejected)
        return

    # 4) Insertion
    for r in cleaned:
        emp = Employeur(
            tenant_id=tenant_id,
            code=r["code"],
            name=r["name"],
            is_active=r["is_active"],
        )
        db.add(emp)
        await db.flush()
        report.inserted_ids.append(str(emp.id))
        report.accepted += 1


# ====================================================================== #
# Import : collaborateurs
# ====================================================================== #
async def _import_collaborateurs(
    db: AsyncSession,
    tenant_id: UUID,
    rows: list[dict],
    report: ImportReport,
) -> None:
    """En-têtes attendues : matricule, employeur_code (ou employeur),
    nom, prenoms (ou prenom), email (opt), telephone (opt), fonction (opt),
    date_embauche (opt YYYY-MM-DD), statut (opt = actif)."""
    from datetime import datetime as _dt

    cleaned: list[dict] = []
    seen_keys: set[tuple] = set()

    for i, row in enumerate(rows, start=2):
        matricule = (row.get("matricule") or "").strip()
        employeur = (row.get("employeur_code") or row.get("employeur") or "").strip().upper()
        nom = (row.get("nom") or "").strip()
        prenoms = (row.get("prenoms") or row.get("prenom") or "").strip()

        if not matricule:
            report.add_error(i, "Colonne 'matricule' obligatoire", row); continue
        if not employeur:
            report.add_error(i, "Colonne 'employeur_code' (ou 'employeur') obligatoire", row); continue
        if not nom:
            report.add_error(i, "Colonne 'nom' obligatoire", row); continue
        if not prenoms:
            report.add_error(i, "Colonne 'prenoms' obligatoire", row); continue

        key = (employeur, matricule)
        if key in seen_keys:
            report.add_error(i, f"Doublon dans le fichier : {employeur}/{matricule}", row); continue

        date_embauche = None
        if row.get("date_embauche"):
            raw_date = str(row["date_embauche"]).strip()
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
                try:
                    date_embauche = _dt.strptime(raw_date, fmt).date()
                    break
                except ValueError:
                    continue
            if date_embauche is None and raw_date:
                report.add_error(i, f"Format date invalide : {raw_date} (attendu YYYY-MM-DD)", row)
                continue

        cleaned.append({
            "matricule": matricule,
            "employeur_code": employeur,
            "nom": nom,
            "prenoms": prenoms,
            "email": (row.get("email") or "").strip() or None,
            "telephone": (row.get("telephone") or row.get("tel") or "").strip() or None,
            "fonction": (row.get("fonction") or "").strip() or None,
            "date_embauche": date_embauche,
            "statut": (row.get("statut") or "actif").strip() or "actif",
            "line": i,
        })
        seen_keys.add(key)

    # Vérif unicité contre la BD
    if cleaned:
        existing_rows = (await db.execute(
            select(Collaborateur).where(Collaborateur.tenant_id == tenant_id)
        )).scalars().all()
        existing_keys = {(c.employeur_code, c.matricule) for c in existing_rows}
        for r in list(cleaned):
            if (r["employeur_code"], r["matricule"]) in existing_keys:
                report.add_error(
                    r["line"],
                    f"Existe déjà : {r['employeur_code']}/{r['matricule']}", r,
                )
                cleaned.remove(r)

    if report.rejected > 0:
        logger.info("Import collaborateurs : %d erreurs, annulation", report.rejected)
        return

    for r in cleaned:
        c = Collaborateur(
            tenant_id=tenant_id,
            matricule=r["matricule"],
            employeur_code=r["employeur_code"],
            nom=r["nom"],
            prenoms=r["prenoms"],
            email=r["email"],
            telephone=r["telephone"],
            fonction=r["fonction"],
            date_embauche=r["date_embauche"],
            statut=r["statut"],
        )
        db.add(c)
        await db.flush()
        report.inserted_ids.append(str(c.id))
        report.accepted += 1


# ====================================================================== #
# Génération de templates
# ====================================================================== #
def template_csv(target: str) -> str:
    """Retourne le contenu d'un fichier modèle pour le référentiel demandé."""
    if target == "employeurs":
        return (
            "﻿code;name;is_active\n"
            "CIE;Compagnie Ivoirienne d'Électricité;true\n"
            "SODECI;Société de Distribution d'Eau de CI;true\n"
            "ERANOVE;Groupe Eranove (siège);true\n"
        )
    if target == "collaborateurs":
        return (
            "﻿matricule;employeur_code;nom;prenoms;email;telephone;fonction;date_embauche;statut\n"
            "CIE-00042;CIE;DIABATE;Mahamadou;mahamadou.diabate@cie.ci;+22507XXXXXX;Chef de service distribution;2015-06-12;actif\n"
            "SODECI-09812;SODECI;COULIBALY;Salimata;;;Responsable clientèle;2018-03-01;actif\n"
            "ERANOVE-00500;ERANOVE;DOUMBIA;Mariam;mariam.doumbia@eranove.com;;Directrice RH groupe;2010-09-15;actif\n"
        )
    raise ValueError(f"Pas de template pour : {target}")
