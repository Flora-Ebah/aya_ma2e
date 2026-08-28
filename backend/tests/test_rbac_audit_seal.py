"""Test de non-régression F-12 — verrou d'immuabilité de la piste d'audit.

Le rapport pentest v1.0 (rec. F-12) exige que la piste d'audit soit
strictement immuable, sans exception de rôle. `_seal_audit_immutability`
doit forcer `audit.write = False` et `audit.delete = False` quelle que
soit la matrice RBAC en entrée, pour TOUS les rôles applicatifs.

Ce test tourne sans DB ni fixture — pure logique. Lancer :

    cd backend
    python -m tests.test_rbac_audit_seal

Sortie attendue : "OK — tous les asserts passent (7)".
"""
from __future__ import annotations

import os
import sys

# Rends l'import possible même sans pytest / installation en package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# F-12 — s'assurer que la config par défaut n'active pas le break-glass
os.environ.setdefault("AUDIT_BREAK_GLASS_ENABLED", "false")
os.environ.setdefault("APP_ENV", "production")

from app.models.user import UserRole  # noqa: E402
from app.services.rbac_service import _seal_audit_immutability  # noqa: E402


def _full_matrix() -> dict:
    """Matrice où tout est autorisé (le pire cas côté sécurité)."""
    return {
        "audit": {"read": True, "write": True, "delete": True, "export": True},
        "validation": {"read": True, "write": True, "delete": True, "export": True},
    }


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        print(f"FAIL: {msg}", file=sys.stderr)
        raise AssertionError(msg)


def main() -> int:
    checks = 0

    # 1. Un agent ne peut jamais écrire ni supprimer sur audit, même si
    #    la matrice le prétend.
    p = _seal_audit_immutability(_full_matrix(), UserRole.agent)
    _assert(p["audit"]["write"] is False, "agent.audit.write doit être False")
    _assert(p["audit"]["delete"] is False, "agent.audit.delete doit être False")
    _assert(p["audit"]["read"] is True, "agent.audit.read n'est pas touché")
    checks += 3

    # 2. Un viewer non plus (même si le viewer n'a normalement pas write,
    #    la matrice d'entrée hostile force True).
    p = _seal_audit_immutability(_full_matrix(), UserRole.viewer)
    _assert(p["audit"]["write"] is False, "viewer.audit.write doit être False")
    _assert(p["audit"]["delete"] is False, "viewer.audit.delete doit être False")
    checks += 2

    # 3. Un tenant_admin non plus. Le pentest exige "y compris administration".
    p = _seal_audit_immutability(_full_matrix(), UserRole.tenant_admin)
    _assert(p["audit"]["write"] is False, "tenant_admin.audit.write doit être False")
    _assert(p["audit"]["delete"] is False, "tenant_admin.audit.delete doit être False")
    checks += 2

    # 4. Le super_admin non plus — la reco pentest dit "sans exception de rôle".
    #    En prod avec AUDIT_BREAK_GLASS_ENABLED=false, super_admin est verrouillé.
    p = _seal_audit_immutability(_full_matrix(), UserRole.super_admin)
    _assert(p["audit"]["write"] is False,
            "super_admin.audit.write doit être False en prod (F-12 sans exception)")
    _assert(p["audit"]["delete"] is False,
            "super_admin.audit.delete doit être False en prod (F-12 sans exception)")
    checks += 2

    # 5. Les autres modules ne sont pas affectés par le seal.
    p = _seal_audit_immutability(_full_matrix(), UserRole.agent)
    _assert(p["validation"]["write"] is True, "seal ne touche pas validation.write")
    _assert(p["validation"]["delete"] is True, "seal ne touche pas validation.delete")
    checks += 2

    print(f"OK — tous les asserts passent ({checks})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
