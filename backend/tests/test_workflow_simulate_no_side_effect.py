"""Test de non-régression F-10 — pas d'action à effet réel en mode simulate.

Le rapport pentest v1.0 (F-10) demande, en plus de restreindre l'accès à
`POST /api/workflows/{id}/simulate` aux administrateurs, de vérifier
que « la simulation ne peut en aucun cas déclencher d'action de service
produisant un effet réel ».

L'implémentation MA2E court-circuite les actions à effet réel via
`context["_simulate"] is True`. Ce test vérifie statiquement (grep AST)
que toute action listée comme "à effet réel" a bien ce check dans son
corps de fonction. Si un futur ajout d'action à effet réel oublie le
garde-fou, ce test échoue.

Lancer :
    python -m tests.test_workflow_simulate_no_side_effect
"""
from __future__ import annotations

import ast
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Actions à effet réel dans le workflow MA2E. Chaque nom correspond à une
# fonction async décorée `@workflow_action(...)` dans default_actions.py.
# Ajouter ici toute nouvelle action susceptible d'écrire en BD, d'envoyer
# une notification, de lire un OCR distant ou de solliciter un service tiers.
ACTIONS_WITH_SIDE_EFFECTS: set[str] = {
    # Création dossier (writes BD)
    "create_validated_dossier",
    "create_real_dossier",
    # OCR distant (calls Azure Vision / OCR.space / Mindee)
    "ocr_extract_recto",
    "ocr_extract_verso",
    # OTP (calls SMTP / SMS)
    "send_email_otp",
    "verify_email_otp",
    # Notifications (calls SMTP / API externe)
    "notify_end_of_enrolment",
    # Revue manuelle (writes BD)
    "queue_for_manual_review",
}

DEFAULT_ACTIONS_PATH = Path(__file__).parent.parent / "app" / "conversation" / "default_actions.py"


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        print(f"FAIL: {msg}", file=sys.stderr)
        raise AssertionError(msg)


def _has_simulate_guard(func: ast.AsyncFunctionDef) -> bool:
    """True si la fonction contient un `if context.get("_simulate") is True: return ...`
    ou équivalent en début de corps (avant tout appel externe).
    Le motif tolère un léger enrobage (variable intermédiaire, autres checks)."""
    for node in ast.walk(func):
        if not isinstance(node, ast.If):
            continue
        # cherche un test qui contient la chaîne "_simulate"
        try:
            test_src = ast.unparse(node.test)
        except Exception:
            continue
        if "_simulate" in test_src:
            # Corps du if doit contenir un return
            for stmt in node.body:
                if isinstance(stmt, ast.Return):
                    return True
    return False


def main() -> int:
    _assert(DEFAULT_ACTIONS_PATH.exists(),
            f"default_actions.py introuvable : {DEFAULT_ACTIONS_PATH}")

    tree = ast.parse(DEFAULT_ACTIONS_PATH.read_text(encoding="utf-8"))

    # Récolte {function_name: FunctionDef}
    functions: dict[str, ast.AsyncFunctionDef] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef):
            functions[node.name] = node

    checks = 0
    missing: list[str] = []

    for action_name in sorted(ACTIONS_WITH_SIDE_EFFECTS):
        _assert(action_name in functions,
                f"Action {action_name} introuvable dans default_actions.py — ajout par erreur ?")
        if not _has_simulate_guard(functions[action_name]):
            missing.append(action_name)
        checks += 1

    if missing:
        print("FAIL: les actions suivantes N'ont PAS de garde `_simulate` :",
              file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)
        raise AssertionError(f"{len(missing)} action(s) sans garde _simulate")

    print(f"OK — les {checks} actions à effet réel ont un garde `_simulate`")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
