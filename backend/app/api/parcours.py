"""API « Parcours IA » — pilotage par upload d'un document libre (Word/PDF/TXT).

Flux :

1. L'admin rédige un document (Word de préférence) avec le titre du parcours
   et la liste numérotée des questions à poser.
2. Il le dépose dans l'UI (``POST /extract``) → le backend extrait le texte,
   demande au LLM de produire le JSON structuré, calcule un diff vs la version
   active et renvoie le tout — SANS rien persister.
3. L'admin peut corriger le JSON dans l'UI (type d'étape, validations) puis
   clique « Appliquer » (``POST /apply``) : le backend persiste le JSON corrigé
   comme nouvelle version active.
4. Rollback possible via ``POST /versions/{id}/activate``.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.tenancy import AuthContext, get_auth_context, get_default_tenant_id
from app.models import UserRole
from app.models.message_template import MessageChannel
from app.models.workflow import Workflow, WorkflowStep, WorkflowStepType
from app.services import workflow_service, workflow_template_service
from app.services.file_text_extractor import ExtractionError, SUPPORTED_EXTENSIONS, extract_text
from app.services.parcours_llm import extract_parcours_from_text
from app.services.parcours_schema import (
    ParcoursDocument,
    ParcoursMeta,
    ParcoursStep,
    diff_parcours,
    document_from_dict,
    document_to_dict,
)

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/parcours", tags=["parcours"])

# Formats acceptés pour l'extraction (xlsx exclu : plus de template Excel)
ACCEPTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


def _require_admin(ctx: AuthContext) -> None:
    if ctx.role not in (UserRole.super_admin, UserRole.tenant_admin):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Réservé aux administrateurs.")


# ---------------------------------------------------------------------------
# Modèles de réponse
# ---------------------------------------------------------------------------


class VersionOut(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    version: int
    active: bool
    steps_count: int
    created_at: str
    updated_at: str


class DiffOut(BaseModel):
    name: str
    language: str
    description: str
    steps_count: int
    messages_count: int
    added_steps: List[str]
    removed_steps: List[str]
    modified_steps: List[str]
    added_messages: List[str]
    removed_messages: List[str]
    modified_messages: List[str]
    is_empty: bool


class ExtractOut(BaseModel):
    document: Dict[str, Any] = Field(..., description="Parcours extrait, prêt à être renvoyé à /apply tel quel.")
    diff: DiffOut


class ApplyPayload(BaseModel):
    document: Dict[str, Any] = Field(..., description="JSON du parcours (meta + steps + messages).")


class ApplyOut(BaseModel):
    workflow_id: UUID
    version: int
    activated: bool
    diff: DiffOut


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _workflow_to_doc(
    db: AsyncSession,
    tenant_id: UUID,
    wf: Workflow,
) -> ParcoursDocument:
    steps_sorted = sorted(wf.steps, key=lambda s: s.position)
    steps: List[ParcoursStep] = []
    messages: Dict[str, str] = {}
    for idx, s in enumerate(steps_sorted, start=1):
        template_code = s.template_code or workflow_template_service.derive_code(s.code)
        content = await workflow_template_service.get_content(db, tenant_id, template_code)
        if content:
            messages[template_code] = content
        steps.append(
            ParcoursStep(
                order=idx,
                code=s.code,
                label=s.label,
                type=s.type.value if hasattr(s.type, "value") else str(s.type),
                question=content,
                template_code=template_code,
                action_name=s.action_name,
                next_step_code=s.next_step_code,
                branches=dict(s.branches or {}),
                validation_rules=dict(s.validation_rules or {}),
                description=str((s.meta or {}).get("description") or ""),
                meta=dict(s.meta or {}),
            )
        )
    return ParcoursDocument(
        meta=ParcoursMeta(name=wf.name, description=wf.description or "", language="fr"),
        steps=steps,
        messages=messages,
    )


def _diff_to_out(doc: ParcoursDocument, diff) -> DiffOut:
    return DiffOut(
        name=doc.meta.name,
        language=doc.meta.language,
        description=doc.meta.description,
        steps_count=len(doc.steps),
        messages_count=len(doc.messages),
        added_steps=diff.added_steps,
        removed_steps=diff.removed_steps,
        modified_steps=diff.modified_steps,
        added_messages=diff.added_messages,
        removed_messages=diff.removed_messages,
        modified_messages=diff.modified_messages,
        is_empty=diff.is_empty,
    )


async def _read_upload_text(file: UploadFile) -> str:
    from pathlib import Path

    name = file.filename or ""
    ext = Path(name).suffix.lower()
    if ext not in ACCEPTED_EXTENSIONS:
        raise HTTPException(
            400,
            f"Format {ext or '(inconnu)'} non pris en charge. "
            f"Formats acceptés : {', '.join(sorted(ACCEPTED_EXTENSIONS))}.",
        )
    data = await file.read()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(400, "Fichier trop volumineux (max 10 Mo).")
    try:
        return extract_text(name, data)
    except ExtractionError as exc:
        raise HTTPException(400, str(exc)) from exc


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/versions", response_model=List[VersionOut])
async def list_versions(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    _require_admin(ctx)
    rows = (
        await db.execute(select(Workflow).order_by(Workflow.updated_at.desc()))
    ).scalars().all()
    out: List[VersionOut] = []
    for wf in rows:
        steps_count = (
            await db.execute(
                select(WorkflowStep).where(WorkflowStep.workflow_id == wf.id)
            )
        ).scalars().all()
        out.append(
            VersionOut(
                id=wf.id,
                name=wf.name,
                description=wf.description,
                version=wf.version,
                active=wf.active,
                steps_count=len(steps_count),
                created_at=wf.created_at.isoformat(),
                updated_at=wf.updated_at.isoformat(),
            )
        )
    return out


@router.post("/extract", response_model=ExtractOut)
async def extract_upload(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Extrait le parcours depuis un document (Word/PDF/TXT) via LLM, calcule
    le diff vs la version active, et renvoie le JSON SANS rien persister.
    L'UI peut ensuite laisser l'admin corriger le JSON avant /apply."""
    _require_admin(ctx)
    text = await _read_upload_text(file)
    tenant_id = await get_default_tenant_id(db)
    try:
        doc = await extract_parcours_from_text(
            text, filename=file.filename or "", db=db, tenant_id=tenant_id,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    active = await workflow_service.get_active_workflow(db)
    before = None
    if active:
        before = await _workflow_to_doc(db, tenant_id, active)
    diff = diff_parcours(before, doc)

    return ExtractOut(document=document_to_dict(doc), diff=_diff_to_out(doc, diff))


@router.post("/apply", response_model=ApplyOut)
async def apply_document(
    payload: ApplyPayload = Body(...),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Persiste le JSON (potentiellement corrigé côté UI) comme nouvelle
    version active. Désactive l'ancienne en transaction."""
    _require_admin(ctx)
    try:
        doc = document_from_dict(payload.document)
    except ValueError as exc:
        raise HTTPException(400, f"Parcours invalide :\n{exc}") from exc

    tenant_id = await get_default_tenant_id(db)

    # Récupère toutes les versions existantes PORTANT LE MÊME NOM — uniquement
    # pour numéroter la nouvelle version (v1, v2…) et calculer le diff vs la
    # version active actuelle. AUCUN workflow existant n'est désactivé : le
    # nouveau est juste ajouté en actif à côté des autres. Si l'admin veut
    # désactiver une version précédente, il clique sur 🗑 explicitement.
    same_name_rows = (
        await db.execute(
            select(Workflow)
            .options(selectinload(Workflow.steps))
            .where(Workflow.name == doc.meta.name)
            .order_by(Workflow.version.desc())
        )
    ).scalars().all()
    previous_active = next((wf for wf in same_name_rows if wf.active), None)
    highest_version = same_name_rows[0].version if same_name_rows else 0

    before = (
        await _workflow_to_doc(db, tenant_id, previous_active)
        if previous_active
        else None
    )
    diff = diff_parcours(before, doc)

    new_version = highest_version + 1
    start_step_code = doc.steps[0].code if doc.steps else None
    wf = Workflow(
        name=doc.meta.name,
        description=doc.meta.description or None,
        active=True,
        version=new_version,
        start_step_code=start_step_code,
    )
    db.add(wf)
    await db.flush()

    for i, s in enumerate(doc.steps, start=1):
        try:
            step_type = WorkflowStepType(s.type)
        except ValueError:
            step_type = WorkflowStepType.question
        # Un template unique par step, dérivé du step code. Le LLM n'est pas
        # déterministe : il assigne parfois le même `template_code` à plusieurs
        # steps distincts (ex. toutes les étapes photo/signature pointées vers
        # `ma2e.confirm`), ce qui fait rendre le même texte partout au runtime.
        # On ignore donc la suggestion LLM pour les steps "question" et "message".
        # On préserve `s.template_code` seulement pour les steps système reconnus
        # (préfixe `ma2e.`) sur des types sans contenu dynamique (action).
        if step_type == WorkflowStepType.action and s.template_code and s.template_code.startswith("ma2e."):
            template_code = s.template_code
        else:
            template_code = workflow_template_service.derive_code(s.code)
        # Meta = tout ce que le LLM / post-processing ont posé (show_when,
        # dynamic_router, switch_to_step…) + description injectée pour l'UI.
        step_meta = dict(s.meta or {})
        if s.description:
            step_meta["description"] = s.description
        step = WorkflowStep(
            workflow_id=wf.id,
            code=s.code,
            label=s.label,
            type=step_type,
            template_code=template_code,
            action_name=s.action_name,
            next_step_code=s.next_step_code,
            branches=s.branches or {},
            validation_rules=s.validation_rules or {},
            prompt_variables={},
            meta=step_meta,
            position=i * 10,
        )
        db.add(step)

        # Prompt à stocker : s.question si fourni, sinon on construit un
        # prompt lisible à partir de description/label pour éviter le fallback
        # ultime `[label]` au runtime (cas photo/signature où le LLM ne pose
        # pas de "question" textuelle).
        question_content = s.question
        if not question_content and step_type != WorkflowStepType.action:
            parts = []
            if s.label:
                parts.append(f"*{s.label}*")
            if s.description:
                parts.append(s.description)
            question_content = "\n\n".join(parts) if parts else None
        if question_content:
            await workflow_template_service.upsert(
                db,
                tenant_id,
                template_code,
                question_content,
                channel=MessageChannel.any_,
                updated_by=ctx.user_id,
            )

    for code, content in doc.messages.items():
        await workflow_template_service.upsert(
            db,
            tenant_id,
            code,
            content,
            channel=MessageChannel.any_,
            updated_by=ctx.user_id,
        )

    await db.commit()
    await db.refresh(wf)
    log.info(
        "Parcours appliqué : %s v%s (steps=%d, messages=%d) par user=%s",
        wf.name,
        wf.version,
        len(doc.steps),
        len(doc.messages),
        ctx.user_id,
    )
    return ApplyOut(
        workflow_id=wf.id,
        version=wf.version,
        activated=True,
        diff=_diff_to_out(doc, diff),
    )


@router.get("/versions/{wf_id}/document")
async def get_version_document(
    wf_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Retourne le ParcoursDocument complet (meta + steps + messages) pour
    une version précise — utilisé par l'UI pour afficher le contenu déplié
    d'un parcours dans l'historique.
    """
    _require_admin(ctx)
    wf = (
        await db.execute(
            select(Workflow)
            .options(selectinload(Workflow.steps))
            .where(Workflow.id == wf_id)
        )
    ).scalar_one_or_none()
    if wf is None:
        raise HTTPException(404, "Version introuvable.")
    tenant_id = await get_default_tenant_id(db)
    doc = await _workflow_to_doc(db, tenant_id, wf)
    return document_to_dict(doc)


@router.post("/versions/{wf_id}/activate", response_model=VersionOut)
async def activate_version(
    wf_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    _require_admin(ctx)
    wf = await workflow_service.activate_workflow(db, wf_id)
    steps = (
        await db.execute(
            select(WorkflowStep).where(WorkflowStep.workflow_id == wf.id)
        )
    ).scalars().all()
    return VersionOut(
        id=wf.id,
        name=wf.name,
        description=wf.description,
        version=wf.version,
        active=wf.active,
        steps_count=len(steps),
        created_at=wf.created_at.isoformat(),
        updated_at=wf.updated_at.isoformat(),
    )


@router.delete("/versions/{wf_id}", status_code=204)
async def delete_version(
    wf_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    _require_admin(ctx)
    await workflow_service.delete_workflow(db, wf_id)
    return Response(status_code=204)
