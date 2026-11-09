"""Service d'envoi de webhooks sortants (signés HMAC) avec retry et tracking.

Garanties :
- **Signature HMAC-SHA256** dans le header `X-MA2E-Signature`
- **Header `X-MA2E-Event`** : type d'événement (dossier_validated, dossier_rejected…)
- **Trace BD** dans `webhook_deliveries` (succès et échecs)
- **Retry** exponentiel sur 5xx et timeouts (1s, 2s, 4s, …) — exécuté en best-effort
- Pas de retry sur 4xx (le receiver a explicitement rejeté)
- Best-effort : un échec n'interrompt JAMAIS le flux métier appelant

Usage typique (depuis dossier_service après validation) :
    await webhook_service.send_event(
        db,
        tenant_id=tenant.id,
        event_type="dossier_validated",
        resource_type="dossier",
        resource_id=str(dossier.id),
        payload={"dossier_number": dossier.dossier_number, ...},
    )
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import WebhookDelivery, WebhookStatus
from app.services import settings_service

logger = logging.getLogger(__name__)

HTTP_TIMEOUT = httpx.Timeout(10.0, connect=5.0)
MAX_BODY_PREVIEW = 4096  # caractères stockés en BD


# ====================================================================== #
# Public API
# ====================================================================== #
async def send_event(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    event_type: str,
    resource_type: str,
    resource_id: str,
    payload: dict,
) -> Optional[WebhookDelivery]:
    """Envoie un événement à la cible configurée (compta) si l'événement
    est inclus dans `compta_webhook_events`. Retourne le `WebhookDelivery`
    créé ou None si pas envoyé.

    NE LÈVE PAS d'exception — un échec d'intégration ne doit pas bloquer
    la transaction métier (validation/refus de dossier).
    """
    try:
        target_url = await settings_service.get_value(
            db, tenant_id, "integrations", "compta_webhook_url"
        )
        events = await settings_service.get_value(
            db, tenant_id, "integrations", "compta_webhook_events"
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("send_event: lecture settings impossible (%s)", e)
        return None

    if not target_url or not _event_matches(event_type, events):
        return None

    delivery = WebhookDelivery(
        tenant_id=tenant_id,
        event_type=event_type,
        resource_type=resource_type,
        resource_id=resource_id,
        target_url=target_url,
        payload=payload,
        status=WebhookStatus.pending,
    )
    db.add(delivery)
    await db.flush()

    # Premier envoi sync (sans bloquer le caller en cas d'échec)
    try:
        await _attempt_delivery(db, delivery)
    except Exception as e:  # noqa: BLE001
        logger.warning("send_event: première tentative KO (%s)", e)
    return delivery


async def retry_delivery(
    db: AsyncSession,
    delivery: WebhookDelivery,
) -> WebhookDelivery:
    """Re-tente une delivery en échec. Utilisé via l'API admin de retry."""
    if delivery.status == WebhookStatus.success:
        raise ValueError("Cette delivery est déjà en succès.")
    delivery.status = WebhookStatus.retrying
    await db.flush()
    await _attempt_delivery(db, delivery)
    return delivery


# ====================================================================== #
# Internals
# ====================================================================== #
def _event_matches(event_type: str, configured: str) -> bool:
    """Décide si un event_type doit déclencher un envoi selon la config.

    configured ∈ {none, validated, decided, all}
    """
    if configured == "none" or not configured:
        return False
    if configured == "all":
        return True
    if configured == "validated":
        return event_type == "dossier_validated"
    if configured == "decided":
        return event_type in ("dossier_validated", "dossier_rejected")
    return False


def _sign(secret: str, body: bytes) -> str:
    """HMAC-SHA256 du body, retourné en hex."""
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


async def _attempt_delivery(db: AsyncSession, delivery: WebhookDelivery) -> None:
    """Tente l'envoi UNE fois. Met à jour la delivery en BD selon le résultat."""
    secret = await settings_service.get_value(
        db, delivery.tenant_id, "integrations", "compta_webhook_secret"
    )
    max_retries = await settings_service.get_value(
        db, delivery.tenant_id, "integrations", "webhook_max_retries"
    )

    body = json.dumps(delivery.payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "X-MA2E-Event": delivery.event_type,
        "X-MA2E-Delivery-Id": str(delivery.id),
        "User-Agent": "MA2E-Webhook/1.0",
    }
    if secret:
        headers["X-MA2E-Signature"] = "sha256=" + _sign(secret, body)

    delivery.attempts += 1
    delivery.last_attempt_at = datetime.now(timezone.utc)

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            resp = await client.post(delivery.target_url, content=body, headers=headers)

        delivery.response_status = resp.status_code
        delivery.response_body = (resp.text or "")[:MAX_BODY_PREVIEW]

        if 200 <= resp.status_code < 300:
            delivery.status = WebhookStatus.success
            delivery.error_message = None
            delivery.next_attempt_at = None
            return

        # 4xx = refus explicite, on ne retry pas
        if 400 <= resp.status_code < 500:
            delivery.status = WebhookStatus.failed
            delivery.error_message = f"HTTP {resp.status_code} : refus client"
            delivery.next_attempt_at = None
            return

        # 5xx = potentiellement transitoire
        delivery.error_message = f"HTTP {resp.status_code}"

    except httpx.TimeoutException:
        delivery.error_message = "timeout"
    except Exception as e:  # noqa: BLE001
        delivery.error_message = f"exception : {type(e).__name__} {str(e)[:200]}"

    # Échec récupérable
    if delivery.attempts < max_retries:
        delivery.status = WebhookStatus.retrying
        # Backoff exponentiel : 2^attempts secondes (1, 2, 4, 8…)
        delay = min(60, 2 ** delivery.attempts)
        # On note la prochaine échéance ; le scheduled job de retry est en
        # tâche follow-up. Pour le POC, on fait un best-effort sync.
        delivery.next_attempt_at = datetime.now(timezone.utc).replace(microsecond=0)
        try:
            await asyncio.sleep(delay)
            await _attempt_delivery(db, delivery)
        except Exception as e:  # noqa: BLE001
            logger.warning("Retry webhook %s KO : %s", delivery.id, e)
    else:
        delivery.status = WebhookStatus.failed
        delivery.next_attempt_at = None
