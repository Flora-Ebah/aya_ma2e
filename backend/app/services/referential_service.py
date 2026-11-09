"""Service de vérification du matricule employeur dans le référentiel ERANOVE.

Adapter pattern : la source est paramétrable par tenant via
`settings.integrations.referential_source` ∈ {none, csv, http}.

Résultat normalisé :
    {
        "found": bool,
        "matricule": str,
        "employeur": str,
        "name": str | None,
        "fonction": str | None,
        "status": "active" | "inactive" | "unknown",
        "source": "csv" | "http" | "none",
    }

En mode strict (`referential_strict_mode=True`), un matricule non trouvé
doit marquer le dossier comme nécessitant une revue manuelle (logique
gérée par l'appelant, pas par ce service).
"""
from __future__ import annotations

import csv
import io
import logging
from pathlib import Path
from typing import Optional
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import settings_service

logger = logging.getLogger(__name__)

HTTP_TIMEOUT = httpx.Timeout(10.0, connect=5.0)

# CSV embed : POC. En prod, le chemin est configurable.
DEFAULT_CSV_PATH = Path(__file__).parent.parent.parent / "seeds" / "referentiel_agents.csv"


# ====================================================================== #
# Public API
# ====================================================================== #
async def verify_matricule(
    db: AsyncSession,
    tenant_id: UUID,
    employeur_code: str,
    matricule: str,
) -> dict:
    """Vérifie un matricule dans le référentiel configuré pour ce tenant.

    Ne lève jamais d'exception : retourne `found=False` avec `source` indiquant
    pourquoi (none = pas configuré, http_error = appel KO, etc.).
    """
    src = await settings_service.get_value(db, tenant_id, "integrations", "referential_source")

    if src == "none" or not src:
        return _result(False, employeur_code, matricule, source="none")

    if src == "csv":
        return await _verify_csv(employeur_code, matricule)

    if src == "http":
        return await _verify_http(db, tenant_id, employeur_code, matricule)

    return _result(False, employeur_code, matricule, source="unknown_source")


# ====================================================================== #
# Adapters
# ====================================================================== #
async def _verify_csv(employeur_code: str, matricule: str) -> dict:
    """Lit un CSV simple matricule;employeur;nom;fonction;status."""
    path = DEFAULT_CSV_PATH
    if not path.exists():
        logger.warning("referentiel_agents.csv introuvable à %s", path)
        return _result(False, employeur_code, matricule, source="csv_missing")

    try:
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=";")
            for row in reader:
                if (
                    row.get("matricule", "").strip().lower() == matricule.strip().lower()
                    and row.get("employeur", "").strip().upper() == employeur_code.strip().upper()
                ):
                    return _result(
                        True, employeur_code, matricule,
                        name=row.get("nom") or None,
                        fonction=row.get("fonction") or None,
                        status=row.get("status") or "unknown",
                        source="csv",
                    )
    except Exception as e:  # noqa: BLE001
        logger.warning("Erreur lecture CSV référentiel : %s", e)
        return _result(False, employeur_code, matricule, source="csv_error")

    return _result(False, employeur_code, matricule, source="csv")


async def _verify_http(
    db: AsyncSession,
    tenant_id: UUID,
    employeur_code: str,
    matricule: str,
) -> dict:
    """Interroge une API HTTP distante via GET avec Bearer token."""
    url = await settings_service.get_value(db, tenant_id, "integrations", "referential_http_url")
    token = await settings_service.get_value(db, tenant_id, "integrations", "referential_http_token")

    if not url:
        return _result(False, employeur_code, matricule, source="http_not_configured")

    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            resp = await client.get(
                url,
                params={"employeur": employeur_code, "matricule": matricule},
                headers=headers,
            )
            if resp.status_code == 404:
                return _result(False, employeur_code, matricule, source="http")
            if resp.status_code >= 400:
                logger.warning("Référentiel HTTP %s : %s", resp.status_code, resp.text[:200])
                return _result(False, employeur_code, matricule, source="http_error")
            data = resp.json()
    except (httpx.HTTPError, ValueError) as e:
        logger.warning("Erreur appel référentiel HTTP : %s", e)
        return _result(False, employeur_code, matricule, source="http_error")

    if not data or not data.get("exists", False):
        return _result(False, employeur_code, matricule, source="http")

    return _result(
        True, employeur_code, matricule,
        name=data.get("name"),
        fonction=data.get("fonction"),
        status=data.get("status", "active"),
        source="http",
    )


# ====================================================================== #
# Helpers
# ====================================================================== #
def _result(
    found: bool,
    employeur_code: str,
    matricule: str,
    *,
    name: Optional[str] = None,
    fonction: Optional[str] = None,
    status: str = "unknown",
    source: str = "none",
) -> dict:
    return {
        "found": found,
        "matricule": matricule,
        "employeur": employeur_code,
        "name": name,
        "fonction": fonction,
        "status": status,
        "source": source,
    }
