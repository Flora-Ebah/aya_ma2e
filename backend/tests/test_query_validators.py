"""Test de non-régression F-11 — helper de validation des query params.

Le rapport pentest v1.0 (F-11) a montré que ``?action=ZZZUNKNOWN`` sur
``/api/audit/logs`` renvoyait une 500. La reco : "valeur inconnue produit
un résultat vide". Le helper ``try_enum`` doit renvoyer ``None`` au lieu
de laisser remonter un ``ValueError``.

Lancer :
    python -m tests.test_query_validators
"""
from __future__ import annotations

import enum
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.query_validators import try_enum  # noqa: E402


class _Color(enum.Enum):
    red = "red"
    green = "green"


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        print(f"FAIL: {msg}", file=sys.stderr)
        raise AssertionError(msg)


def main() -> int:
    checks = 0

    # 1. Valeur reconnue → instance enum
    _assert(try_enum(_Color, "red") is _Color.red, "try_enum('red') doit retourner Color.red")
    checks += 1

    # 2. Valeur inconnue → None (pas de ValueError levé)
    _assert(try_enum(_Color, "ZZZUNKNOWN") is None,
            "try_enum('ZZZUNKNOWN') doit retourner None, pas lever")
    checks += 1

    # 3. None → None
    _assert(try_enum(_Color, None) is None, "try_enum(None) doit retourner None")
    checks += 1

    # 4. Chaîne vide → None (ne pas confondre avec valeur reconnue)
    _assert(try_enum(_Color, "") is None, "try_enum('') doit retourner None")
    checks += 1

    # 5. Une injection SQL-like n'est PAS reconnue
    _assert(try_enum(_Color, "1' OR '1'='1") is None,
            "try_enum d'une injection SQL doit renvoyer None")
    checks += 1

    # 6. Sur un vrai enum métier — AuditAction — l'action publique connue passe,
    #    une inconnue ne passe pas.
    from app.models import AuditAction
    known = next(iter(AuditAction)).value  # une action existante quelconque
    _assert(try_enum(AuditAction, known) is not None,
            f"try_enum d'une AuditAction connue ({known}) doit passer")
    _assert(try_enum(AuditAction, "ZZZUNKNOWN") is None,
            "try_enum(AuditAction, 'ZZZUNKNOWN') doit renvoyer None")
    checks += 2

    print(f"OK — tous les asserts passent ({checks})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
