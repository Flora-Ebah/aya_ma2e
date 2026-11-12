"""Colonne « Champs manquants » : calcul + câblage API/UI. Lancer : python -m tests.test_dossier_completude"""
from __future__ import annotations

import inspect
from pathlib import Path
from types import SimpleNamespace as NS

from app.services.dossier_completude import CHAMPS_REQUIS, champs_manquants

CHECKS = 0
FRONT = Path(__file__).resolve().parents[2] / "frontend"


def _assert(c, m):
    global CHECKS
    CHECKS += 1
    if not c:
        raise AssertionError(m)


def dossier(fonction="Technicien", situation="marie", extra=None, pieces=None):
    return NS(donnees_pro=NS(fonction=fonction, situation_familiale=situation, extra=extra or {}), pieces=pieces or [])


FULL = {"date_naissance": "1978-12-13", "lieu_naissance": "Abidjan", "numero_piece": "CI01", "domicile": "Cocody",
        "personne_a_prevenir": "Awa"}


def test_calcul() -> None:
    eu = NS(phone=None, extra={"telephone": "0700000000"})
    _assert(champs_manquants(dossier(extra=FULL), eu) == [], "dossier complet -> liste vide")
    m = champs_manquants(dossier(fonction=None, situation=None, extra={}), NS(phone=None, extra={}))
    _assert(m == [l for _, l in CHAMPS_REQUIS], "tout vide -> tous les champs, dans l'ordre")
    _assert(champs_manquants(dossier(fonction=None, extra=FULL), eu) == ["Fonction"], "fonction absente")
    _assert(champs_manquants(dossier(situation="  ", extra=FULL), eu) == ["Situation familiale"], "espaces = vide")
    _assert("Téléphone" not in champs_manquants(dossier(extra=FULL), NS(phone="0101", extra={})), "téléphone du chat")
    _assert("Téléphone" in champs_manquants(dossier(extra=FULL), NS(phone=None, extra={})), "téléphone absent")
    _assert(champs_manquants(NS(donnees_pro=None, pieces=[]), None) == [l for _, l in CHAMPS_REQUIS], "sans donnees_pro")
    # repli OCR : date de naissance / n° de pièce lus sur la pièce comptent comme renseignés
    piece = NS(face="recto", piece_type="cni", ocr_data={"fields": {"date_naissance": "1978-12-13", "numero_piece": "X1"}})
    ex = {k: v for k, v in FULL.items() if k not in ("date_naissance", "numero_piece")}
    _assert(champs_manquants(dossier(extra=ex, pieces=[piece]), eu) == [], "valeurs OCR acceptées")
    _assert(set(champs_manquants(dossier(extra=ex), eu)) == {"Date de naissance", "N° de pièce"}, "sans OCR : manquants")


def test_wiring() -> None:
    from app.api import dossiers
    from app.schemas.dossier import DossierListItem
    src = inspect.getsource(dossiers.list_dossiers)
    _assert("champs_manquants=champs_manquants(d, u)" in src and "selectinload(Dossier.donnees_pro)" in src,
            "API : calcul + chargement de donnees_pro (pas de N+1)")
    _assert("champs_manquants" in DossierListItem.model_fields and "champs_total" in DossierListItem.model_fields, "schéma de réponse")
    _assert("champs_total=len(CHAMPS_REQUIS)" in src, "dénominateur de la barre fourni par le serveur")
    tab = (FRONT / "app/(app)/(workspace)/dossiers/_DossiersTable.tsx").read_text(encoding="utf-8")
    _assert('Champs manquants</th>' in tab and "<MissingFields" in tab, "colonne dans le tableau")
    _assert("total={d.champs_total}" in tab and "n <= 2 ?" in tab and "n <= 4 ?" in tab, "pastille colorée selon la gravité + /total")
    _assert("colSpan={canSelect ? 7 : 6}" in tab and tab.count("sa-skeleton--text") >= 6, "colspan et squelette alignés")
    _assert("champs_manquants" in (FRONT / "app/(app)/(workspace)/dossiers/_types.ts").read_text(encoding="utf-8"), "type")


def main() -> int:
    for t in (test_calcul, test_wiring):
        t()
        print(f"  ✓ {t.__name__}")
    print(f"OK — tous les asserts passent ({CHECKS})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
