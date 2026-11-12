"""Tests : GET /api/collaborateurs/stats (fenêtre « Référentiel des sociétaires ERANOVE » : chiffres, liste, export, historique).

Sans base de données : on vérifie le contrat de la route, son ordre de déclaration, la
protection administrateur, le SQL du « dernier import » (un import refusé ne compte pas) et la
forme de la réponse avec une fausse session.

Lancer :
    python -m tests.test_collaborateurs_stats
"""
from __future__ import annotations

import asyncio
import inspect
import os
import re
import sys
import types
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import HTTPException  # noqa: E402

from app.api import collaborateurs as api  # noqa: E402
from app.models import UserRole  # noqa: E402

CHECKS = 0
BACKEND = Path(__file__).resolve().parents[1]


def _assert(cond: bool, msg: str) -> None:
    global CHECKS
    if not cond:
        print(f"FAIL: {msg}", file=sys.stderr)
        raise AssertionError(msg)
    CHECKS += 1


def test_route_order_and_access() -> None:
    src = (BACKEND / "app/api/collaborateurs.py").read_text(encoding="utf-8")
    routes = re.findall(r'^@router\.(?:get|post|patch|delete)\("([^"]*)"', src, flags=re.M)
    _assert("/stats" in routes, "route /stats déclarée")
    _assert(routes.index("/stats") < routes.index("/{collab_id}"),
            "/stats déclarée AVANT /{collab_id} (sinon « stats » serait lu comme un identifiant)")

    code = inspect.getsource(api.stats)
    _assert(code.split("await ", 1)[0].count("_require_admin(ctx)") == 1 or "_require_admin(ctx)" in code.split("select(")[0],
            "accès administrateur vérifié avant toute requête")
    _assert("_resolve_tenant(ctx)" in code and code.count("tenant_id") >= 4, "toutes les requêtes limitées au tenant")

    class _Ctx:
        def __init__(self, role):
            self.role = role

    for role in [r for r in UserRole if r not in (UserRole.super_admin, UserRole.tenant_admin)]:
        try:
            api._require_admin(_Ctx(role))
            _assert(False, f"rôle {role.value} doit être refusé")
        except HTTPException as e:
            _assert(e.status_code == 403, f"rôle {role.value} → 403")


def test_last_import_sql() -> None:
    code = inspect.getsource(api.stats)
    _assert('AuditLog.resource_type == "import:collaborateurs"' in code, "dernier import = audit des imports du référentiel")
    _assert('AuditLog.details["accepted"].astext.cast(Integer) > 0' in code,
            "un import REFUSÉ (0 ligne insérée) n'est jamais présenté comme « dernier import »")
    _assert("desc(AuditLog.created_at)" in code and ".limit(1)" in code, "le plus récent d'abord")
    _assert("Societaire.imported_at" in code, "dernière importation de la base MA2E exposée")


class _Row(tuple):
    pass


class _FakeResult:
    def __init__(self, one=None, all_=None, first=None):
        self._one, self._all, self._first = one, all_, first

    def one(self):
        return self._one

    def all(self):
        return self._all

    def first(self):
        return self._first


class _FakeDB:
    """Répond aux 4 requêtes de stats() dans l'ordre : totaux, par employeur, dernier import, base MA2E."""

    def __init__(self, *, total=0, actifs=0, employeurs=(), last=None, base=(0, None)):
        self.results = [
            _FakeResult(one=(total, actifs)), _FakeResult(all_=list(employeurs)),
            _FakeResult(first=last), _FakeResult(one=base),
        ]

    async def execute(self, stmt):
        return self.results.pop(0)


def _call(db):
    ctx = types.SimpleNamespace(role=UserRole.tenant_admin, tenant_id=uuid.uuid4())
    return asyncio.run(api.stats(db=db, ctx=ctx))


def test_response_shape() -> None:
    # Référentiel vide, base MA2E chargée (le cas de la capture d'écran)
    r = _call(_FakeDB(base=(4, datetime(2026, 11, 11, 11, 47, tzinfo=timezone.utc))))
    _assert(r["total"] == 0 and r["actifs"] == 0 and r["par_employeur"] == [], "référentiel vide")
    _assert(r["dernier_import"] is None, "aucun import : dernier_import = null")
    _assert(r["base_ma2e"]["total"] == 4 and r["base_ma2e"]["dernier_import"].startswith("2026-11-11T11:47"),
            "base MA2E comptée séparément")

    # Référentiel chargé
    last = (datetime(2026, 11, 11, 12, 1, 32, tzinfo=timezone.utc), {"filename": "ref.csv", "accepted": 2})
    r = _call(_FakeDB(total=3, actifs=2, employeurs=[("CIE", 2), ("SODECI", 1)], last=last))
    _assert((r["total"], r["actifs"]) == (3, 2), "total et actifs")
    _assert(r["par_employeur"] == [{"code": "CIE", "total": 2}, {"code": "SODECI", "total": 1}], "répartition par employeur")
    _assert(r["dernier_import"] == {"date": "2026-11-11T12:01:32+00:00", "fichier": "ref.csv", "lignes": 2},
            "dernier import : date, fichier, lignes")
    _assert(r["base_ma2e"] == {"total": 0, "dernier_import": None}, "base MA2E vide")

    # Détails d'audit incomplets : pas d'erreur
    r = _call(_FakeDB(total=1, actifs=1, last=(datetime(2026, 1, 1, tzinfo=timezone.utc), None)))
    _assert(r["dernier_import"]["fichier"] is None and r["dernier_import"]["lignes"] is None, "détails absents tolérés")


def test_frontend_wiring() -> None:
    front = BACKEND.parent / "frontend"
    page = (front / "app/(app)/assistante/listes/page.tsx").read_text(encoding="utf-8")
    _assert("api.collaborateursStats()" in page, "la page lit /api/collaborateurs/stats")
    _assert("listCollaborateurs({ limit: 1000 })" not in page, "plus de compteur plafonné à 1000 lignes")
    _assert("Référentiel des sociétaires ERANOVE" in page, "titre de la fenêtre")
    _assert("Cette liste n&apos;est" not in page, "plus de bandeau ni compteur « dossiers importés » dans la fenêtre")
    _assert("voir dans Dossiers" not in page, "plus de renvoi vers les dossiers importés dans la liste des valeurs")
    _assert("collaborateursStats" in (front / "lib/api.ts").read_text(encoding="utf-8"), "client API")


# ============================================================ étape 3 : liste paginée + export
def _sql(*conds) -> str:
    from sqlalchemy import select
    from sqlalchemy.dialects import postgresql
    from app.models import Collaborateur
    return str(select(Collaborateur.id).where(*conds).compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))


def test_search_filters() -> None:
    t = uuid.uuid4()
    sql = _sql(*api.search_filters(t, None, None, None))
    _assert(f"tenant_id = '{t}'" in sql and " OR " not in sql, "sans critère : seulement le filtre de tenant")
    sql = _sql(*api.search_filters(t, " t 001 ", None, None))
    _assert("= 'T001'" in sql, "matricule normalisé : « t 001 » retrouve « T-001 »")
    for col in ("matricule", "nom", "prenoms", "email", "fonction"):
        _assert(f"collaborateurs.{col} ILIKE" in sql, f"recherche sur {col}")
    _assert("concat(collaborateurs.nom, ' ', collaborateurs.prenoms)" in sql
            and "concat(collaborateurs.prenoms, ' ', collaborateurs.nom)" in sql,
            "« nom prénoms » et « prénoms nom » cherchés ensemble")
    sql = _sql(*api.search_filters(t, None, "cie", "retraite"))
    _assert("employeur_code = 'CIE'" in sql, "employeur insensible à la casse (majuscules)")
    _assert("statut = 'retraite'" in sql, "filtre de statut")
    _assert(set(api.SORTS) == {"nom", "matricule", "employeur", "recent"}, "tris autorisés")
    _assert(set(api.STATUTS) == {"actif", "retraite", "demission", "licencie", "inactif"}, "statuts connus")


def test_search_route_contract() -> None:
    p = inspect.signature(api.search).parameters
    _assert(p["page"].default.default == 1 and p["page_size"].default.default == 25, "page 1, 25 lignes par défaut")
    code = inspect.getsource(api.search)
    _assert(code.index("_require_admin(ctx)") < code.index("db.execute"), "accès administrateur AVANT toute requête")
    _assert("func.count()" in code and ".offset((page - 1) * page_size).limit(page_size)" in code,
            "total + pagination côté serveur")
    _assert('"total": total' in code, "le total est renvoyé")
    _assert("le=200" in inspect.getsource(api).split("async def search(")[1].split("db: AsyncSession")[0],
            "page_size borné à 200 (pas de liste illimitée)")
    src = (BACKEND / "app/api/collaborateurs.py").read_text(encoding="utf-8")
    routes = re.findall(r'^@router\.(?:get|post|patch|delete)\("([^"]*)"', src, flags=re.M)
    for r in ("/search", "/export.csv", "/stats"):
        _assert(routes.index(r) < routes.index("/{collab_id}"), f"{r} déclarée avant /{{collab_id}}")


def test_csv_export() -> None:
    c = api.csv_cell
    _assert(c(None) == "" and c("") == "", "vide")
    _assert(c("Technicien") == "Technicien", "texte simple inchangé")
    _assert(c("KONÉ") == "KONÉ", "accents conservés")
    for dangerous in ("=1+1", "+33612345678", "-1+1", "@SUM(A1)", "\tcmd"):
        _assert(c(dangerous).lstrip('"').startswith("'"), f"formule Excel neutralisée : {dangerous!r}")
    got = c('=HYPERLINK("http://x")')
    _assert(got == "\"'=HYPERLINK(\"\"http://x\"\")\"", "formule + guillemets : neutralisée ET protégée")
    _assert(c("Chef; réseau") == '"Chef; réseau"', "point-virgule protégé par des guillemets")
    _assert(c('Dit "oui"') == '"Dit ""oui"""', "guillemets doublés")
    _assert("\n" not in c("a\nb") and "\r" not in c("a\rb"), "retours à la ligne supprimés (une ligne = un matricule)")
    _assert(c(date(2015, 6, 12)) == "2015-06-12", "date au format ISO (ré-importable)")
    _assert(api.CSV_COLUMNS == ["matricule", "employeur_code", "nom", "prenoms", "email", "telephone",
                                "fonction", "date_embauche", "statut"], "mêmes colonnes que le modèle d'import")
    from app.services.importer_service import template_csv
    _assert(template_csv("collaborateurs").lstrip("﻿").splitlines()[0] == ";".join(api.CSV_COLUMNS),
            "en-tête de l'export = en-tête du modèle d'import (fichier ré-importable)")

    code = inspect.getsource(api.export_csv)
    _assert(code.index("_require_admin(ctx)") < code.index("db.execute"), "export : accès administrateur AVANT toute requête")
    _assert("AuditAction.data_export" in code and "export:collaborateurs" in code, "export tracé dans le journal d'audit")
    _assert("EXPORT_MAX_ROWS" in code and api.EXPORT_MAX_ROWS == 100_000, "export plafonné")
    _assert("ufeff" in code, "BOM UTF-8 (accents lus correctement par Excel)")


def test_patch_hardening() -> None:
    code = inspect.getsource(api.update_collaborateur)
    _assert('field in ("nom", "prenoms", "statut")' in code and "continue" in code,
            "PATCH : un « null » sur un champ obligatoire est ignoré (pas d'erreur 500)")


def test_frontend_step3() -> None:
    front = BACKEND.parent / "frontend"
    page = (front / "app/(app)/assistante/listes/page.tsx").read_text(encoding="utf-8")
    # Décision produit : la fenêtre du référentiel n'affiche QUE l'historique (plus de liste « Sociétaires »)
    for gone in ("api.searchCollaborateurs(", "collaborateursExportUrl", "Exporter CSV", "Le référentiel est vide",
                 "api.deleteCollaborateur(", "REF_PAGE_SIZE"):
        _assert(gone not in page, f"liste retirée de la fenêtre : {gone}")
    _assert("api.historiqueCollaborateurs(" in page and "ListPagination" in page, "historique paginé")
    _assert("setAddOpen(true)" in page and "setImportOpen(true)" in page, "boutons Ajouter / Importer conservés")
    api_ts = (front / "lib/api.ts").read_text(encoding="utf-8")
    _assert("searchCollaborateurs" in api_ts and "collaborateursExportUrl" in api_ts, "client API (routes serveur conservées)")


# ============================================================ historique des actions du référentiel
def test_describe_action() -> None:
    d = api.describe_action
    # imports
    k, lib, det = d("import:collaborateurs", "data_export", {"filename": "ref.csv", "accepted": 60, "rejected": 0, "total_lines": 60})
    _assert(k == "import" and "ref.csv" in lib and det == "60 matricules ajoutés sur 60 lignes", "import accepté")
    k, lib, det = d("import:collaborateurs", "data_export", {"filename": "ref.csv", "accepted": 1, "total_lines": 1})
    _assert(det == "1 matricule ajouté sur 1 ligne", "singulier")
    k, lib, det = d("import:collaborateurs", "data_export", {"filename": "doublon.csv", "accepted": 0, "rejected": 3, "total_lines": 3})
    _assert(k == "import_refuse" and "refusé" in lib and "3 lignes en erreur" in det and "aucun matricule" in det,
            "import refusé : distingué d'un import réussi")
    # exports
    k, lib, det = d("export:collaborateurs", "data_export", {"lignes": 750, "employeur_code": "SMB", "statut": "actif"})
    _assert(k == "export" and "750 lignes" in det and "employeur = SMB" in det and "statut = actif" in det, "export avec filtres")
    k, lib, det = d("export:collaborateurs", "data_export", {"lignes": 1})
    _assert(det == "1 ligne", "export sans filtre")
    # actions unitaires
    k, lib, det = d("collaborateur", "referentiel_added", {"matricule": "T-001", "employeur_code": "CIE"})
    _assert(k == "ajout" and lib == "Ajout du matricule T-001 (CIE)", "ajout")
    k, lib, det = d("collaborateur", "referentiel_removed", {"matricule": "T-001", "employeur_code": "CIE"})
    _assert(k == "retrait" and lib == "Retrait du matricule T-001 (CIE)", "retrait")
    k, lib, det = d("collaborateur", "referentiel_updated",
                    {"matricule": "T-001", "employeur_code": "CIE", "champs": ["fonction", "statut", "date_embauche"],
                     "statut": {"de": "actif", "vers": "retraite"}})
    _assert(k == "modification" and "fonction, statut, date d'embauche" in det and "Actif → Retraité" in det,
            "modification : champs en français + statut avant → après")
    k, lib, det = d("collaborateur", "referentiel_updated", {})
    _assert(k == "modification" and "?" in lib, "détails absents tolérés")


def test_history_privacy_and_wiring() -> None:
    from app.models import AuditAction
    for v in ("referentiel_added", "referentiel_updated", "referentiel_removed"):
        _assert(v in [a.value for a in AuditAction], f"valeur d'audit {v}")
    boot = (BACKEND / "app/bootstrap.py").read_text(encoding="utf-8")
    _assert(all(f"\"{v}\"" in boot for v in ("referentiel_added", "referentiel_updated", "referentiel_removed"))
            and "ALTER TYPE audit_action ADD VALUE IF NOT EXISTS" in boot,
            "migration idempotente du type PostgreSQL existant")

    create = inspect.getsource(api.create_collaborateur)
    update = inspect.getsource(api.update_collaborateur)
    delete = inspect.getsource(api.delete_collaborateur)
    _assert("AuditAction.referentiel_added" in create, "création tracée")
    _assert("AuditAction.referentiel_updated" in update, "modification tracée")
    _assert("AuditAction.referentiel_removed" in delete and delete.index("_audit(") < delete.index("db.delete(row)"),
            "retrait tracé AVANT la suppression de la ligne")
    _assert("if changed:" in update, "une modification sans effet réel n'est pas tracée")
    # Vie privée : le journal est en ajout seul (non effaçable) -> jamais de nom / e-mail / téléphone
    for name, code in (("création", create), ("modification", update), ("retrait", delete)):
        audit_calls = [l for l in code.splitlines() if "details" in l or "matricule" in l and "employeur_code" in l]
        _assert(not any(w in " ".join(audit_calls) for w in ("row.nom", "row.prenoms", "row.email", "row.telephone", "payload.email")),
                f"{name} : aucun nom / e-mail / téléphone dans le journal d'audit")
    _assert('"champs": changed' in update and "statut_avant" in update, "modification : NOMS des champs, jamais leurs valeurs")


def test_history_endpoint() -> None:
    p = inspect.signature(api.historique).parameters
    _assert(p["page"].default.default == 1 and p["page_size"].default.default == 25, "page 1, 25 lignes par défaut")
    code = inspect.getsource(api.historique)
    _assert(code.index("_require_admin(ctx)") < code.index("db.execute"), "accès administrateur AVANT toute requête")
    _assert("AuditLog.tenant_id == tenant_id" in code and "HISTORY_RESOURCES" in code, "limité au tenant et aux actions du référentiel")
    _assert(set(api.HISTORY_RESOURCES) == {"collaborateur", "import:collaborateurs", "export:collaborateurs"},
            "ressources d'audit lues (les imports de la base MA2E n'y figurent pas)")
    _assert("desc(AuditLog.created_at)" in code and ".offset((page - 1) * page_size).limit(page_size)" in code,
            "du plus récent au plus ancien, paginé côté serveur")
    _assert('"Système"' in code and "Utilisateur supprimé" in code, "auteur absent : libellé de repli")
    _assert("le=100" in inspect.getsource(api).split("async def historique(")[1].split("db: AsyncSession")[0],
            "page_size borné à 100")
    src = (BACKEND / "app/api/collaborateurs.py").read_text(encoding="utf-8")
    routes = re.findall(r'^@router\.(?:get|post|patch|delete)\("([^"]*)"', src, flags=re.M)
    _assert(routes.index("/historique") < routes.index("/{collab_id}"), "/historique déclarée avant /{collab_id}")


def test_frontend_history_and_rename() -> None:
    front = BACKEND.parent / "frontend"
    page = (front / "app/(app)/assistante/listes/page.tsx").read_text(encoding="utf-8")
    _assert("api.historiqueCollaborateurs(" in page and "HIST_PAGE_SIZE" in page, "onglet Historique : liste paginée")
    _assert('aria-pressed={tab ===' not in page and "sa-segmented" not in page and "setTab(" not in page,
            "la fenêtre n'affiche que l'historique (plus d'onglet « Sociétaires »)")
    _assert(page.count("bumpHistory();") == 2, "les 4 actions (retrait, modification, ajout, import) rechargent l'historique")
    _assert("Aucune action enregistrée" in page, "état vide de l'historique")
    for t in ("import", "import_refuse", "export", "ajout", "modification", "retrait"):
        _assert(f"{t}: {{ label:" in page, f"pastille pour le type « {t} »")
    # Renommage demandé : « Référentiel des sociétaires ERANOVE » partout
    _assert("matricules ERANOVE" not in page and "matricules du groupe ERANOVE" not in page, "ancien nom supprimé de la page")
    _assert(page.count("Référentiel des sociétaires ERANOVE") >= 3, "nouveau nom : fenêtre, ligne et sélecteur d import")
    _assert("historiqueCollaborateurs" in (front / "lib/api.ts").read_text(encoding="utf-8"), "client API")


def main() -> int:
    for t in (test_route_order_and_access, test_last_import_sql, test_response_shape, test_frontend_wiring,
              test_search_filters, test_search_route_contract, test_csv_export, test_patch_hardening,
              test_frontend_step3, test_describe_action, test_history_privacy_and_wiring,
              test_history_endpoint, test_frontend_history_and_rename):
        t()
        print(f"  ✓ {t.__name__}")
    print(f"OK — tous les asserts passent ({CHECKS})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
