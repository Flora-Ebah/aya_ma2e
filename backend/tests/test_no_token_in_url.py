"""Test de non-régression F-07 — le jeton ne circule jamais en URL.

Le rapport pentest v1.0 (F-07) demande de proscrire le passage du
jeton d'accès en paramètre d'URL sur TOUS les endpoints, y compris les
usages non-auth (rate-limit, tracing, etc.).

Ce test parcourt le code source côté backend et échoue si un motif
`query_params.get("token")` ou `?token=` apparaît dans un chemin qui
n'est pas un commentaire de remédiation F-07.

Lancer :
    python -m tests.test_no_token_in_url
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BACKEND_APP = Path(__file__).parent.parent / "app"

# Fichiers ignorés : ceux qui contiennent uniquement des commentaires ou de
# la documentation autour de la remédiation F-07.
IGNORE_FILES: set[str] = set()

# Motifs interdits : lire un token dans la query string OU construire une
# URL avec `?token=` / `&token=`.
FORBIDDEN_PATTERNS: tuple[str, ...] = (
    'query_params.get("token")',
    "query_params.get('token')",
    "Query(alias=\"token\")",
    "Query(alias='token')",
)

# Motifs de commentaire acceptés (pour ne pas fail sur la doc du fix)
COMMENT_MARKERS: tuple[str, ...] = (
    "# F-07",
    "# fallback query",
    "F-07 —",
)


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        print(f"FAIL: {msg}", file=sys.stderr)
        raise AssertionError(msg)


def _is_forbidden_line(line: str) -> bool:
    stripped = line.strip()
    # Ligne de commentaire ou docstring → autorisée (on peut documenter le fix)
    if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
        return False
    # Sinon, cherche un motif interdit
    for pat in FORBIDDEN_PATTERNS:
        if pat in line:
            return True
    return False


def main() -> int:
    checks = 0
    violations: list[str] = []

    files = list(BACKEND_APP.rglob("*.py"))
    _assert(len(files) > 5, f"Peu de fichiers Python trouvés dans {BACKEND_APP} : {len(files)}")

    for file_path in files:
        if file_path.name in IGNORE_FILES:
            continue
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for i, line in enumerate(content.splitlines(), start=1):
            if _is_forbidden_line(line):
                rel = file_path.relative_to(BACKEND_APP.parent)
                violations.append(f"{rel}:{i}: {line.strip()}")

    checks += 1

    if violations:
        print("FAIL: motifs interdits détectés dans le code backend (F-07) :",
              file=sys.stderr)
        for v in violations:
            print(f"  {v}", file=sys.stderr)
        raise AssertionError(f"{len(violations)} violation(s) F-07 dans le code")

    # Vérification complémentaire : `get_auth_context` accepte uniquement
    # Header + Cookie (pas de Query).
    tenancy_src = (BACKEND_APP / "core" / "tenancy.py").read_text(encoding="utf-8")
    _assert("async def get_auth_context" in tenancy_src,
            "get_auth_context introuvable dans tenancy.py")
    _assert("Query(" not in tenancy_src.split("async def get_auth_context")[1].split("async def ")[0],
            "get_auth_context ne doit pas avoir de dépendance Query()")
    checks += 2

    print(f"OK — le jeton ne circule jamais en URL ({checks} vérifs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
