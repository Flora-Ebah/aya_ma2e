"""Menu d'accueil du parcours d'inscription : « 2 / 3 » doivent BASCULER vers Consultation / Mise à jour
(avant : message sans suite -> conversation « done » -> le matricule relançait le menu).
Lancer : python -m tests.test_handoff_switch"""
from __future__ import annotations

import asyncio
import inspect
import uuid
from types import SimpleNamespace as NS

from app.conversation import workflow_executor as we

CHECKS = 0


def _assert(c, m):
    global CHECKS
    CHECKS += 1
    if not c:
        raise AssertionError(m)


class _Res:
    def __init__(self, rows): self.rows = rows
    def scalars(self): return NS(all=lambda: self.rows)


class _DB:
    def __init__(self, rows): self.rows = rows
    async def execute(self, *_a, **_k): return _Res(self.rows)


def wf(name, start, ident=None):
    return NS(id=ident or uuid.uuid4(), name=name, start_step_code=start)


def test_target_resolution() -> None:
    insc = wf("Inscription sociétaire MA2E", "welcome")
    conso = wf("Consultation de dossier", "consult_welcome")
    maj = wf("Mise à jour de dossier", "update_welcome")
    db = _DB([insc, conso, maj])
    run = lambda code, cur=insc, d=db: asyncio.run(we._handoff_target_start(d, cur, code))
    _assert(run("handoff_consultation") == "consult_welcome", "2 -> Consultation")
    _assert(run("handoff_modification") == "update_welcome", "3 -> Mise à jour")
    _assert(run("handoff_chat") is None, "pas de parcours chat actif -> message d'origine conservé")
    _assert(run("handoff_consultation", cur=conso) is None, "jamais de bascule vers le parcours courant")
    _assert(run("handoff_consultation", d=_DB([insc])) is None, "parcours cible absent/inactif -> None")
    _assert(run("handoff_modification", d=_DB([wf("Mise à jour", None)])) is None, "cible sans étape de départ -> None")


def test_wiring() -> None:
    src = inspect.getsource(we.execute)
    _assert('if next_code and next_code.startswith("handoff_"):' in src and "switch_to_step=switch" in src, "execute() bascule sur un handoff")
    _assert(src.index('next_code.startswith("handoff_")') > src.index("next_code = _resolve_next_code(current, branch)"),
            "contrôle appliqué APRÈS la résolution de la branche")
    from app.conversation import dispatcher
    d = inspect.getsource(dispatcher.dispatch)
    _assert('switched_ctx["_pinned_workflow_id"] = str(target_workflow.id)' in d, "le pin suit la bascule")


def main() -> int:
    for t in (test_target_resolution, test_wiring):
        t()
        print(f"  ✓ {t.__name__}")
    print(f"OK — tous les asserts passent ({CHECKS})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
