"""Tests de l'import de la base sociétaires MA2E (backlog 01/02).

Couvre :
  A. normalisation des données sales (matricule, CNI, téléphone, dates, booléens)
  B. `clean_row` : correspondance des 56 colonnes du fichier source → table
  C. `import_societaires` : rejets, doublons, créés vs mis à jour, simulation,
     écriture par lots, clé d'upsert — avec une FAUSSE session (aucune BD requise)
  D. `import_referential` de bout en bout depuis un vrai .xlsx construit en
     mémoire (en-têtes du fichier source, lignes vides, limite de taille)
  E. API : accès réservé aux administrateurs, paramètre `dry_run` exposé

Lancer :
    python -m tests.test_societaire_import
"""
from __future__ import annotations

import asyncio
import inspect
import io
import os
import sys
from datetime import date, datetime
from uuid import uuid4

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.dialects import postgresql  # noqa: E402
from sqlalchemy.sql import Select  # noqa: E402

from app.services import importer_service  # noqa: E402
from app.services.importer_service import ImportReport  # noqa: E402
from app.services.societaire_import import (  # noqa: E402
    BATCH_SIZE,
    clean_row,
    import_societaires,
    norm_cni,
    norm_matricule,
    norm_phone,
    to_bool,
    to_date,
)

CHECKS = 0


def _assert(cond: bool, msg: str) -> None:
    global CHECKS
    if not cond:
        print(f"FAIL: {msg}", file=sys.stderr)
        raise AssertionError(msg)
    CHECKS += 1


# --------------------------------------------------------------------------
# Données : en-têtes réels du fichier source MA2E + 1re ligne du modèle fourni
# --------------------------------------------------------------------------
SOURCE_HEADERS = [
    "code_categorie_client", "id_client", "code_client", "num_manuel", "nom_client", "prenoms_client",
    "id_agence", "nom_agence", "code_agence", "sexe", "civilite", "statut_matrimonial", "telephone",
    "date_adhesion", "date_naissance", "lieu_naissance", "nationalite", "code_type_piece",
    "type_piece_identite", "numero_piece_identite", "email", "code_profession", "profession", "bp",
    "ville", "adresse", "code_type_client", "type_client", "categorie_client", "code_zone", "code_zone3",
    "code_zone2", "code_zone1", "zone", "zone3", "zone2", "zone1", "alphabetise", "dirigeant",
    "personnel", "gestionnaire", "nbre_homme", "nbre_femme", "date_depart", "motif_depart",
    "age_adhesion", "date_last_modified", "client_perfect", "client_tontine", "collecteur",
    "zone_collecte", "age_client", "CATEGORIE(1)", "EMPLOYEUR(2)", "NOM DE MERE(3)",
    "CONSENTEMENT RECU(4)",
]


def _norm(k: str) -> str:
    return importer_service._norm_key(k)


def _row(**over) -> dict:
    """Une ligne telle que produite par le parseur (clés normalisées)."""
    base = {
        "code_categorie_client": "IND", "id_client": "A0100003", "code_client": "A0104688",
        "num_manuel": "016126G", "nom_client": "SOUMAHORO", "prenoms_client": "FALIKOU",
        "nom_agence": "MA2E", "sexe": "M", "civilite": "M", "statut_matrimonial": "M",
        "telephone": "01 42 87 84 80/07 07 04 73 92",
        "date_adhesion": datetime(2008, 5, 9), "date_naissance": datetime(1978, 12, 13),
        "lieu_naissance": "ZOUANHOUNIEN", "nationalite": "COTE D'IVOIRE",
        "type_piece_identite": "Attestation d'Identité", "numero_piece_identite": "CI001490454",
        "email": None, "profession": "DIRECTEUR REGIONAL", "bp": "0", "type_client": "SODECI",
        "categorie_client": "Individu", "date_depart": None,
        "categorie(1)": None, "employeur(2)": None, "nom_de_mere(3)": None, "consentement_recu(4)": None,
    }
    base.update(over)
    return base


# --------------------------------------------------------------------------
# Fausse session SQLAlchemy : enregistre les requêtes au lieu de les exécuter
# --------------------------------------------------------------------------
class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeDB:
    def __init__(self, existing_ids=()):
        self.existing_ids = set(existing_ids)
        self.inserts = []  # requêtes INSERT ... ON CONFLICT reçues

    async def execute(self, stmt):
        if isinstance(stmt, Select):
            return _FakeResult([(i,) for i in self.existing_ids])
        self.inserts.append(stmt)
        return _FakeResult([])

    def rows_written(self) -> int:
        n = 0
        for stmt in self.inserts:
            params = stmt.compile(dialect=postgresql.dialect()).params
            n += sum(1 for k in params if k.startswith("id_client_m"))
        return n


def _run(rows, existing=(), dry_run=False):
    db = _FakeDB(existing)
    report = ImportReport(target="societaires", total_lines=len(rows), dry_run=dry_run)
    asyncio.run(import_societaires(db, uuid4(), rows, report, source_file="test.xlsx", dry_run=dry_run))
    return db, report


# ==========================================================================
# A. Normalisation
# ==========================================================================
def test_normalisation() -> None:
    _assert(norm_matricule(" 016126 g ") == "016126G", "matricule : majuscules, sans espace")
    _assert(norm_matricule("SODE-2018/45.21") == "SODE2018" + "4521", "matricule : sans - / .")
    _assert(norm_matricule("00006") == "00006", "matricule : les zéros initiaux sont conservés")
    _assert(norm_matricule("0") is None and norm_matricule("") is None, "matricule vide / '0' → None")

    _assert(norm_cni("ci 0014-90454") == "CI001490454", "CNI : alphanumérique majuscule")

    _assert(norm_phone("01 42 87 84 80/07 07 04 73 92") == "0142878480", "tél : 1er numéro valide d'une liste")
    _assert(norm_phone("abc/07 07 04 73 92") == "0707047392", "tél : saute un 1er élément invalide")
    _assert(norm_phone("+225 07 01 02 03 04") == "0701020304", "tél : indicatif +225 retiré")
    _assert(norm_phone("00225 0701020304") == "0701020304", "tél : indicatif 00225 retiré")
    _assert(norm_phone("0") is None, "tél : '0' → None")
    _assert(norm_phone("12345") is None, "tél : trop court → None")
    _assert(norm_phone(778701287) == "0778701287", "tél : nombre Excel sans son 0 → 0 remis")
    _assert(norm_phone(778701287.0) == "0778701287", "tél : nombre Excel (float) → 0 remis")
    _assert(norm_phone(225778701287) == "0778701287", "tél : 225 + 9 chiffres en nombre → 0 remis")
    _assert(norm_phone("778701287") is None, "tél : texte à 9 chiffres NON corrigé (pas une perte Excel)")

    _assert(to_date(datetime(2008, 5, 9, 0, 0)) == date(2008, 5, 9), "date : datetime Excel")
    _assert(to_date("13/12/1978") == date(1978, 12, 13), "date : JJ/MM/AAAA")
    _assert(to_date("1978-12-13") == date(1978, 12, 13), "date : ISO")
    _assert(to_date(None) is None and to_date("") is None, "date vide → None")
    for txt in ("13/12/1978 00:00", "13/12/1978 00:00:00", "1978-12-13 00:00:00", "1978-12-13T00:00:00",
                "13.12.1978", "13-12-1978", "13/12/78"):
        _assert(to_date(txt) == date(1978, 12, 13), f"date : format « {txt} » reconnu")
    _assert(to_date("09/05/08") == date(2008, 5, 9), "date 2 chiffres récente → 2008")
    _assert(to_date("01/01/99") == date(1999, 1, 1), "date 2 chiffres future → siècle précédent (1999)")
    try:
        to_date("pas une date")
        _assert(False, "date invalide doit lever ValueError")
    except ValueError:
        _assert(True, "")

    _assert(to_bool("OUI") is True and to_bool("x") is True, "bool : OUI / x → True")
    _assert(to_bool("non") is False, "bool : non → False")
    _assert(to_bool(None) is None and to_bool("peut-être") is None, "bool : vide / inconnu → None")


# ==========================================================================
# B. clean_row
# ==========================================================================
def test_clean_row() -> None:
    d = clean_row(_row(), "f.xlsx")
    _assert(d["id_client"] == "A0100003" and d["code_client"] == "A0104688", "identifiants repris")
    _assert(d["matricule"] == "016126G" and d["matricule_norm"] == "016126G", "matricule = num_manuel")
    _assert(d["telephone"] == "01 42 87 84 80/07 07 04 73 92", "téléphone brut conservé")
    _assert(d["telephone_norm"] == "0142878480", "téléphone normalisé")
    _assert(d["cni_norm"] == "CI001490454", "CNI normalisée")
    _assert(d["date_adhesion"] == date(2008, 5, 9), "date d'adhésion convertie")
    _assert(d["employeur_code"] == "SODECI", "employeur : repli sur type_client si EMPLOYEUR(2) vide")
    _assert(d["boite_postale"] is None, "bp '0' → vide")
    _assert(d["categorie_client"] is None,
            "catégorie : NE reprend PAS categorie_client ('Individu' = type de client)")
    _assert(d["actif"] is True, "actif si pas de date de départ")
    _assert(d["extra"]["categorie_client"] == "Individu", "la ligne source complète reste dans extra")
    _assert(d["extra"]["date_naissance"] == "1978-12-13T00:00:00", "extra : dates sérialisées en JSON")
    _assert(d["source_file"] == "f.xlsx", "fichier source tracé")

    d = clean_row(_row(**{
        "employeur(2)": "cie", "categorie(1)": "CADRE", "nom_de_mere(3)": "KONE FANTA",
        "consentement_recu(4)": "OUI", "nom_client": "eba", "prenoms_client": "aka monique",
        "email": "D.Amani@GS2E.CI", "bp": "01 BP 8142 Abidjan 01", "date_depart": "30/06/2020",
    }), "f.xlsx")
    _assert(d["employeur_code"] == "CIE", "EMPLOYEUR(2) prioritaire, en majuscules")
    _assert(d["categorie_client"] == "CADRE", "catégorie = CATEGORIE(1)")
    _assert(d["nom_mere"] == "KONE FANTA" and d["consentement_recu"] is True, "colonnes MA2E (3) et (4)")
    _assert(d["nom"] == "EBA" and d["prenoms"] == "AKA MONIQUE", "nom / prénoms en majuscules")
    _assert(d["email"] == "d.amani@gs2e.ci", "email en minuscules")
    _assert(d["boite_postale"] == "01 BP 8142 Abidjan 01", "boîte postale reprise de bp")
    _assert(d["actif"] is False and d["date_depart"] == date(2020, 6, 30), "inactif si date de départ")

    for bad, label in [({"id_client": None}, "id_client"), ({"id_client": "  "}, "id_client blanc"),
                       ({"nom_client": None}, "nom_client")]:
        try:
            clean_row(_row(**bad), "f")
            _assert(False, f"ligne sans {label} doit être rejetée")
        except ValueError:
            _assert(True, "")

    long = clean_row(_row(nom_client="X" * 400), "f")
    _assert(len(long["nom"]) == 255, "valeurs tronquées à la taille de colonne")

    # Une date illisible NE rejette PAS le sociétaire : vide + avertissement
    w: list[str] = []
    d = clean_row(_row(date_naissance="31/31/1978", date_adhesion="bientôt"), "f", w)
    _assert(d["date_naissance"] is None and d["date_adhesion"] is None, "date illisible → laissée vide")
    _assert(len(w) == 2 and "date_naissance" in w[0] and "date_adhesion" in w[1], "2 avertissements, un par date")

    # Matricule saisi comme nombre dans Excel : importé, « 6 » (pas « 6.0 »), signalé
    w = []
    d = clean_row(_row(num_manuel=6.0), "f", w)
    _assert(d["matricule"] == "6", "matricule nombre → « 6 », jamais « 6.0 »")
    _assert(any("num_manuel" in x for x in w), "matricule nombre → avertissement zéros perdus")
    w = []
    clean_row(_row(num_manuel="00006"), "f", w)
    _assert(w == [], "matricule texte → aucun avertissement")


# ==========================================================================
# C. import_societaires (fausse session)
# ==========================================================================
def test_import_logic() -> None:
    # Fichier qui n'est pas la base MA2E
    try:
        _run([{"matricule": "X", "nom": "Y"}])
        _assert(False, "colonnes obligatoires absentes → ValueError")
    except ValueError as e:
        _assert("id_client" in str(e), "le message cite la colonne manquante")

    # 4 lignes valides, aucune en base → 4 créées
    rows = [_row(id_client=f"A{i}") for i in range(4)]
    db, rep = _run(rows)
    _assert((rep.accepted, rep.updated, rep.rejected) == (4, 0, 0), "4 créées")
    _assert(db.rows_written() == 4, "4 lignes envoyées à la base")

    # Ré-import : toutes déjà en base → 4 mises à jour, 0 créée (pas de doublon)
    db, rep = _run(rows, existing={"A0", "A1", "A2", "A3"})
    _assert((rep.accepted, rep.updated) == (0, 4), "ré-import = mises à jour")

    # Mélange : 1 existante, 1 nouvelle, 1 sans id, 1 sans nom, 1 doublon, 1 date invalide
    rows = [_row(id_client="OLD"), _row(id_client="NEW"), _row(id_client=None),
            _row(id_client="NONOM", nom_client=""), _row(id_client="NEW"),
            _row(id_client="BADDATE", date_naissance="31/31/1990")]
    db, rep = _run(rows, existing={"OLD"})
    _assert((rep.accepted, rep.updated, rep.rejected) == (2, 1, 3),
            f"2 créées (dont la date illisible), 1 mise à jour, 3 rejetées "
            f"(obtenu {rep.accepted}/{rep.updated}/{rep.rejected})")
    lines = sorted(e["line"] for e in rep.errors)
    _assert(lines == [4, 5, 6], f"n° de ligne Excel des rejets (en-tête = ligne 1) : {lines}")
    _assert(any("Doublon" in e["error"] for e in rep.errors), "doublon d'id_client signalé")
    _assert([(x["line"], x["id_client"]) for x in rep.warnings] == [(7, "BADDATE")],
            f"date illisible signalée en avertissement, ligne 7 : {rep.warnings}")
    _assert(db.rows_written() == 3, "les lignes valides sont écrites malgré les rejets")

    # Simulation : compte mais n'écrit rien
    db, rep = _run([_row(id_client="A"), _row(id_client="B")], existing={"A"}, dry_run=True)
    _assert((rep.accepted, rep.updated) == (1, 1), "simulation : comptes corrects")
    _assert(db.inserts == [], "simulation : AUCUNE écriture")

    # Gros volume : écriture par lots
    n = BATCH_SIZE * 2 + 7
    db, rep = _run([_row(id_client=f"B{i}") for i in range(n)])
    _assert(len(db.inserts) == 3, f"{n} lignes → 3 lots de {BATCH_SIZE} max")
    _assert(db.rows_written() == n and rep.accepted == n, "toutes les lignes écrites")

    # Clé d'upsert
    sql = str(db.inserts[0].compile(dialect=postgresql.dialect()))
    _assert("ON CONFLICT ON CONSTRAINT uq_societaire_id_client DO UPDATE" in sql,
            "upsert sur (tenant_id, id_client)")

    # Fichier vide : rien à faire
    db, rep = _run([])
    _assert(rep.accepted == 0 and db.inserts == [], "fichier vide : aucune écriture")

    # Fichier PARTIEL (quelques colonnes) : un sociétaire existant ne doit perdre aucune
    # des autres colonnes importées avant (date d'adhésion, lieu de naissance...).
    from app.services.societaire_import import COLUMN_SOURCES, updatable_columns
    partial = [{"id_client": "OLD", "nom_client": "X", "telephone": "0707070707"}]
    db, rep = _run(partial, existing={"OLD"})
    sql = str(db.inserts[0].compile(dialect=postgresql.dialect()))
    set_part = sql.split("DO UPDATE SET", 1)[1]
    import re as _re
    set_cols = set(_re.findall(r"(?:^\s*|, )(\w+) = ", set_part))
    for col in ("telephone", "telephone_norm", "nom"):
        _assert(col in set_cols, f"partiel : {col} mis à jour")
    for col in ("date_adhesion", "lieu_naissance", "matricule", "email", "actif", "employeur_code"):
        _assert(col not in set_cols, f"partiel : {col} NON écrasé")
    _assert("telephone = coalesce(excluded.telephone, societaires.telephone)" in set_part,
            "cellule vide / illisible : la valeur existante est conservée")
    _assert("nom = excluded.nom" in set_part, "nom (obligatoire) : toujours remplacé")
    db, _ = _run([{"id_client": "OLD", "nom_client": "X", "date_depart": "01/01/2020"}], existing={"OLD"})
    set_part = str(db.inserts[0].compile(dialect=postgresql.dialect())).split("DO UPDATE SET", 1)[1]
    _assert("actif = (coalesce(excluded.date_depart, societaires.date_depart) IS NULL)" in set_part,
            "actif recalculé sur la date de départ finale")
    _assert("extra = (societaires.extra || excluded.extra)" in set_part,
            "extra fusionné (jsonb ||) : historique _modifications conservé")

    # Fichier complet : toutes les colonnes mises à jour
    cols = clean_row(_row(), "f").keys()
    full = updatable_columns({_norm(h) for h in SOURCE_HEADERS}, cols)
    _assert(set(full) == set(cols) - {"id_client", "extra"}, "fichier complet : toutes les colonnes")
    # Garde-fou : toute nouvelle colonne de clean_row doit être déclarée dans COLUMN_SOURCES
    undeclared = set(cols) - set(COLUMN_SOURCES) - {"id_client", "extra", "nom", "source_file"}
    _assert(not undeclared, f"colonnes absentes de COLUMN_SOURCES : {undeclared}")


# ==========================================================================
# D. import_referential depuis un vrai .xlsx
# ==========================================================================
def _xlsx(rows: list[list]) -> bytes:
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(SOURCE_HEADERS)
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _line(**vals) -> list:
    return [vals.get(_norm(h)) for h in SOURCE_HEADERS]


def test_xlsx_end_to_end() -> None:
    raw = _xlsx([
        _line(id_client="A0100027", nom_client="DOUABOU", num_manuel="00006",
              type_client="GS2E", **{"categorie(1)": "CADRE"}),
        [None] * len(SOURCE_HEADERS),                       # ligne vide : ignorée
        _line(id_client="A0100031", nom_client="MANDA", telephone="0757109672"),
    ])
    db = _FakeDB()
    rep = asyncio.run(importer_service.import_referential(
        db, tenant_id=uuid4(), target="societaires", filename="Fichier Source.xlsx", raw_bytes=raw))
    _assert(rep.total_lines == 2, f"ligne vide ignorée (total {rep.total_lines})")
    _assert(rep.accepted == 2 and rep.rejected == 0, "2 lignes importées depuis le .xlsx")

    # Les en-têtes « CATEGORIE(1) » etc. sont bien reconnus après normalisation
    rows = importer_service._parse_file("f.xlsx", raw)
    _assert("categorie(1)" in rows[0] and "nom_de_mere(3)" in rows[0], "en-têtes MA2E normalisés")
    _assert(clean_row(rows[0], "f")["categorie_client"] == "CADRE", "CATEGORIE(1) lue depuis le .xlsx")
    _assert(clean_row(rows[0], "f")["matricule"] == "00006", "matricule texte conservé tel quel")

    # Simulation de bout en bout
    db = _FakeDB()
    rep = asyncio.run(importer_service.import_referential(
        db, tenant_id=uuid4(), target="societaires", filename="f.xlsx", raw_bytes=raw, dry_run=True))
    _assert(rep.dry_run is True and db.inserts == [], "dry_run transmis jusqu'au service")

    # Limite de taille : 50 Mo pour les sociétaires, 10 Mo pour les autres cibles
    big = b"0" * (11 * 1024 * 1024)
    try:
        asyncio.run(importer_service.import_referential(
            _FakeDB(), tenant_id=uuid4(), target="employeurs", filename="e.csv", raw_bytes=big))
        _assert(False, "11 Mo refusé pour employeurs")
    except ValueError as e:
        _assert("volumineux" in str(e), "11 Mo refusé pour employeurs")
    try:
        asyncio.run(importer_service.import_referential(
            _FakeDB(), tenant_id=uuid4(), target="societaires", filename="s.xlsx", raw_bytes=big))
    except ValueError as e:
        _assert("volumineux" not in str(e), "11 Mo accepté (taille) pour sociétaires")
    except Exception:
        _assert(True, "")  # contenu invalide : on ne teste ici que la taille
    huge = b"0" * (51 * 1024 * 1024)
    try:
        asyncio.run(importer_service.import_referential(
            _FakeDB(), tenant_id=uuid4(), target="societaires", filename="s.xlsx", raw_bytes=huge))
        _assert(False, "51 Mo refusé pour sociétaires")
    except ValueError as e:
        _assert("volumineux" in str(e), "51 Mo refusé pour sociétaires")

    # Formats refusés AVEC un message clair (ValueError → HTTP 422 côté API, jamais une 500)
    for fn, raw_bad, expected in [("s.pdf", b"x", "Format non supporté"),
                                  ("s.xls", b"\xd0\xcf\x11\xe0fake", ".xlsx"),
                                  ("s.xlsx", b"pas un zip", "illisible")]:
        try:
            asyncio.run(importer_service.import_referential(
                _FakeDB(), tenant_id=uuid4(), target="societaires", filename=fn, raw_bytes=raw_bad))
            _assert(False, f"{fn} refusé")
        except ValueError as e:
            _assert(expected in str(e), f"{fn} : message clair ({str(e)[:60]})")

    # Cellules Excel au format NOMBRE
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(["id_client", "nom_client", "num_manuel", "telephone"])
    ws.append(["A1", "KONE", 6, 778701287])
    ws["C2"].number_format = "00000"          # matricule affiché « 00006 » dans Excel
    ws.append(["A2", "TRAORE", 42, 707070707])  # format standard : zéros non récupérables
    buf = io.BytesIO()
    wb.save(buf)
    rows = importer_service._parse_file("n.xlsx", buf.getvalue())
    _assert(rows[0]["num_manuel"] == "00006", "format « 00000 » → zéros du matricule reconstitués")
    _assert(clean_row(rows[0], "f")["telephone_norm"] == "0778701287", "tél nombre → 0 remis")
    w: list[str] = []
    _assert(clean_row(rows[1], "f", w)["matricule"] == "42" and w, "format standard → « 42 » + avertissement")

    # CSV avec dates exportées par Excel (heure, année sur 2 chiffres), encodage Windows
    csv_raw = ("id_client;nom_client;date_naissance;date_adhesion\n"
               "A1;KONÉ;13/12/1978 00:00;09/05/08\n").encode("cp1252")
    d = clean_row(importer_service._parse_file("x.csv", csv_raw)[0], "f")
    _assert(d["nom"] == "KONÉ", "CSV cp1252 : accents conservés")
    _assert(d["date_naissance"] == date(1978, 12, 13) and d["date_adhesion"] == date(2008, 5, 9),
            "CSV : dates avec heure / sur 2 chiffres reconnues")

    _assert("societaires" in importer_service.SUPPORTED_TARGETS, "cible déclarée")
    _assert("id_client" in importer_service.template_csv("societaires"), "modèle téléchargeable")


# ==========================================================================
# E. API
# ==========================================================================
def test_api() -> None:
    from fastapi import HTTPException
    from app.api import imports
    from app.models import UserRole

    class _Ctx:
        def __init__(self, role):
            self.role = role

    for role in (UserRole.super_admin, UserRole.tenant_admin):
        imports._require_admin(_Ctx(role))  # ne lève pas
        _assert(True, "")
    for role in [r for r in UserRole if r not in (UserRole.super_admin, UserRole.tenant_admin)]:
        try:
            imports._require_admin(_Ctx(role))
            _assert(False, f"rôle {role.value} doit être refusé")
        except HTTPException as e:
            _assert(e.status_code == 403, f"rôle {role.value} → 403")

    params = inspect.signature(imports.import_referential).parameters
    _assert("dry_run" in params, "paramètre dry_run exposé par l'API")
    _assert(params["dry_run"].default.default is False, "dry_run désactivé par défaut")


def main() -> int:
    for t in (test_normalisation, test_clean_row, test_import_logic, test_xlsx_end_to_end, test_api):
        t()
        print(f"  ✓ {t.__name__}")
    print(f"OK — tous les asserts passent ({CHECKS})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
