"""API conformité ARTCI / RGPD.

Endpoints :
    GET    /api/security/policy
        → snapshot lisible de la politique de sécurité effective du tenant

    GET    /api/security/retention/preview
        → liste des dossiers éligibles à la purge selon la politique de rétention

    GET    /api/security/dossiers/{id}/export
        → export RGPD individuel d'un dossier au format JSON
        → audité (data_export)
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.tenancy import AuthContext, get_auth_context
from app.models import (
    AuditAction, Consentement, Conversation, DonneesPro, Dossier,
    EndUser, Message, PieceIdentite, UserRole,
)
from app.services import anonymization_service, audit_service, rbac_service, security_policy

router = APIRouter(prefix="/api/security", tags=["security"])


def _require_admin(ctx: AuthContext) -> None:
    if ctx.role not in (UserRole.super_admin, UserRole.tenant_admin):
        raise HTTPException(
            status_code=403,
            detail="Seuls les administrateurs peuvent accéder à la conformité.",
        )


def _resolve_tenant(ctx: AuthContext) -> UUID:
    if not ctx.tenant_id:
        raise HTTPException(status_code=400, detail="Aucun tenant lié à la session.")
    return ctx.tenant_id


@router.get("/policy")
async def get_policy(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Snapshot de la politique sécurité effective du tenant."""
    _require_admin(ctx)
    tenant_id = _resolve_tenant(ctx)
    policy = await security_policy.get_policy(db, tenant_id)
    return {
        "password": {
            "min_length": policy.password_min_length,
            "require_uppercase": policy.password_require_uppercase,
            "require_digit": policy.password_require_digit,
            "require_special": policy.password_require_special,
        },
        "session": {
            "idle_minutes": policy.session_idle_minutes,
            "max_failed_attempts": policy.login_max_failed_attempts,
            "lockout_minutes": policy.login_lockout_minutes,
        },
        "retention_artci": {
            "dossier_retention_years": policy.dossier_retention_years,
            "grace_days": policy.retention_grace_days,
            "purge_after_inactivity": f"{policy.dossier_retention_years} ans + "
                                      f"{policy.retention_grace_days} jours de grâce",
        },
        "droits": {
            "dpo_response_days": policy.dpo_response_days,
            "dpo_email": policy.dpo_email,
        },
    }


@router.get("/retention/preview")
async def retention_preview(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Liste des dossiers éligibles à la purge selon la politique courante.

    N'effectue PAS la purge — c'est un audit / aperçu seulement. La purge
    effective sera ajoutée plus tard via une scheduled task (Phase B).
    """
    _require_admin(ctx)
    tenant_id = _resolve_tenant(ctx)
    policy = await security_policy.get_policy(db, tenant_id)
    now = datetime.now(timezone.utc)

    # On considère "last_activity" comme max(updated_at, validated_at) du dossier
    stmt = select(Dossier).where(Dossier.tenant_id == tenant_id)
    rows = (await db.execute(stmt)).scalars().all()

    eligible = []
    upcoming = []  # dossiers approchant l'échéance (< 90j)
    for d in rows:
        last_activity = d.validated_at or d.updated_at or d.created_at
        if last_activity is None:
            continue
        deadline = security_policy.compute_retention_deadline(last_activity, policy)
        days_remaining = (deadline - now).days

        entry = {
            "dossier_id": str(d.id),
            "dossier_number": d.dossier_number,
            "status": d.status.value,
            "last_activity_at": last_activity.isoformat(),
            "purge_deadline": deadline.isoformat(),
            "days_remaining": days_remaining,
        }
        if days_remaining <= 0:
            eligible.append(entry)
        elif days_remaining <= 90:
            upcoming.append(entry)

    return {
        "policy": {
            "retention_years": policy.dossier_retention_years,
            "grace_days": policy.retention_grace_days,
        },
        "eligible_for_purge": eligible,
        "upcoming_purges": upcoming,
        "summary": {
            "total_dossiers": len(rows),
            "eligible_count": len(eligible),
            "upcoming_count": len(upcoming),
        },
    }


@router.get("/dossiers/{dossier_id}/export")
async def export_dossier_rgpd(
    dossier_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Export RGPD complet d'un dossier au format JSON.

    Inclut : dossier, données pro, pièces, consentements, conversations,
    messages. Toute exécution est auditée via AuditAction.data_export.

    F-02 — le contrôle d'export est désormais uniforme sur TOUS les
    endpoints : on s'appuie sur `require_permission("conformite", "export")`
    déclarée dans le profil RBAC, au lieu du raccourci `_require_admin`.
    Un rôle métier « Conformité » peut ainsi être délégué sans avoir à
    accorder les droits d'administration système.
    """
    await rbac_service.require_permission(db, ctx, "conformite", "export")
    tenant_id = _resolve_tenant(ctx)

    stmt = (
        select(Dossier)
        .where(Dossier.id == dossier_id, Dossier.tenant_id == tenant_id)
        .options(
            selectinload(Dossier.pieces),
            selectinload(Dossier.donnees_pro),
            selectinload(Dossier.consentements),
        )
    )
    dossier = (await db.execute(stmt)).scalar_one_or_none()
    if dossier is None:
        raise HTTPException(status_code=404, detail="Dossier introuvable")

    # End user + conversations
    end_user = (
        await db.execute(select(EndUser).where(EndUser.id == dossier.end_user_id))
    ).scalar_one_or_none()

    convs_stmt = select(Conversation).where(
        Conversation.tenant_id == tenant_id,
        Conversation.end_user_id == dossier.end_user_id,
    )
    conversations = list((await db.execute(convs_stmt)).scalars().all())

    msgs_stmt = select(Message).where(
        Message.conversation_id.in_([c.id for c in conversations])
    ).order_by(Message.created_at.asc()) if conversations else None
    messages = list((await db.execute(msgs_stmt)).scalars().all()) if msgs_stmt is not None else []

    payload = {
        "export_metadata": {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "exported_by": str(ctx.user_id),
            "tenant_id": str(tenant_id),
            "format_version": "1.0",
            "purpose": "Demande de droit d'accès ARTCI / RGPD art.15",
        },
        "end_user": _serialize_end_user(end_user) if end_user else None,
        "dossier": _serialize_dossier(dossier),
        "donnees_pro": _serialize_donnees_pro(dossier.donnees_pro) if dossier.donnees_pro else None,
        "pieces": [_serialize_piece(p) for p in dossier.pieces],
        "consentements": [_serialize_consentement(c) for c in dossier.consentements],
        "conversations": [_serialize_conversation(c) for c in conversations],
        "messages": [_serialize_message(m) for m in messages],
    }

    await audit_service.log(
        db,
        tenant_id=tenant_id,
        action=AuditAction.data_export,
        resource_type="dossier",
        resource_id=str(dossier.id),
        actor_type="user",
        actor_id=str(ctx.user_id),
        details={
            "format": "json",
            "scope": "rgpd_individual_export",
            "messages_count": len(messages),
            "pieces_count": len(dossier.pieces),
        },
    )
    await db.commit()
    return payload


# ====================================================================== #
# Anonymisation US-28
# ====================================================================== #
class AnonymizeRequest(BaseModel):
    """Lancement d'anonymisation par le DPO (US-28)."""
    confirm: bool = Field(
        ...,
        description="DOIT être true. Confirmation explicite pour exécuter (irréversible).",
    )
    reason: str = Field(min_length=10, max_length=512, description="Motif consigné pour traçabilité")


@router.post("/dossiers/{dossier_id}/anonymize")
async def anonymize_dossier(
    dossier_id: UUID,
    payload: AnonymizeRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Exécute le droit à l'oubli sur un dossier (US-28).

    Réservé aux admins (le DPO doit avoir un compte tenant_admin ou super_admin).
    Irréversible. Produit un accusé d'exécution.
    """
    _require_admin(ctx)
    tenant_id = _resolve_tenant(ctx)

    if not payload.confirm:
        raise HTTPException(
            status_code=400,
            detail="Confirmation explicite requise (confirm=true). Cette opération est irréversible.",
        )

    try:
        receipt = await anonymization_service.anonymize_dossier(
            db,
            dossier_id=dossier_id,
            tenant_id=tenant_id,
            actor_id=ctx.user_id,
            reason=payload.reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    await db.commit()
    return receipt


# ====================================================================== #
# Page publique ARTCI — formulaire de contact (US-29 AC3)
# ====================================================================== #
class ArtciContactIn(BaseModel):
    """Soumission depuis la page publique /artci (sans authentification)."""
    full_name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    subject: str = Field(min_length=2, max_length=255)
    message: str = Field(min_length=10, max_length=4000)
    request_type: str = Field(
        default="access",
        description="access | rectification | deletion | opposition | other",
    )
    tenant_slug: str = Field(default="ma2e", min_length=1, max_length=64)


@router.post("/artci/contact", status_code=202)
async def artci_contact(
    payload: ArtciContactIn,
    db: AsyncSession = Depends(get_db),
):
    """Endpoint **public** (pas d'auth) qui reçoit les demandes ARTCI et
    notifie le DPO du tenant sous 24h (US-29 AC3).

    Best-effort : si SMTP indisponible, la demande est tout de même enregistrée
    dans le journal d'audit pour relance manuelle par le DPO.
    """
    from app.models import Tenant
    from app.services import email_service, settings_service

    tenant = (
        await db.execute(select(Tenant).where(Tenant.slug == payload.tenant_slug))
    ).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant inconnu")

    # DPO email depuis settings.security.dpo_email
    try:
        dpo_email = await settings_service.get_value(
            db, tenant.id, "security", "dpo_email"
        )
    except Exception:
        dpo_email = "dpo@ma2e.ci"

    # 1) Trace dans l'audit (la demande est conservée même si l'email échoue)
    await audit_service.log(
        db,
        tenant_id=tenant.id,
        action=AuditAction.artci_contact_received,
        resource_type="artci_contact",
        resource_id=payload.email,
        actor_type="public",
        actor_id=payload.email,
        details={
            "full_name": payload.full_name,
            "request_type": payload.request_type,
            "subject": payload.subject[:255],
            "message_preview": payload.message[:512],
            "dpo_target": dpo_email,
        },
    )
    await db.commit()

    # 2) Notification DPO best-effort
    try:
        subject = f"[ARTCI/{payload.request_type}] Demande de {payload.full_name} — {payload.subject}"
        text_body = (
            f"Nouvelle demande reçue via la page publique ARTCI.\n\n"
            f"Type      : {payload.request_type}\n"
            f"Nom       : {payload.full_name}\n"
            f"Email     : {payload.email}\n"
            f"Objet     : {payload.subject}\n\n"
            f"Message :\n{payload.message}\n\n"
            f"—\n"
            f"Délai légal de réponse : 30 jours (art.18-22 loi 2013-450).\n"
            f"Cette demande est tracée dans le journal d'audit MA2E (action artci_contact_received)."
        )
        html_body = "<pre style=\"font-family:monospace;\">" + text_body.replace("<", "&lt;") + "</pre>"
        await email_service.send_email(dpo_email, subject, html_body, text_body=text_body)
    except Exception as e:  # noqa: BLE001
        # On ne fait pas échouer la requête publique — la trace audit suffit
        # pour que le DPO puisse retrouver la demande.
        import logging
        logging.getLogger(__name__).warning("Notif DPO échouée : %s", e)

    return {
        "received": True,
        "expected_response_within_days": 30,
        "message": (
            "Votre demande a été enregistrée. Le Délégué à la Protection des "
            "Données de MA2E vous répondra sous 30 jours."
        ),
    }


# ====================================================================== #
# Sérialiseurs (clés snake_case, valeurs sérialisables JSON)
# ====================================================================== #
def _iso(dt):
    return dt.isoformat() if dt else None


def _serialize_end_user(u):
    return {
        "id": str(u.id),
        "name": u.name,
        "phone": u.phone,
        "telegram_id": u.telegram_id,
        "extra": u.extra,
        "created_at": _iso(u.created_at),
    }


def _serialize_dossier(d):
    return {
        "id": str(d.id),
        "dossier_number": d.dossier_number,
        "status": d.status.value,
        "matricule": d.matricule,
        "employeur_code": d.employeur_code,
        "rejection_motive": d.rejection_motive,
        "additional_request": d.additional_request,
        "submitted_at": _iso(d.submitted_at),
        "validated_at": _iso(d.validated_at),
        "created_at": _iso(d.created_at),
        "updated_at": _iso(d.updated_at),
    }


def _serialize_donnees_pro(dp):
    return {
        "fonction": dp.fonction,
        "anciennete_annees": dp.anciennete_annees,
        "situation_familiale": dp.situation_familiale,
        "nombre_ayants_droit": dp.nombre_ayants_droit,
        "rib": dp.rib,
        "extra": dp.extra,
        "created_at": _iso(dp.created_at),
    }


def _serialize_piece(p):
    # On ne donne PAS le contenu du blob — uniquement les métadonnées
    return {
        "id": str(p.id),
        "piece_type": p.piece_type.value if p.piece_type else None,
        "face": p.face.value if p.face else None,
        "storage_key": p.storage_key,
        "mime_type": p.mime_type,
        "ocr_status": p.ocr_status,
        "ocr_confidence": p.ocr_confidence,
        "ocr_data": p.ocr_data,
        "mrz_data": p.mrz_data,
        "user_corrections": p.user_corrections,
        "created_at": _iso(p.created_at),
    }


def _serialize_consentement(c):
    return {
        "id": str(c.id),
        "gate": c.gate.value if c.gate else None,
        "decision": c.decision.value if c.decision else None,
        "texte_version": c.texte_version,
        "texte_hash": c.texte_hash,
        "channel": c.channel,
        "ip_or_phone": c.ip_or_phone,
        "created_at": _iso(c.created_at),
    }


def _serialize_conversation(c):
    return {
        "id": str(c.id),
        "channel": c.channel.value if c.channel else None,
        "state": c.state,
        "last_activity_at": _iso(c.last_activity_at),
        "created_at": _iso(c.created_at),
    }


def _serialize_message(m):
    return {
        "id": str(m.id),
        "conversation_id": str(m.conversation_id),
        "direction": m.direction.value if m.direction else None,
        "content": m.content,
        "created_at": _iso(m.created_at),
    }
