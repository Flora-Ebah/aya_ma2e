"""Service d'anonymisation effective (US-28, droit à l'oubli ARTCI art.21).

Quand le DPO déclenche l'anonymisation d'un dossier :

1. **Remplace** les données nominatives par des valeurs anonymes :
   - end_user.name, phone, telegram_id, extra → null / "anonymized"
   - dossier.matricule → null
   - pieces.ocr_data, mrz_data, user_corrections → {} (conservant ocr_status/score)
   - donnees_pro.fonction, rib → null
   - conversation messages → texte remplacé par "[anonymisé]"
2. **Conserve** :
   - L'identifiant technique (id) pour préserver l'intégrité référentielle
   - Le journal d'audit (statistiques + chaîne SHA-256)
   - Le numéro de sociétaire (utile pour la compta, mais détaché de l'identité)
3. **Marque** le dossier comme anonymisé via `status=rejete` + motif clair
4. **Produit** un accusé d'exécution daté, audité via `droits_anonymisation`

L'opération est **irréversible** (les données effacées le sont définitivement).
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AuditAction,
    Conversation,
    DonneesPro,
    Dossier,
    DossierStatus,
    EndUser,
    Message,
    PieceIdentite,
)
from app.services import audit_service

logger = logging.getLogger(__name__)

ANON_PLACEHOLDER = "[anonymisé]"


async def anonymize_dossier(
    db: AsyncSession,
    *,
    dossier_id: UUID,
    tenant_id: UUID,
    actor_id: UUID,
    reason: Optional[str] = None,
) -> dict:
    """Effectue l'anonymisation effective d'un dossier.

    Retourne un accusé d'exécution avec un hash empreinte (preuve d'avoir
    procédé sans contenir aucune donnée identifiante).
    """
    dossier = (
        await db.execute(
            select(Dossier).where(
                Dossier.id == dossier_id,
                Dossier.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if dossier is None:
        raise ValueError("Dossier introuvable ou hors tenant.")

    # 0) Empreinte avant (sans révéler les données) : hash de l'ID + matricule + statut
    fingerprint = hashlib.sha256(
        f"{dossier.id}|{dossier.matricule}|{dossier.status.value}".encode()
    ).hexdigest()[:16]

    # 1) End user
    end_user = (
        await db.execute(select(EndUser).where(EndUser.id == dossier.end_user_id))
    ).scalar_one_or_none()
    if end_user is not None:
        end_user.name = ANON_PLACEHOLDER
        end_user.phone = None
        end_user.telegram_id = None
        end_user.extra = {"anonymized": True, "at": datetime.now(timezone.utc).isoformat()}

    # 2) Dossier — efface matricule, motive, demande
    dossier.matricule = None
    dossier.rejection_motive = (
        f"Anonymisation suite à exercice du droit à l'oubli (ARTCI art.21). "
        f"Motif DPO : {reason or 'non précisé'}"
    )
    dossier.additional_request = None
    if dossier.status not in (DossierStatus.rejete,):
        dossier.status = DossierStatus.rejete
    dossier.priority_review = False
    dossier.priority_reason = None
    dossier.locked_by = None
    dossier.locked_at = None

    # 3) Pièces — vide ocr_data, mrz_data, user_corrections, et marque
    pieces = list(
        (
            await db.execute(
                select(PieceIdentite).where(PieceIdentite.dossier_id == dossier.id)
            )
        ).scalars().all()
    )
    for p in pieces:
        p.ocr_data = {}
        p.mrz_data = {}
        p.user_corrections = {}
        # storage_key conservé pour permettre la suppression du blob côté infra
        # (la suppression du fichier Azure Blob est faite par un job séparé)

    # 4) Données pro
    dp = (
        await db.execute(
            select(DonneesPro).where(DonneesPro.dossier_id == dossier.id)
        )
    ).scalar_one_or_none()
    if dp is not None:
        dp.fonction = None
        dp.rib = None
        dp.extra = {"anonymized": True}

    # 5) Messages des conversations de cet end_user → contenu remplacé
    if end_user is not None:
        convs = list(
            (
                await db.execute(
                    select(Conversation).where(
                        Conversation.tenant_id == tenant_id,
                        Conversation.end_user_id == end_user.id,
                    )
                )
            ).scalars().all()
        )
        if convs:
            conv_ids = [c.id for c in convs]
            msgs = list(
                (
                    await db.execute(
                        select(Message).where(Message.conversation_id.in_(conv_ids))
                    )
                ).scalars().all()
            )
            for m in msgs:
                m.content = ANON_PLACEHOLDER
                m.media_url = None
                m.extra = {"anonymized": True}

    await db.flush()

    # 6) Audit (NE PAS inclure de données nominatives dans details)
    receipt_time = datetime.now(timezone.utc)
    await audit_service.log(
        db,
        tenant_id=tenant_id,
        action=AuditAction.droits_anonymisation,
        resource_type="dossier",
        resource_id=str(dossier.id),
        actor_type="user",
        actor_id=str(actor_id),
        details={
            "fingerprint_before": fingerprint,
            "executed_at": receipt_time.isoformat(),
            "pieces_anonymized": len(pieces),
            "messages_anonymized_for_end_user": str(end_user.id) if end_user else None,
            "reason_short": (reason or "")[:200],
            "irreversible": True,
        },
    )

    return {
        "dossier_id": str(dossier.id),
        "executed_at": receipt_time.isoformat(),
        "fingerprint_before": fingerprint,
        "pieces_anonymized": len(pieces),
        "irreversible": True,
        "message": (
            "Anonymisation exécutée avec succès. Les données nominatives ont "
            "été remplacées. Le journal d'audit et les statistiques agrégées "
            "sont conservés conformément à la loi 2013-450."
        ),
    }
