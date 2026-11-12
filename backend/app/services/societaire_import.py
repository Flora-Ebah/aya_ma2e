"""Import de la base des sociétaires MA2E (fichier source Excel/CSV).

Différences volontaires avec les autres imports (employeurs, collaborateurs) :
- PAS de rollback global : une ligne invalide est rejetée et rapportée, les
  autres sont importées (le fichier réel compte des milliers de lignes).
- UPSERT sur (tenant_id, id_client) : ré-importer le même fichier est idempotent
  et met à jour les lignes existantes au lieu de les rejeter.
- `dry_run=True` valide et compte (créés / mis à jour / rejetés) sans rien écrire.
- La ligne source complète est conservée dans `extra` (aucune colonne perdue).
"""
from __future__ import annotations

import logging
import re
from datetime import date, datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Societaire

logger = logging.getLogger(__name__)

BATCH_SIZE = 500

# En-têtes sources attendues (après _norm_key : minuscules, espaces/tirets -> _)
REQUIRED_HEADERS = ("id_client", "nom_client")


# ====================================================================== #
# Normalisation
# ====================================================================== #
def _s(v: Any) -> Optional[str]:
    """str nettoyée ; None si vide ou valeur « nulle » ('0', 'null', 'none').

    Un nombre entier venu d'une cellule Excel (6, 6.0) devient « 6 », jamais « 6.0 ».
    """
    if v is None:
        return None
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    s = str(v).strip()
    if s.lower() in ("", "0", "null", "none", "nan", "-"):
        return None
    return s


def norm_matricule(v: Any) -> Optional[str]:
    """Clé de recherche : majuscules, sans espaces/séparateurs (garde zéros initiaux)."""
    s = _s(v)
    return re.sub(r"[\s\-_./]", "", s).upper() if s else None


def norm_cni(v: Any) -> Optional[str]:
    s = _s(v)
    return re.sub(r"[^A-Za-z0-9]", "", s).upper() if s else None


def norm_phone(v: Any) -> Optional[str]:
    """1er numéro ivoirien valide (10 chiffres) d'une chaîne parfois multi-numéros
    (« 01 42 87 84 80/07 07 04 73 92 »). None si aucun n'est valide (ex: '0').

    Cellule Excel au format NOMBRE : Excel a supprimé le 0 initial (0778701287 →
    778701287) ; on le remet pour un nombre à 9 chiffres (ou 225 + 9 chiffres).
    """
    numeric = isinstance(v, (int, float)) and not isinstance(v, bool)
    s = _s(v)
    if not s:
        return None
    for part in re.split(r"[/;,]", s):
        digits = re.sub(r"\D", "", part)
        if digits.startswith("00225"):
            digits = digits[5:]
        elif digits.startswith("225") and len(digits) == 13:
            digits = digits[3:]
        elif numeric and digits.startswith("225") and len(digits) == 12:
            digits = "0" + digits[3:]
        if numeric and len(digits) == 9:
            digits = "0" + digits
        if len(digits) == 10:
            return digits
    return None


def to_date(v: Any) -> Optional[date]:
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v).strip()
    for fmt in _DATE_FORMATS:
        try:
            d = datetime.strptime(s, fmt).date()
        except ValueError:
            continue
        # Année sur 2 chiffres : Python lit « 78 » comme 1978 et « 24 » comme 2024.
        # Une date future (naissance, adhésion) est forcément du siècle précédent.
        if "%y" in fmt and d > date.today():
            d = d.replace(year=d.year - 100)
        return d
    raise ValueError(f"date invalide : {s!r}")


# Formats rencontrés dans les exports Excel / CSV (français et ISO), avec ou sans heure
_DATE_FORMATS = (
    "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d", "%Y/%m/%d",
    "%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S", "%d-%m-%Y %H:%M", "%d-%m-%Y %H:%M:%S",
    "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S.%f",
    "%d/%m/%y", "%d-%m-%y", "%d.%m.%y", "%d/%m/%y %H:%M",
)


def to_bool(v: Any) -> Optional[bool]:
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in ("1", "true", "vrai", "oui", "yes", "o", "x"):
        return True
    if s in ("0", "false", "faux", "non", "no", "n"):
        return False
    return None


def _json_safe(v: Any) -> Any:
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    return str(v)


def _trunc(v: Optional[str], n: int) -> Optional[str]:
    return v[:n] if v else v


# ====================================================================== #
# Ligne source -> dict colonnes Societaire
# ====================================================================== #
def clean_row(row: dict, source_file: str, warnings: Optional[list[str]] = None) -> dict:
    """Lève ValueError si la ligne est inutilisable (id_client ou nom manquant).

    Les problèmes qui n'empêchent pas d'importer le sociétaire (date illisible,
    matricule saisi comme nombre dans Excel) sont ajoutés à `warnings` : la
    valeur fautive est laissée vide ou telle quelle, et signalée dans le rapport.
    """
    warn = warnings if warnings is not None else []
    id_client = _s(row.get("id_client"))
    nom = _s(row.get("nom_client"))
    if not id_client:
        raise ValueError("id_client manquant")
    if not nom:
        raise ValueError("nom_client manquant")

    def _date(col: str) -> Optional[date]:
        try:
            return to_date(row.get(col))
        except ValueError:
            warn.append(f"{col} illisible ({row.get(col)!r}) : laissée vide")
            return None

    # Employeur : colonne MA2E « EMPLOYEUR(2) » si remplie, sinon type_client (SODECI, CIE, GS2E...)
    employeur = _s(row.get("employeur(2)")) or _s(row.get("type_client"))
    date_depart = _date("date_depart")
    raw_mat = row.get("num_manuel")
    matricule = _s(raw_mat)
    if isinstance(raw_mat, (int, float)) and not isinstance(raw_mat, bool) and matricule:
        warn.append(
            f"num_manuel saisi comme nombre dans Excel ({matricule}) : "
            "d'éventuels zéros initiaux ont pu être perdus, à vérifier"
        )

    return {
        "id_client": _trunc(id_client, 32),
        "code_client": _trunc(_s(row.get("code_client")), 32),
        "matricule": _trunc(matricule, 64),
        "matricule_norm": _trunc(norm_matricule(matricule), 64),
        "nom": _trunc(nom.upper(), 255),
        "prenoms": _trunc((_s(row.get("prenoms_client")) or "").upper() or None, 255),
        "sexe": _trunc(_s(row.get("sexe")), 8),
        "civilite": _trunc(_s(row.get("civilite")), 16),
        "statut_matrimonial": _trunc(_s(row.get("statut_matrimonial")), 16),
        "date_naissance": _date("date_naissance"),
        "lieu_naissance": _trunc(_s(row.get("lieu_naissance")), 255),
        "nationalite": _trunc(_s(row.get("nationalite")), 64),
        "type_piece": _trunc(_s(row.get("type_piece_identite")), 128),
        "numero_piece": _trunc(_s(row.get("numero_piece_identite")), 64),
        "cni_norm": _trunc(norm_cni(row.get("numero_piece_identite")), 64),
        "telephone": _trunc(_s(row.get("telephone")), 128),
        "telephone_norm": norm_phone(row.get("telephone")),
        "email": _trunc((_s(row.get("email")) or "").lower() or None, 255),
        "adresse": _trunc(_s(row.get("adresse")), 255),
        "ville": _trunc(_s(row.get("ville")), 128),
        "boite_postale": _trunc(_s(row.get("bp")), 128),
        "profession": _trunc(_s(row.get("profession")), 255),
        "employeur_code": _trunc(employeur.upper() if employeur else None, 64),
        # Catégorie PROFESSIONNELLE (CADRE...) = colonne MA2E « CATEGORIE(1) ».
        # La colonne source `categorie_client` vaut « Individu » (type de client) : elle reste dans `extra`.
        "categorie_client": _trunc(_s(row.get("categorie(1)")), 64),
        "agence": _trunc(_s(row.get("nom_agence")), 64),
        "date_adhesion": _date("date_adhesion"),
        "date_depart": date_depart,
        "motif_depart": _trunc(_s(row.get("motif_depart")), 255),
        "actif": date_depart is None,
        "nom_mere": _trunc(_s(row.get("nom_de_mere(3)")), 255),
        "consentement_recu": to_bool(row.get("consentement_recu(4)")),
        "extra": {k: _json_safe(v) for k, v in row.items()},
        "source_file": _trunc(source_file, 255),
    }


# Colonne de la table → en-têtes sources (normalisés) qui l'alimentent. Une colonne absente
# de ce dict (nom, source_file) est toujours mise à jour ; `id_client` et `extra` à part.
COLUMN_SOURCES: dict[str, tuple[str, ...]] = {
    "code_client": ("code_client",),
    "matricule": ("num_manuel",), "matricule_norm": ("num_manuel",),
    "prenoms": ("prenoms_client",), "sexe": ("sexe",), "civilite": ("civilite",),
    "statut_matrimonial": ("statut_matrimonial",), "date_naissance": ("date_naissance",),
    "lieu_naissance": ("lieu_naissance",), "nationalite": ("nationalite",),
    "type_piece": ("type_piece_identite",),
    "numero_piece": ("numero_piece_identite",), "cni_norm": ("numero_piece_identite",),
    "telephone": ("telephone",), "telephone_norm": ("telephone",),
    "email": ("email",), "adresse": ("adresse",), "ville": ("ville",), "boite_postale": ("bp",),
    "profession": ("profession",), "employeur_code": ("employeur(2)", "type_client"),
    "categorie_client": ("categorie(1)",), "agence": ("nom_agence",),
    "date_adhesion": ("date_adhesion",), "date_depart": ("date_depart",),
    "motif_depart": ("motif_depart",), "actif": ("date_depart",),
    "nom_mere": ("nom_de_mere(3)",), "consentement_recu": ("consentement_recu(4)",),
}


def updatable_columns(headers: set[str], columns) -> list[str]:
    """Colonnes à mettre à jour pour un sociétaire existant, d'après les en-têtes du fichier."""
    return [
        c for c in columns
        if c not in ("id_client", "extra")
        and (c not in COLUMN_SOURCES or any(h in headers for h in COLUMN_SOURCES[c]))
    ]


# ====================================================================== #
# Import
# ====================================================================== #
async def import_societaires(
    db: AsyncSession,
    tenant_id: UUID,
    rows: list[dict],
    report,
    *,
    source_file: str = "",
    dry_run: bool = False,
) -> None:
    """Remplit `report` (ImportReport). Ne commit pas : c'est le rôle de l'appelant."""
    if rows:
        missing = [h for h in REQUIRED_HEADERS if h not in rows[0]]
        if missing:
            raise ValueError(
                f"Colonnes obligatoires absentes du fichier : {', '.join(missing)}. "
                "Vérifiez qu'il s'agit bien du fichier source MA2E."
            )

    cleaned: list[dict] = []
    seen: set[str] = set()
    for i, row in enumerate(rows, start=2):  # ligne 1 = en-têtes
        row_warnings: list[str] = []
        try:
            data = clean_row(row, source_file, row_warnings)
        except ValueError as e:
            report.add_error(i, str(e), {k: _json_safe(v) for k, v in list(row.items())[:6]})
            continue
        if data["id_client"] in seen:
            report.add_error(i, f"Doublon d'id_client dans le fichier : {data['id_client']}",
                             {"id_client": data["id_client"]})
            continue
        seen.add(data["id_client"])
        cleaned.append(data)
        for w in row_warnings:  # ligne importée, mais une valeur est à vérifier
            report.warnings.append({"line": i, "id_client": data["id_client"], "warning": w})

    if not cleaned:
        return

    # Combien existent déjà (pour distinguer créés / mis à jour)
    existing: set[str] = set()
    ids = [c["id_client"] for c in cleaned]
    for k in range(0, len(ids), 5000):
        res = await db.execute(
            select(Societaire.id_client).where(
                Societaire.tenant_id == tenant_id,
                Societaire.id_client.in_(ids[k:k + 5000]),
            )
        )
        existing.update(r[0] for r in res.all())

    n_update = sum(1 for c in cleaned if c["id_client"] in existing)
    report.updated = n_update
    report.accepted = len(cleaned) - n_update  # accepted = créés
    if dry_run:
        return

    # Mise à jour PARTIELLE : un sociétaire existant ne voit changer que les colonnes que
    # le fichier contient. Un fichier réduit (ex. id_client + telephone) ne doit pas effacer
    # la date d'adhésion, le lieu de naissance… importés avant depuis le fichier complet.
    update_cols = updatable_columns(set(rows[0].keys()), cleaned[0].keys())
    table = Societaire.__table__
    for k in range(0, len(cleaned), BATCH_SIZE):
        batch = [{**c, "tenant_id": tenant_id} for c in cleaned[k:k + BATCH_SIZE]]
        stmt = pg_insert(Societaire).values(batch)
        ex = stmt.excluded

        def _set(col: str):
            if col in ("nom", "source_file"):          # toujours renseignés
                return ex[col]
            if col == "actif":                         # recalculé sur la date de départ FINALE
                return func.coalesce(ex.date_depart, table.c.date_depart).is_(None)
            # Cellule vide ou illisible (→ NULL) : on garde la valeur déjà en base
            return func.coalesce(ex[col], table.c[col])

        stmt = stmt.on_conflict_do_update(
            constraint="uq_societaire_id_client",
            set_={col: _set(col) for col in update_cols} | {
                # extra = ligne source : on FUSIONNE (jsonb ||) pour garder les colonnes absentes
                # de ce fichier et l'historique `_modifications` des mises à jour faites par chat.
                "extra": Societaire.__table__.c.extra.op("||")(stmt.excluded.extra),
                "imported_at": func.now(),
                "updated_at": func.now(),
            },
        )
        await db.execute(stmt)
    # Chaque sociétaire importé apparaît dans la page « Dossiers » (dossier « Validé » lié)
    from app.services.societaire_dossiers import sync_dossiers
    for k in range(0, len(ids), 5000):
        rows_db = (await db.execute(
            select(Societaire).where(
                Societaire.tenant_id == tenant_id, Societaire.id_client.in_(ids[k:k + 5000])
            )
        )).scalars().all()
        c, u = await sync_dossiers(db, tenant_id, rows_db)
        report.dossiers_created += c
        report.dossiers_updated += u
    logger.info("Import sociétaires : %d créés, %d mis à jour, %d rejetés (dossiers : %d créés, %d mis à jour)",
                report.accepted, report.updated, report.rejected,
                report.dossiers_created, report.dossiers_updated)
