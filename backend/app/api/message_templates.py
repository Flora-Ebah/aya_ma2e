"""API REST des templates de messages tenant-scoped.

Endpoints :
    GET    /api/templates/groups
        → liste des groupes de templates (Onboarding, Validation, Support…)

    GET    /api/templates
        → tous les templates du tenant (filtrable par ?group=Onboarding)

    GET    /api/templates/{code}
        → un template (vue détail)

    PUT    /api/templates/{code}
        → personnalise le contenu (validation registry + audit + cache invalidation)

    POST   /api/templates/{code}/preview
        → prévisualise un rendu sans persister (utile pour l'UI admin)

    POST   /api/templates/{code}/reset
        → réinitialise au défaut du registry

    GET    /api/templates/{code}/history
        → historique des versions

    POST   /api/templates/{code}/rollback/{target_version}
        → rollback à une version antérieure
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.tenancy import AuthContext, get_auth_context
from app.models import UserRole
from app.models.message_template import MessageChannel, MessageTemplate
from app.schemas.message_template import (
    TemplateGroupOut,
    TemplateHistoryOut,
    TemplateOut,
    TemplatePreviewIn,
    TemplatePreviewOut,
    TemplateUpsertIn,
)
from app.services import message_template_service
from app.services.message_template_registry import (
    MessageTemplateDescriptor,
    template_registry,
)

router = APIRouter(prefix="/api/templates", tags=["templates"])


# ====================================================================== #
# Helpers
# ====================================================================== #
def _resolve_tenant(ctx: AuthContext) -> UUID:
    if not ctx.tenant_id:
        raise HTTPException(
            status_code=400,
            detail="Aucun tenant associé à votre session — précisez le tenant cible.",
        )
    return ctx.tenant_id


def _require_admin(ctx: AuthContext) -> None:
    if ctx.role not in (UserRole.super_admin, UserRole.tenant_admin):
        raise HTTPException(
            status_code=403,
            detail="Seuls les administrateurs peuvent modifier les templates.",
        )


def _to_template_out(
    descriptor: MessageTemplateDescriptor,
    row: Optional[MessageTemplate],
    language: str = "fr",
) -> TemplateOut:
    is_default = row is None
    return TemplateOut(
        code=descriptor.code,
        language=language,
        label=descriptor.label,
        description=descriptor.description,
        group=descriptor.group,
        channel=(row.channel.value if row else descriptor.channel.value),
        subject=(row.subject if row else descriptor.default_subject_fr),
        content=(row.content if row else descriptor.default_fr),
        required_vars=list(descriptor.required_vars),
        optional_vars=list(descriptor.optional_vars),
        max_length=descriptor.max_length,
        version=row.version if row else 1,
        is_default=is_default,
        updated_at=row.updated_at if row else None,
        updated_by=row.updated_by if row else None,
    )


def _parse_channel(value: Optional[str]) -> Optional[MessageChannel]:
    if value is None:
        return None
    # Mapping façade : "any" → MessageChannel.any_
    mapping = {
        "whatsapp": MessageChannel.whatsapp,
        "email": MessageChannel.email,
        "web_chat": MessageChannel.web_chat,
        "sms": MessageChannel.sms,
        "any": MessageChannel.any_,
    }
    if value not in mapping:
        raise HTTPException(status_code=422, detail=f"Canal invalide : {value}")
    return mapping[value]


# ====================================================================== #
# Endpoints
# ====================================================================== #
@router.get("/groups", response_model=list[str])
async def list_groups(
    ctx: AuthContext = Depends(get_auth_context),
):
    """Liste des groupes de templates disponibles."""
    return template_registry.groups()


@router.get("", response_model=list[TemplateGroupOut])
async def list_templates(
    group: Optional[str] = Query(default=None, description="Filtre par groupe"),
    language: str = Query(default="fr"),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Retourne tous les templates, regroupés par groupe.

    Si `group` est précisé, retourne uniquement ce groupe.
    """
    tenant_id = _resolve_tenant(ctx)
    pairs = await message_template_service.list_templates(
        db, tenant_id=tenant_id, group=group, language=language
    )

    # Regroupement par group
    by_group: dict[str, list[TemplateOut]] = {}
    for descriptor, row in pairs:
        by_group.setdefault(descriptor.group, []).append(
            _to_template_out(descriptor, row, language)
        )

    return [
        TemplateGroupOut(group=g, templates=items)
        for g, items in by_group.items()
    ]


@router.get("/{code}", response_model=TemplateOut)
async def get_template(
    code: str,
    language: str = Query(default="fr"),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Retourne un template spécifique."""
    tenant_id = _resolve_tenant(ctx)
    try:
        descriptor, row = await message_template_service.get_template(
            db, tenant_id=tenant_id, code=code, language=language
        )
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Template inconnu : {code}")
    return _to_template_out(descriptor, row, language)


@router.put("/{code}", response_model=TemplateOut)
async def upsert_template(
    code: str,
    payload: TemplateUpsertIn,
    language: str = Query(default="fr"),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Crée ou met à jour un template (admin uniquement)."""
    _require_admin(ctx)
    tenant_id = _resolve_tenant(ctx)

    try:
        channel = _parse_channel(payload.channel)
        row = await message_template_service.upsert_template(
            db,
            tenant_id=tenant_id,
            code=code,
            content=payload.content,
            subject=payload.subject,
            channel=channel,
            language=language,
            updated_by=ctx.user_id,
            change_reason=payload.change_reason,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Template inconnu : {code}")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    await db.commit()
    await db.refresh(row)
    descriptor = template_registry.get(code)
    return _to_template_out(descriptor, row, language)


@router.post("/{code}/preview", response_model=TemplatePreviewOut)
async def preview_template(
    code: str,
    payload: TemplatePreviewIn,
    language: str = Query(default="fr"),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Prévisualise le rendu d'un template sans persistance.

    Si `payload.content` est fourni, prévisualise ce contenu (utile dans l'UI
    admin pour montrer un aperçu en temps réel). Sinon, utilise le contenu
    actuel (BD ou défaut).
    """
    tenant_id = _resolve_tenant(ctx)
    try:
        descriptor = template_registry.get(code)
        if descriptor is None:
            raise KeyError(code)

        if payload.content is not None:
            content_to_render = payload.content
            subject_to_render = None
        else:
            subject_to_render, content_to_render = await message_template_service.get_content(
                db, tenant_id=tenant_id, code=code, language=language
            )

        # Variables référencées dans le contenu mais absentes du payload
        used = template_registry.extract_vars(content_to_render)
        missing = sorted(v for v in used if v not in payload.variables)

        rendered_subject = (
            template_registry.render(subject_to_render, payload.variables)
            if subject_to_render
            else None
        )
        rendered_content = template_registry.render(content_to_render, payload.variables)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Template inconnu : {code}")

    return TemplatePreviewOut(
        subject=rendered_subject,
        rendered=rendered_content,
        missing_variables=missing,
    )


@router.post("/{code}/reset", response_model=TemplateOut)
async def reset_template(
    code: str,
    language: str = Query(default="fr"),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Réinitialise un template à sa valeur par défaut."""
    _require_admin(ctx)
    tenant_id = _resolve_tenant(ctx)
    try:
        row = await message_template_service.reset_to_default(
            db,
            tenant_id=tenant_id,
            code=code,
            language=language,
            updated_by=ctx.user_id,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Template inconnu : {code}")

    await db.commit()
    await db.refresh(row)
    descriptor = template_registry.get(code)
    return _to_template_out(descriptor, row, language)


@router.get("/{code}/history", response_model=list[TemplateHistoryOut])
async def list_history(
    code: str,
    language: str = Query(default="fr"),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Historique des versions d'un template (du plus récent au plus ancien)."""
    tenant_id = _resolve_tenant(ctx)
    try:
        history = await message_template_service.list_history(
            db, tenant_id=tenant_id, code=code, language=language, limit=limit
        )
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Template inconnu : {code}")
    return [TemplateHistoryOut.model_validate(h) for h in history]


@router.post("/{code}/rollback/{target_version}", response_model=TemplateOut)
async def rollback_template(
    code: str,
    target_version: int,
    language: str = Query(default="fr"),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Restaure une version antérieure d'un template."""
    _require_admin(ctx)
    tenant_id = _resolve_tenant(ctx)
    try:
        row = await message_template_service.rollback_to_version(
            db,
            tenant_id=tenant_id,
            code=code,
            target_version=target_version,
            language=language,
            updated_by=ctx.user_id,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Template inconnu : {code}")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    await db.commit()
    await db.refresh(row)
    descriptor = template_registry.get(code)
    return _to_template_out(descriptor, row, language)
