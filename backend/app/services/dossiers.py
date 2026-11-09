"""Service métier des dossiers d'identification MA2E."""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import Integer, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AuditAction,
    Conversation,
    DonneesPro,
    Dossier,
    DossierStatus,
    EndUser,
    PieceFace,
    PieceIdentite,
    PieceType,
    Tenant,
)
from app.services import audit_service


async def next_dossier_number(db: AsyncSession, tenant: Tenant) -> str:
    """Génère le prochain numéro MA2E-YYYY-NNNNNN.

    Utilise MAX(suffixe) + 1 et pas COUNT(*) + 1 : si un dossier est supprimé
    ou si une transaction précédente a avancé le compteur sans commit, COUNT
    fait collision sur le MA2E-YYYY-NNN déjà pris. MAX reste monotone.
    """
    year = datetime.now(timezone.utc).year
    prefix = f"MA2E-{year}-"
    # Extrait la partie numérique après le préfixe et prend le max.
    suffix_expr = func.substring(Dossier.dossier_number, len(prefix) + 1)
    stmt = select(func.max(func.cast(suffix_expr, Integer))).where(
        Dossier.tenant_id == tenant.id,
        Dossier.dossier_number.like(f"{prefix}%"),
    )
    max_suffix = (await db.execute(stmt)).scalar() or 0
    return f"{prefix}{(max_suffix + 1):06d}"


async def get_or_create_dossier(
    db: AsyncSession,
    tenant: Tenant,
    end_user: EndUser,
    conversation: Conversation,
) -> Dossier:
    stmt = (
        select(Dossier)
        .where(
            Dossier.tenant_id == tenant.id,
            Dossier.end_user_id == end_user.id,
            Dossier.status.in_([DossierStatus.en_cours, DossierStatus.complement_requis]),
        )
        .order_by(Dossier.created_at.desc())
        .limit(1)
    )
    dossier = (await db.execute(stmt)).scalar_one_or_none()
    if dossier:
        return dossier

    number = await next_dossier_number(db, tenant)
    dossier = Dossier(
        tenant_id=tenant.id,
        dossier_number=number,
        end_user_id=end_user.id,
        conversation_id=conversation.id,
        status=DossierStatus.en_cours,
    )
    db.add(dossier)
    await db.flush()

    await audit_service.log(
        db=db,
        tenant_id=tenant.id,
        action=AuditAction.dossier_created,
        resource_type="dossier",
        resource_id=str(dossier.id),
        actor_type="end_user",
        actor_id=str(end_user.id),
        details={"dossier_number": number, "channel": conversation.channel.value},
    )
    return dossier


async def attach_piece(
    db: AsyncSession,
    tenant_id: UUID,
    dossier: Dossier,
    piece_type: PieceType,
    face: PieceFace,
    storage_key: str,
    mime_type: str = "image/jpeg",
) -> PieceIdentite:
    piece = PieceIdentite(
        tenant_id=tenant_id,
        dossier_id=dossier.id,
        piece_type=piece_type,
        face=face,
        storage_key=storage_key,
        mime_type=mime_type,
        ocr_status="pending",
    )
    db.add(piece)
    await db.flush()

    await audit_service.log(
        db=db,
        tenant_id=tenant_id,
        action=AuditAction.piece_uploaded,
        resource_type="piece_identite",
        resource_id=str(piece.id),
        details={"dossier_id": str(dossier.id), "face": face.value, "type": piece_type.value},
    )
    return piece


async def store_ocr_result(
    db: AsyncSession,
    piece: PieceIdentite,
    ocr_result: dict,
) -> None:
    piece.ocr_status = "completed"
    piece.ocr_data = ocr_result.get("fields", {})
    piece.mrz_data = ocr_result.get("mrz", {})
    piece.ocr_confidence = ocr_result.get("confidence")
    await db.flush()

    await audit_service.log(
        db=db,
        tenant_id=piece.tenant_id,
        action=AuditAction.piece_ocr_completed,
        resource_type="piece_identite",
        resource_id=str(piece.id),
        details={
            "provider": ocr_result.get("provider"),
            "confidence": ocr_result.get("confidence"),
            "warnings": ocr_result.get("warnings", []),
        },
    )


async def upsert_donnees_pro(
    db: AsyncSession,
    tenant_id: UUID,
    dossier: Dossier,
    **fields,
) -> DonneesPro:
    """Crée ou met à jour la DonneesPro du dossier. Comportement :
    - les champs scalaires (fonction, situation_familiale…) sont écrasés
    - le champ `extra` (JSONB) est **fusionné** avec l'existant (les nouvelles
      clés remplacent les anciennes mais les clés non touchées sont conservées).
    Permet d'enrichir progressivement le dossier au fil du parcours.
    """
    stmt = select(DonneesPro).where(DonneesPro.dossier_id == dossier.id)
    dp = (await db.execute(stmt)).scalar_one_or_none()

    # Ne pas écraser avec une valeur None — laisse la valeur en place
    clean_fields = {k: v for k, v in fields.items() if v is not None}

    if dp is None:
        # Création initiale — utilise extra=... tel quel
        dp = DonneesPro(tenant_id=tenant_id, dossier_id=dossier.id, **clean_fields)
        db.add(dp)
    else:
        for k, v in clean_fields.items():
            if k == "extra" and isinstance(v, dict):
                # Merge avec l'existant pour préserver les anciennes clés
                merged = dict(dp.extra or {})
                merged.update(v)
                dp.extra = merged
            else:
                setattr(dp, k, v)
    await db.flush()
    return dp


async def submit_dossier(db: AsyncSession, dossier: Dossier) -> None:
    dossier.status = DossierStatus.soumis
    dossier.submitted_at = datetime.now(timezone.utc)
    await db.flush()

    await audit_service.log(
        db=db,
        tenant_id=dossier.tenant_id,
        action=AuditAction.dossier_submitted,
        resource_type="dossier",
        resource_id=str(dossier.id),
        details={"dossier_number": dossier.dossier_number},
    )
