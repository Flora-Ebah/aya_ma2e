"""Tâche 06 — longueur des matricules : un intervalle (min / max) COMMUN à toutes les entités du groupe,
réglé au-dessus de la liste « Employeurs du groupe » ; liste datée (plus récent en haut) et reliée à la
table `employeurs`. Lancer : python -m tests.test_matricule_format"""
from __future__ import annotations

import asyncio
import inspect
import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace as NS

from fastapi import HTTPException

from app.services import matricule_format as mf
from app.services import reference_list_service as rls

CHECKS = 0
ROOT = Path(__file__).resolve().parents[2]
R = mf.MatriculeRule


def _assert(c, m):
    global CHECKS
    CHECKS += 1
    if not c:
        raise AssertionError(m)


def test_rule_validation() -> None:
    mf.check_rule(None, None)
    mf.check_rule(3, 5)
    mf.check_rule(4, 4)
    for lo, hi, why in ((0, 5, "min 0"), (3, 65, "max > 64"), (6, 5, "min > max"), (-1, None, "négatif")):
        try:
            mf.check_rule(lo, hi)
        except ValueError as e:
            _assert(str(e), f"message FR : {why}")
        else:
            raise AssertionError(f"intervalle accepté à tort : {why}")
    _assert(mf.rule_from_config({"matricule_min_len": 3, "matricule_max_len": 5}) == R(3, 5), "lu depuis la config")
    _assert(not mf.rule_from_config(None).is_set and not mf.rule_from_config({}).is_set, "config vide : pas de règle")
    _assert(mf.rule_from_config({"matricule_min_len": "3", "matricule_max_len": True}) == R(), "valeur corrompue ignorée")


def test_length() -> None:
    r = R(min_len=3, max_len=5)
    _assert(mf.matches(r, "ABC") and mf.matches(r, "12345") and mf.matches(r, "a-1 2"), "dans l'intervalle (normalisé)")
    _assert(mf.matches(r, "A1B2") and mf.matches(r, "0123"), "alphanumérique ET numérique acceptés")
    _assert(not mf.matches(r, "AB") and not mf.matches(r, "123456"), "hors intervalle")
    _assert(mf.matches(R(min_len=4), "123456") and not mf.matches(R(min_len=4), "123"), "minimum seul")
    _assert(mf.matches(R(max_len=4), "1") and not mf.matches(R(max_len=4), "12345"), "maximum seul")
    _assert(mf.matches(R(5, 5), "00012") and not mf.matches(R(5, 5), "0012"), "zéros de tête comptés")
    _assert(not mf.matches(r, "") and not mf.matches(r, "  "), "vide refusé")
    _assert(mf.matches(R(), "n'importe quoi") and mf.matches(None, "x"), "sans règle : aucun contrôle")


def test_messages() -> None:
    r = R(3, 5)
    m = mf.validate("12", r)
    _assert(m == "Le matricule « 12 » doit comporter entre 3 et 5 caractères (règle commune aux entités du groupe).",
            f"message : {m}")
    _assert(mf.validate("123", r) is None, "valide -> None")
    _assert(R(4, 4).describe() == "4 caractères" and R(1, None).describe() == "au moins 1 caractère", "libellés")
    _assert(mf.chat_error("123", r) is None, "chat : valide")
    e = mf.chat_error("1", r)
    _assert(e and "entre 3 et 5 caractères" in e, "chat : longueur attendue rappelée")


class _Res:
    def __init__(self, rows): self.rows = rows
    def scalar_one_or_none(self): return self.rows[0] if self.rows else None
    def scalars(self): return iter(self.rows)


class _FakeDB:
    def __init__(self, *results): self.results = list(results); self.added = []
    async def execute(self, *_a, **_k): return _Res(self.results.pop(0))
    def add(self, o): self.added.append(o)
    async def flush(self): pass
    async def commit(self): pass


def test_chat_action() -> None:
    from app.conversation.default_actions import verify_matricule_referentiel as fn
    tid = str(uuid.uuid4())
    liste = NS(key="employeurs", config={"matricule_min_len": 5, "matricule_max_len": 7})
    run = lambda db, saisie: asyncio.run(fn(db, {"_tenant_id": tid, "ask_matricule": saisie}, saisie))
    r = run(_FakeDB([], [liste]), "AB12")
    _assert(r.branch_key == "not_found" and "entre 5 et 7" in (r.message or ""), "trop court -> retour à la saisie")
    r = run(_FakeDB([], [liste]), "A99999")
    _assert(r.branch_key is None and r.extra_context["matricule_verified"] is False, "bonne longueur hors référentiel")
    r = run(_FakeDB([], [NS(key="employeurs", config={})]), "X")
    _assert(r.branch_key is None, "sans intervalle : inchangé")
    collab = NS(prenoms="A", nom="B", employeur_code="CIE", fonction="F", id=uuid.uuid4())
    r = run(_FakeDB([collab]), "AB")
    _assert(r.extra_context["matricule_verified"] is True, "présent au référentiel : jamais bloqué")


def test_save_rule() -> None:
    tid = uuid.uuid4()
    rl = NS(id=uuid.uuid4(), key="employeurs", config={"autre": 1})
    logs = []

    async def _log(db, **kw): logs.append(kw)
    from app.services import audit_service
    orig = audit_service.log
    audit_service.log = _log
    try:
        run = lambda changes, target=rl: asyncio.run(rls._apply_matricule_rule(None, tid, target, changes, uuid.uuid4()))
        run({"matricule_min_len": 3, "matricule_max_len": 5})
        _assert(rl.config == {"autre": 1, "matricule_min_len": 3, "matricule_max_len": 5} and len(logs) == 1,
                "intervalle enregistré + journalisé")
        run({"matricule_max_len": None})
        _assert(rl.config == {"autre": 1, "matricule_min_len": 3}, "null = pas de maximum ; le reste est gardé")
        run({"matricule_min_len": 3})
        _assert(len(logs) == 2, "rien de changé : pas de journal")
        for bad in ({"matricule_max_len": 2}, {"matricule_min_len": 0}, {"matricule_max_len": 99}):
            try:
                run(bad)
            except HTTPException as exc:
                _assert(exc.status_code == 422, f"refus 422 : {bad}")
            else:
                raise AssertionError(f"intervalle accepté à tort : {bad}")
        _assert(rl.config == {"autre": 1, "matricule_min_len": 3}, "refus : config inchangée")
        try:
            run({"matricule_min_len": 3}, NS(id=uuid.uuid4(), key="civilites", config={}))
        except HTTPException as exc:
            _assert(exc.status_code == 400, "autre liste : refusé")
        else:
            raise AssertionError("intervalle accepté sur une autre liste")
    finally:
        audit_service.log = orig


def test_list_order() -> None:
    items = [{"code": "a", "label": "A", "added_at": "2026-01-01T00:00:00+00:00"},
             {"code": "new1", "label": "NEW1"}, {"code": "new2", "label": "NEW2"},
             {"code": "b", "label": "B", "added_at": "2026-03-01T00:00:00+00:00"}]
    out = rls.sort_by_added_at(rls.stamp_new_items(items, datetime(2026, 11, 16, tzinfo=timezone.utc)))
    _assert([i["code"] for i in out] == ["new1", "new2", "b", "a"], f"plus récent en haut : {[i['code'] for i in out]}")
    norm = rls._normalize_items([{"label": "X", "added_at": "2026-02-02T00:00:00+00:00"}, {"label": "Y"}])
    _assert(norm[0]["added_at"].startswith("2026-02-02") and "added_at" not in norm[1], "added_at gardé")


def test_sync_employeurs() -> None:
    from app.models import Employeur
    tid = uuid.uuid4()
    cie = Employeur(tenant_id=tid, code="CIE", name="CIE", is_active=True)
    sde = Employeur(tenant_id=tid, code="SDE", name="SDE", is_active=True)
    autre = Employeur(tenant_id=tid, code="AUTRE", name="Autre", is_active=True)
    db = _FakeDB([cie, sde, autre])
    asyncio.run(rls.sync_employeurs(db, tid, [{"code": "cie", "label": "CIE"}, {"code": "sde", "label": "SDE"}],
                                    [{"code": "nouvelle", "label": "Nouvelle Société"}, {"code": "cie", "label": "CIE"}]))
    _assert(len(db.added) == 1 and db.added[0].code == "NOUVELLE", "employeur ajouté -> créé")
    _assert(sde.is_active is False and cie.is_active and autre.is_active, "retiré -> désactivé, autres intacts")


def test_chronology_migration() -> None:
    rl = NS(key="employeurs", created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            items=[{"code": "gs2e", "label": "GS2E"}, {"code": "cie", "label": "CIE"}, {"code": "sde", "label": "SDE"}])
    from app.models import Employeur
    tid = uuid.uuid4()
    db = _FakeDB([rl], [Employeur(tenant_id=tid, code=c, name=c, is_active=True) for c in ("GS2E", "CIE", "SDE", "CIPREL")])
    _assert(asyncio.run(rls.ensure_employeurs_chronology(db, tid)) and
            [i["code"] for i in rl.items] == ["ciprel", "sde", "cie", "gs2e"], "CIPREL en haut, plus ancien en bas")
    _assert(asyncio.run(rls.ensure_employeurs_chronology(_FakeDB([rl]), tid)) is False, "une seule fois")


def test_wiring() -> None:
    from app.api import collaborateurs, employeurs, reference_lists
    from app.models import Employeur, ReferenceList
    from app.services import importer_service, societaire_import

    _assert(hasattr(ReferenceList, "config"), "colonne config de la liste")
    _assert(not any(hasattr(Employeur, c) for c in ("matricule_min_len", "matricule_max_len", "matricule_types")),
            "plus de règle par employeur")
    boot = (ROOT / "backend/app/bootstrap.py").read_text(encoding="utf-8")
    _assert("ALTER TABLE reference_lists ADD COLUMN IF NOT EXISTS config" in boot, "migration idempotente")
    _assert(not ({"matricule_types", "matricule_exemple", "matricule_min_len"} & set(employeurs.EmployeurUpdateIn.model_fields)),
            "type / exemple / intervalle retirés de l'API employeur")
    _assert({"matricule_min_len", "matricule_max_len"} <= set(reference_lists.UpdateIn.model_fields)
            and "config" in reference_lists.ReferenceListOut.model_fields, "intervalle exposé sur la liste")
    src = inspect.getsource(collaborateurs.create_collaborateur)
    _assert("validate_matricule(" in src and src.index("validate_matricule(") < src.index("db.add(row)"),
            "ajout unitaire : contrôlé avant l'écriture")
    imp = inspect.getsource(importer_service._import_collaborateurs)
    _assert("load_rule(" in imp and "report.add_error(i, msg, row)" in imp, "import référentiel : ligne rejetée")
    soc = inspect.getsource(societaire_import.import_societaires)
    _assert("validate_matricule(" in soc and "row_warnings.append(msg" in soc, "import base MA2E : avertissement")
    _assert("_apply_matricule_rule(" in inspect.getsource(rls.update_list), "enregistré avec la liste")

    front = ROOT / "frontend"
    page = (front / "app/(app)/assistante/listes/page.tsx").read_text(encoding="utf-8")
    _assert("Alphanumérique" not in page and "Exemple de matricule" not in page and "Tester un matricule" not in page,
            "type de caractère, exemple et test supprimés")
    _assert("Longueur des matricules (toutes les entités du groupe)" in page, "min / max au-dessus de la liste")
    _assert(page.index("Longueur des matricules (toutes les entités") < page.index("Items ({items.length})"),
            "placé AU-DESSUS des employeurs")
    _assert("api.updateEmployeur" not in page and "matricule_min_len: matMin.trim()" in page,
            "une seule requête (liste + intervalle)")
    _assert('[{ label: "", synonyms: [] }, ...prev]' in page, "nouvel employeur ajouté en haut")
    _assert("matricule_types" not in (front / "lib/api.ts").read_text(encoding="utf-8"), "client API nettoyé")


def main() -> int:
    for t in (test_rule_validation, test_length, test_messages, test_chat_action, test_save_rule,
              test_list_order, test_sync_employeurs, test_chronology_migration, test_wiring):
        t()
        print(f"  ✓ {t.__name__}")
    print(f"OK — tous les asserts passent ({CHECKS})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
