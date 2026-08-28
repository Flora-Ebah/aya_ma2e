"""Test de non-régression F-06 — arbitrage saisie utilisateur ↔ OCR.

Le rapport pentest v1.0 (F-06) exige : "Traiter la donnée saisie et la
donnée extraite comme deux sources à confronter, et signaler tout écart
pour arbitrage humain, plutôt que d'accorder une priorité automatique
à l'une des deux."

Ce test valide `verify_user_data_vs_ocr` sans DB :
  - Match exact des 4 champs → branche "match"
  - 1-2 champs proches (Levenshtein) → branche "partial_match"
  - ≥3 champs mismatch → branche "mismatch" avec message clair
  - Le summary contient TOUJOURS les 2 valeurs côte à côte
  - Un « SPECIMEN vs Didier » ne peut PAS produire "match"

Lancer :
    python -m tests.test_data_vs_ocr_arbitrage
"""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.conversation.default_actions import verify_user_data_vs_ocr  # noqa: E402


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        print(f"FAIL: {msg}", file=sys.stderr)
        raise AssertionError(msg)


def _run(context: dict):
    """Exécute l'action en isolant les side-effects (pas de DB)."""
    return asyncio.run(
        verify_user_data_vs_ocr(db=None, context=context, last_input=None)
    )


def _ctx(user: dict, ocr: dict) -> dict:
    """Construit un context minimal comme celui reçu par l'action."""
    return {
        "ask_nom": user.get("nom"),
        "ask_prenoms": user.get("prenoms"),
        "ask_numero_piece": user.get("numero_piece"),
        "ask_date_naissance": user.get("date_naissance"),
        "ocr_recto": {
            "fields": {
                "nom": ocr.get("nom"),
                "prenoms": ocr.get("prenoms"),
                "numero_piece": ocr.get("numero_piece"),
                "date_naissance": ocr.get("date_naissance"),
            }
        },
    }


def main() -> int:
    checks = 0

    # ---- 1. Match parfait sur les 4 champs → branche "match" ----
    ctx = _ctx(
        user={"nom": "OUATTARA", "prenoms": "AHMED", "numero_piece": "C00123456",
              "date_naissance": "1985-04-12"},
        ocr={"nom": "OUATTARA", "prenoms": "AHMED", "numero_piece": "C00123456",
             "date_naissance": "1985-04-12"},
    )
    result = _run(ctx)
    _assert(result.branch_key == "match",
            f"4 champs identiques doivent brancher 'match', got '{result.branch_key}'")
    _assert(result.extra_context["data_match_mismatches"] == 0,
            "match parfait → 0 mismatch")
    checks += 2

    # ---- 2. PoC pentester : Didier / dechan (saisi) vs SPECIMEN / SPECIMEN (OCR) ----
    # C'est le cas EXACT du screenshot F-06. Doit brancher 'mismatch' avec
    # arbitrage humain forcé, pas laisser passer.
    ctx = _ctx(
        user={"nom": "Didier", "prenoms": "dechan", "numero_piece": "P987654",
              "date_naissance": "1990-05-20"},
        ocr={"nom": "SPECIMEN", "prenoms": "SPECIMEN", "numero_piece": "IC000000411",
             "date_naissance": "2000-01-01"},
    )
    result = _run(ctx)
    _assert(result.branch_key == "mismatch",
            f"PoC pentester (SPECIMEN vs Didier) doit brancher 'mismatch', "
            f"got '{result.branch_key}'")
    _assert(result.extra_context["data_match_mismatches"] >= 3,
            f"PoC pentester doit avoir ≥3 mismatch, got "
            f"{result.extra_context['data_match_mismatches']}")
    _assert(result.message and "manuellement" in result.message.lower(),
            "Message mismatch doit annoncer un examen manuel")
    checks += 3

    # ---- 3. Summary contient TOUJOURS les 2 valeurs côte à côte ----
    summary = result.extra_context["data_match_summary"]
    _assert("Didier" in summary, "summary doit inclure la saisie 'Didier'")
    _assert("SPECIMEN" in summary, "summary doit inclure l'OCR 'SPECIMEN'")
    _assert("dechan" in summary, "summary doit inclure la saisie 'dechan'")
    checks += 3

    # ---- 4. 1 champ proche (Levenshtein) → branche "partial_match" ----
    # ex : OUATTARA vs OUATARA (1 lettre en moins, très courant OCR)
    ctx = _ctx(
        user={"nom": "OUATTARA", "prenoms": "AHMED", "numero_piece": "C00123456",
              "date_naissance": "1985-04-12"},
        ocr={"nom": "OUATARA", "prenoms": "AHMED", "numero_piece": "C00123456",
             "date_naissance": "1985-04-12"},
    )
    result = _run(ctx)
    _assert(result.branch_key == "partial_match",
            f"1 champ 'close' doit brancher 'partial_match', got '{result.branch_key}'")
    checks += 1

    # ---- 5. numero_piece strict : pas de tolérance Levenshtein ----
    # Un numéro de pièce différent d'un caractère est un mismatch (strict).
    ctx = _ctx(
        user={"nom": "OUATTARA", "prenoms": "AHMED", "numero_piece": "C00123456",
              "date_naissance": "1985-04-12"},
        ocr={"nom": "OUATTARA", "prenoms": "AHMED", "numero_piece": "C00123457",  # 1 chiffre diff
             "date_naissance": "1985-04-12"},
    )
    result = _run(ctx)
    # 1 champ mismatch strict + 3 match → branche partial_match
    _assert(result.branch_key == "partial_match",
            f"1 mismatch strict (numero) → 'partial_match', got '{result.branch_key}'")
    _assert(result.extra_context["data_match_results"]["numero"] == "mismatch",
            "numero strict doit être 'mismatch' pas 'close'")
    checks += 2

    sys.stdout.write(
        f"OK - arbitrage saisie vs OCR fonctionne comme attendu ({checks} verifs)\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
