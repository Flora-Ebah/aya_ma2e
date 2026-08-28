"""Test de non-régression F-05 — /docs, /redoc, /openapi.json fermés en prod.

Le rapport pentest v1.0 (F-05) exige que la documentation interactive
soit désactivée en production. La reco offre plusieurs options ; MA2E
a retenu la première : `docs_url=None`, `redoc_url=None`,
`openapi_url=None` quand `APP_ENV` correspond à un alias de production.

Ce test vérifie qu'une FastAPI construite avec `APP_ENV=production`
n'expose PAS ces 3 endpoints. Il inspecte les attributs sur l'app
créée par `app/main.py`.

Lancer :
    APP_ENV=production python -m tests.test_docs_disabled_in_prod
    APP_ENV=development python -m tests.test_docs_disabled_in_prod
"""
from __future__ import annotations

import os
import sys
import importlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        sys.stderr.write(f"FAIL: {msg}\n")
        raise AssertionError(msg)


def _reload_app_with_env(app_env_value: str):
    """Reload complet du module main avec APP_ENV positionné."""
    os.environ["APP_ENV"] = app_env_value
    # Purge des modules déjà importés pour forcer une relecture propre du setting
    for mod_name in list(sys.modules.keys()):
        if mod_name.startswith("app.") or mod_name == "app":
            del sys.modules[mod_name]
    main = importlib.import_module("app.main")
    return main.app, main._IS_PROD


def _check_prod_alias(alias: str) -> None:
    """Vérifie que `alias` (ex. 'production', 'PROD', 'Prod') active le kill-switch."""
    app, is_prod = _reload_app_with_env(alias)
    _assert(is_prod is True,
            f"APP_ENV={alias!r} doit être reconnu comme production (_IS_PROD)")
    _assert(app.docs_url is None,
            f"APP_ENV={alias!r} : /docs doit être fermé (docs_url=None)")
    _assert(app.redoc_url is None,
            f"APP_ENV={alias!r} : /redoc doit être fermé (redoc_url=None)")
    _assert(app.openapi_url is None,
            f"APP_ENV={alias!r} : /openapi.json doit être fermé (openapi_url=None)")


def _check_non_prod(env_value: str) -> None:
    """Vérifie qu'un env dev/staging garde la doc active."""
    app, is_prod = _reload_app_with_env(env_value)
    _assert(is_prod is False,
            f"APP_ENV={env_value!r} ne doit PAS déclencher _IS_PROD")
    _assert(app.docs_url is not None,
            f"APP_ENV={env_value!r} : /docs doit rester actif en non-prod")


def main() -> int:
    checks = 0

    # ---- 1. Toutes les variantes 'prod' déclenchent le kill-switch ----
    for alias in ("production", "PRODUCTION", "Production", "prod", "PROD", "Prod", "prd"):
        _check_prod_alias(alias)
        checks += 4  # is_prod + 3 endpoints

    # ---- 2. Les env non-prod gardent la doc ----
    for env_value in ("development", "staging", "test", "dev"):
        _check_non_prod(env_value)
        checks += 2  # is_prod + docs_url

    # ---- 3. Une valeur vide ou étrange n'active PAS la prod (fail-safe :
    #        si un ops oublie la variable, on ne cache pas Swagger ; ça se
    #        remarquera en dev/staging. Mais on ne réactive pas non plus
    #        Swagger silencieusement en prod si APP_ENV=production est bien
    #        posé.). Le vrai fail-safe est côté ops.
    for env_value in ("", "   "):
        _check_non_prod(env_value)
        checks += 2

    sys.stdout.write(
        f"OK - kill-switch F-05 fonctionne sur toutes les variantes ({checks} verifs)\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
