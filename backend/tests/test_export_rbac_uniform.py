"""Test de non-régression F-02 — contrôle d'export uniforme.

Le rapport pentest v1.0 (F-02) demande :
  1. Appliquer le contrôle d'export de manière UNIFORME à toutes les
     fonctions concernées, en s'appuyant sur `permission("export")`.
  2. Réviser TOUS les endpoints d'export.
  3. Minimiser les données à caractère personnel dans les exports.

Ce test statique parcourt tous les endpoints d'export connus et
échoue si l'un d'eux n'appelle pas `rbac_service.require_permission(...,
"export")` dans son corps de fonction.

Il valide aussi que `anonymize_ip` et `sanitize_user_agent` fonctionnent
correctement pour la reco 3.

Lancer :
    python -m tests.test_export_rbac_uniform
"""
from __future__ import annotations

import ast
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.export_pii import anonymize_ip, sanitize_user_agent  # noqa: E402


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        sys.stderr.write(f"FAIL: {msg}\n")
        raise AssertionError(msg)


# Endpoints connus qui exportent des données (nom fichier api, nom fonction)
# À enrichir si un nouvel endpoint export est créé — le test doit rester la
# barrière de conformité F-02.
EXPORT_ENDPOINTS: list[tuple[str, str]] = [
    ("dossiers.py", "export_dossiers_xlsx"),
    ("dossiers.py", "export_dossiers_csv"),
    ("audit.py", "export_audit_csv"),
    ("stats.py", "overview_pdf"),
    ("security.py", "export_dossier_rgpd"),
]

API_DIR = Path(__file__).parent.parent / "app" / "api"


def _has_export_check(fn: ast.AsyncFunctionDef) -> bool:
    """Cherche `require_permission(..., "export")` dans le corps de la fonction."""
    for node in ast.walk(fn):
        if isinstance(node, ast.Call):
            try:
                src = ast.unparse(node)
            except Exception:
                continue
            if "require_permission" in src and '"export"' in src:
                return True
            if "require_permission" in src and "'export'" in src:
                return True
    return False


def main() -> int:
    checks = 0
    violations: list[str] = []

    for filename, funcname in EXPORT_ENDPOINTS:
        path = API_DIR / filename
        _assert(path.exists(), f"{filename} introuvable")
        tree = ast.parse(path.read_text(encoding="utf-8"))
        # Trouve la fonction async par nom
        found = False
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == funcname:
                found = True
                if not _has_export_check(node):
                    violations.append(
                        f"{filename}:{funcname} n'a pas de require_permission(..., 'export')"
                    )
                break
        _assert(found, f"{filename}:{funcname} introuvable dans le module")
        checks += 1

    if violations:
        for v in violations:
            sys.stderr.write(f"FAIL: {v}\n")
        raise AssertionError(f"{len(violations)} endpoint(s) sans contrôle export uniforme")

    # ---- anonymize_ip ----
    _assert(anonymize_ip("192.168.1.42") == "192.168.1.0/24",
            "IPv4 doit être tronquée à /24")
    _assert(anonymize_ip("10.0.0.1") == "10.0.0.0/24",
            "IPv4 interne aussi")
    _assert(anonymize_ip("2001:db8::1") == "2001:db8::/64",
            "IPv6 doit être tronquée à /64")
    _assert(anonymize_ip("") == "",
            "IP vide → chaîne vide")
    _assert(anonymize_ip("invalid_ip") == "",
            "IP invalide → chaîne vide")
    _assert(anonymize_ip("1.2.3.4, 5.6.7.8") == "1.2.3.0/24",
            "X-Forwarded-For : garde seulement la première IP")
    checks += 6

    # ---- sanitize_user_agent ----
    _assert(sanitize_user_agent(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0.6478.183"
    ) == "Chrome/126 (Windows)", "Chrome/Windows détecté")
    _assert(sanitize_user_agent(
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/17.4 Safari/605.1.15"
    ) == "Safari/17 (macOS)", "Safari/macOS détecté")
    _assert(sanitize_user_agent("curl/8.20.0") == "curl/8",
            "curl détecté, pas d'OS")
    _assert(sanitize_user_agent("") == "", "UA vide → chaîne vide")
    _assert(sanitize_user_agent("something/nothing") == "unknown",
            "UA inconnu → 'unknown'")
    _assert(sanitize_user_agent(
        "Mozilla/5.0 (X11; Linux x86_64) Firefox/128.0"
    ) == "Firefox/128 (Linux)", "Firefox/Linux détecté")
    checks += 6

    sys.stdout.write(
        f"OK - controle d'export uniforme + PII minimisation ({checks} verifs)\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
