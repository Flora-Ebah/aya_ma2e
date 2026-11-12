"""Tâche 06 — matricule à format variable par employeur. Lancer : python -m tests.test_matricule_format"""
from __future__ import annotations

import asyncio
import inspect
from pathlib import Path
from types import SimpleNamespace as NS

from app.services import matricule_format as mf

CHECKS = 0
ROOT = Path(__file__).resolve().parents[2]


def _assert(c, m):
    global CHECKS
    CHECKS += 1
    if not c:
        raise AssertionError(m)


def test_check_pattern() -> None:
    _assert(mf.check_pattern(None) is None and mf.check_pattern("   ") is None, "vide -> pas de règle")
    _assert(mf.check_pattern(r" [A-Z]\d{4} ") == r"[A-Z]\d{4}", "espaces retirés")
    for bad, why in (("[", "regex invalide"), ("(a+)+", "quantificateurs imbriqués"), (r"(\w*)*b", "idem avec \\w"),
                     ("a" * 121, "trop long"), ("(", "parenthèse")):
        try:
            mf.check_pattern(bad)
        except ValueError as e:
            _assert(str(e), f"message FR pour {why}")
        else:
            raise AssertionError(f"format accepté à tort : {why}")
    _assert(mf.check_pattern("([a-z])+") == "([a-z])+", "groupe simple quantifié accepté")


def test_matches() -> None:
    p = r"[A-Z]\d{4}"
    _assert(mf.matches(p, "A1234") and mf.matches(p, "a1234"), "casse ignorée")
    _assert(mf.matches(p, "a-12 34") and mf.matches(p, "A.12/34"), "séparateurs ignorés (matricule normalisé)")
    _assert(not mf.matches(p, "A12345") and not mf.matches(p, "AB12") and not mf.matches(p, "1234A"), "correspondance ENTIÈRE")
    _assert(not mf.matches(p, "") and not mf.matches(p, "   "), "matricule vide refusé")
    _assert(not mf.matches(p, "A" * 200), "matricule démesuré refusé")
    _assert(mf.matches(None, "n'importe quoi") and mf.matches("", "x"), "sans format : aucun contrôle")
    _assert(not mf.matches("[", "A1"), "format enregistré invalide : refus, pas d'exception")
    _assert(mf.matches(r"\d{5,8}", "00123456") and not mf.matches(r"\d{5,8}", "1234"), "zéros de tête conservés, longueur variable")


def test_messages() -> None:
    m = mf.validate_for_employeur("AB12", "CIE", r"[A-Z]\d{4}", "A1234")
    _assert(m == "Le matricule « AB12 » ne respecte pas le format des matricules CIE (exemple : A1234).", "message avec exemple")
    _assert(mf.validate_for_employeur("A1234", "CIE", r"[A-Z]\d{4}", "A1234") is None, "valide -> None")
    _assert("exemple" not in mf.validate_for_employeur("x", "SMB", r"\d+", None), "sans exemple : pas de parenthèse")
    _assert(mf.validate_for_employeur("zzz", "SMB", None, None) is None, "sans format -> None")

    fm = {"CIE": (r"[A-Z]\d{4}", "A1234"), "SODECI": (r"\d{6}", "012345")}
    _assert(mf.known_format_error("A1234", fm) is None and mf.known_format_error("012345", fm) is None, "un format suffit")
    e = mf.known_format_error("QQ", fm)
    _assert(e and "CIE : A1234" in e and "SODECI : 012345" in e, "exemples de TOUS les formats listés")
    _assert(mf.known_format_error("QQ", {}) is None, "aucun format configuré -> pas de blocage")


class _Res:
    def __init__(self, rows): self.rows = rows
    def scalar_one_or_none(self): return self.rows[0] if self.rows else None
    def scalars(self): return iter(self.rows)


class _FakeDB:
    def __init__(self, *results): self.results = list(results)
    async def execute(self, *_a, **_k): return _Res(self.results.pop(0))


def test_chat_action() -> None:
    from app.conversation.default_actions import verify_matricule_referentiel as fn
    import uuid
    tid = str(uuid.uuid4())
    cie = NS(code="CIE", matricule_format=r"[A-Z]\d{4}", matricule_exemple="A1234")
    run = lambda db, saisie: asyncio.run(fn(db, {"_tenant_id": tid, "ask_matricule": saisie}, saisie))

    r = run(_FakeDB([], [cie]), "AB12")           # absent du référentiel + format inconnu
    _assert(r.branch_key == "not_found" and "format" in (r.message or "") and "A1234" in r.message, "format inconnu -> retour à la saisie")
    r = run(_FakeDB([], [cie]), "A9999")          # absent du référentiel mais format valide : accepté comme avant
    _assert(r.branch_key is None and r.extra_context["matricule_verified"] is False, "format valide hors référentiel : accepté")
    r = run(_FakeDB([], []), "N'IMPORTE QUOI")    # aucun format configuré : comportement antérieur
    _assert(r.branch_key is None and r.extra_context["matricule_verified"] is False, "sans format configuré : inchangé")
    collab = NS(prenoms="A", nom="B", employeur_code="CIE", fonction="F", id=uuid.uuid4())
    r = run(_FakeDB([collab]), "AB12")            # présent dans le référentiel : jamais bloqué par le format
    _assert(r.extra_context["matricule_verified"] is True, "présent au référentiel : pas de contrôle de format")


def test_wiring() -> None:
    from app.api import collaborateurs, employeurs
    from app.models import Employeur
    from app.services import importer_service

    _assert(hasattr(Employeur, "matricule_format") and hasattr(Employeur, "matricule_exemple"), "colonnes du modèle")
    boot = (ROOT / "backend/app/bootstrap.py").read_text(encoding="utf-8")
    _assert("ALTER TABLE employeurs ADD COLUMN IF NOT EXISTS matricule_format" in boot, "migration idempotente")
    upd = inspect.getsource(employeurs.update_employeur)
    _assert("check_pattern(" in upd and "status_code=422" in upd and "matches(" in upd, "PATCH : format validé + exemple cohérent")
    _assert("matricule_format" in employeurs.EmployeurOut.model_fields, "format exposé par l'API")
    src = inspect.getsource(collaborateurs.create_collaborateur)
    _assert("validate_for_employeur(" in src and src.index("validate_for_employeur(") < src.index("db.add(row)"),
            "ajout unitaire : format contrôlé avant l'écriture")
    imp = inspect.getsource(importer_service._import_collaborateurs)
    _assert("validate_for_employeur(" in imp and "report.add_error(i, msg, row)" in imp, "import : ligne rejetée avec message")
    from app.conversation import societaire_actions
    fs = inspect.getsource(societaire_actions.find_societaires)
    _assert('func.ltrim(Societaire.matricule_norm, "0")' in fs and "mat.isdigit()" in fs,
            "recherche : « 6 » = « 06 » = « 00006 » pour un matricule numérique")
    front = ROOT / "frontend"
    page = (front / "app/(app)/assistante/listes/page.tsx").read_text(encoding="utf-8")
    # Intégré à la liste « Employeurs du groupe » (éditeur), plus de ligne / fenêtre séparée
    _assert("MatriculeFormatsModal" not in page and "Formats de matricule par employeur" not in page and "setFormatsOpen" not in page,
            "plus d'écran séparé")
    _assert('initial?.key === "employeurs"' in page and "api.updateEmployeur(e.id, { matricule_format" in page,
            "format édité dans l'éditeur de la liste « Employeurs du groupe »")
    _assert(page.index("api.updateEmployeur(e.id, { matricule_format") < page.index("await api.updateReferenceList("),
            "formats enregistrés AVANT la liste (une erreur ne laisse rien à moitié enregistré)")
    _assert("Format du matricule" in page and "Tester un matricule" in page, "champs format / exemple / test sous chaque employeur")
    _assert("matricule_format" in (front / "lib/api.ts").read_text(encoding="utf-8"), "client API")


def main() -> int:
    for t in (test_check_pattern, test_matches, test_messages, test_chat_action, test_wiring):
        t()
        print(f"  ✓ {t.__name__}")
    print(f"OK — tous les asserts passent ({CHECKS})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
