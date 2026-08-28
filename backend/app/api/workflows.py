"""API CRUD des workflows conversationnels.

L'édition est réservée aux administrateurs (tenant_admin / super_admin).
Le runtime conversationnel (moteur d'exécution) est branché en Phase 3 ;
en attendant, l'éditeur permet de préparer et valider le parcours.
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.conversation import default_actions  # noqa: F401 (enregistre les actions)
from app.conversation import handoff_actions  # noqa: F401 (enregistre lookup/update/rag)
from app.conversation import workflow_executor
from app.conversation.workflow_actions import list_actions, list_actions_detailed
from app.core.database import get_db
from app.core.tenancy import AuthContext, get_auth_context, get_default_tenant_id
from app.models import UserRole
from app.schemas.workflow import (
    WorkflowCreate,
    WorkflowDetailOut,
    WorkflowOut,
    WorkflowStepCreate,
    WorkflowStepOut,
    WorkflowStepReorderRequest,
    WorkflowStepUpdate,
    WorkflowUpdate,
)
from app.services import workflow_service, workflow_template_service

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


def _require_admin(ctx: AuthContext) -> None:
    if ctx.role not in (UserRole.super_admin, UserRole.tenant_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Réservé aux administrateurs.",
        )


# ====================================================================== #
# Workflows
# ====================================================================== #
@router.get("", response_model=list[WorkflowOut])
async def list_workflows(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    return await workflow_service.list_workflows(db)


async def _enrich_steps_with_template_content(
    db: AsyncSession,
    tenant_id: UUID,
    workflow: WorkflowDetailOut,
) -> WorkflowDetailOut:
    """Charge le contenu courant du template pour chaque step et l'embarque
    dans la réponse — évite au frontend un round-trip par step."""
    for step in workflow.steps:
        code = step.template_code or workflow_template_service.derive_code(step.code)
        content = await workflow_template_service.get_content(db, tenant_id, code)
        step.template_content = content
    return workflow


@router.get("/active", response_model=WorkflowDetailOut | None)
async def get_active_workflow(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    wf = await workflow_service.get_active_workflow(db)
    if wf is None:
        return None
    tenant_id = await get_default_tenant_id(db)
    out = WorkflowDetailOut.model_validate(wf)
    return await _enrich_steps_with_template_content(db, tenant_id, out)


@router.get("/{workflow_id}", response_model=WorkflowDetailOut)
async def get_workflow(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    wf = await workflow_service.get_workflow(db, workflow_id)
    tenant_id = await get_default_tenant_id(db)
    out = WorkflowDetailOut.model_validate(wf)
    return await _enrich_steps_with_template_content(db, tenant_id, out)


@router.post("", response_model=WorkflowOut, status_code=201)
async def create_workflow(
    payload: WorkflowCreate,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    _require_admin(ctx)
    return await workflow_service.create_workflow(
        db,
        name=payload.name,
        description=payload.description,
        start_step_code=payload.start_step_code,
    )


@router.patch("/{workflow_id}", response_model=WorkflowOut)
async def update_workflow(
    workflow_id: UUID,
    payload: WorkflowUpdate,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    _require_admin(ctx)
    return await workflow_service.update_workflow(
        db,
        workflow_id,
        name=payload.name,
        description=payload.description,
        start_step_code=payload.start_step_code,
    )


@router.post("/{workflow_id}/activate", response_model=WorkflowOut)
async def activate_workflow(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    _require_admin(ctx)
    return await workflow_service.activate_workflow(db, workflow_id)


@router.delete("/{workflow_id}", status_code=204)
async def delete_workflow(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    _require_admin(ctx)
    await workflow_service.delete_workflow(db, workflow_id)


class ReorderWorkflowsRequest(BaseModel):
    ordered_ids: list[UUID]


@router.post("/reorder", response_model=list[WorkflowOut])
async def reorder_workflows(
    payload: ReorderWorkflowsRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    _require_admin(ctx)
    return await workflow_service.reorder_workflows(db, payload.ordered_ids)


class SetActiveRequest(BaseModel):
    active: bool


@router.post("/{workflow_id}/set-active", response_model=WorkflowOut)
async def set_active(
    workflow_id: UUID,
    payload: SetActiveRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Active ou désactive ce parcours indépendamment des autres (multi-actif OK)."""
    _require_admin(ctx)
    return await workflow_service.set_active(db, workflow_id, payload.active)


# ====================================================================== #
# Steps
# ====================================================================== #
async def _persist_template_content(
    db: AsyncSession,
    tenant_id: UUID,
    *,
    template_code: Optional[str],
    step_code: str,
    template_content: Optional[str],
    updated_by: Optional[UUID],
) -> None:
    """Upsert le contenu du template si fourni (non-None). Auto-dérive le code
    si template_code est vide → 'workflow.<step_code>'."""
    if template_content is None:
        return
    code = template_code or workflow_template_service.derive_code(step_code)
    await workflow_template_service.upsert(
        db, tenant_id, code, template_content, updated_by=updated_by,
    )


@router.post("/{workflow_id}/steps", response_model=WorkflowStepOut, status_code=201)
async def create_step(
    workflow_id: UUID,
    payload: WorkflowStepCreate,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    _require_admin(ctx)
    step = await workflow_service.create_step(
        db,
        workflow_id,
        code=payload.code,
        label=payload.label,
        type=payload.type,
        template_code=payload.template_code,
        action_name=payload.action_name,
        next_step_code=payload.next_step_code,
        branches=payload.branches,
        validation_rules=payload.validation_rules,
        prompt_variables=payload.prompt_variables,
        meta=payload.meta,
        position=payload.position,
    )
    tenant_id = await get_default_tenant_id(db)
    await _persist_template_content(
        db, tenant_id,
        template_code=step.template_code,
        step_code=step.code,
        template_content=payload.template_content,
        updated_by=ctx.user_id,
    )
    await db.commit()
    out = WorkflowStepOut.model_validate(step)
    out.template_content = payload.template_content
    return out


@router.patch("/{workflow_id}/steps/{step_id}", response_model=WorkflowStepOut)
async def update_step(
    workflow_id: UUID,
    step_id: UUID,
    payload: WorkflowStepUpdate,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    _require_admin(ctx)
    patch = payload.model_dump(exclude_unset=True)
    template_content = patch.pop("template_content", None)
    step = await workflow_service.update_step(db, step_id, **patch)
    tenant_id = await get_default_tenant_id(db)
    if template_content is not None:
        await _persist_template_content(
            db, tenant_id,
            template_code=step.template_code,
            step_code=step.code,
            template_content=template_content,
            updated_by=ctx.user_id,
        )
        await db.commit()
    out = WorkflowStepOut.model_validate(step)
    out.template_content = template_content if template_content is not None else (
        await workflow_template_service.get_content(
            db, tenant_id,
            step.template_code or workflow_template_service.derive_code(step.code),
        )
    )
    return out


@router.delete("/{workflow_id}/steps/{step_id}", status_code=204)
async def delete_step(
    workflow_id: UUID,
    step_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    _require_admin(ctx)
    await workflow_service.delete_step(db, step_id)


class ReorderRequest(BaseModel):
    ordered_codes: list[str]


@router.post("/{workflow_id}/steps/reorder", response_model=list[WorkflowStepOut])
async def reorder_steps(
    workflow_id: UUID,
    payload: ReorderRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    _require_admin(ctx)
    return await workflow_service.reorder_steps(db, workflow_id, payload.ordered_codes)


# ====================================================================== #
# Simulateur — pour tester le workflow sans toucher au webhook
# ====================================================================== #
class SimulateRequest(BaseModel):
    current_step_code: Optional[str] = None
    """Code de l'étape courante. None = démarrage du parcours."""

    user_input: Optional[str] = None
    """Réponse simulée du sociétaire."""

    context: dict = {}
    """Contexte de conversation accumulé (variables collectées jusqu'ici)."""


class SimulateResponse(BaseModel):
    messages: list[str]
    next_step_code: Optional[str]
    is_terminal: bool
    context: dict
    error: Optional[str] = None


@router.post("/{workflow_id}/simulate", response_model=SimulateResponse)
async def simulate_workflow(
    workflow_id: UUID,
    payload: SimulateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
):
    """Simule un tour de conversation contre le workflow.

    Le caller fournit l'état courant ; on retourne l'état suivant + les
    messages à afficher. Aucune écriture en BD réelle (actions en mode
    simulateur via le flag `_simulate` dans le contexte).

    F-10 — le simulateur expose la logique conversationnelle complète
    (messages, branches, actions). Il doit être réservé aux administrateurs,
    au même titre que les endpoints de modification de workflow, pour éviter
    qu'un compte en lecture seule ne cartographie l'intégralité du parcours
    et n'abuse de la simulation comme charge sur le serveur.
    """
    _require_admin(ctx)
    wf = await workflow_executor.load_workflow(db, workflow_id)
    if wf is None:
        raise HTTPException(status_code=404, detail="Workflow introuvable.")

    tenant_id = await get_default_tenant_id(db)
    sim_context = {**(payload.context or {}), "_simulate": True}

    result = await workflow_executor.execute(
        db,
        workflow=wf,
        tenant_id=tenant_id,
        current_step_code=payload.current_step_code,
        user_input=payload.user_input,
        context=sim_context,
    )

    return SimulateResponse(
        messages=result.messages,
        next_step_code=result.next_step_code,
        is_terminal=result.is_terminal,
        context=result.context,
        error=result.error,
    )


@router.get("/_meta/actions", response_model=list[str])
async def list_registered_actions(
    ctx: AuthContext = Depends(get_auth_context),
):
    """Retourne la liste des `action_name` enregistrés côté backend.

    Utile pour proposer une auto-complétion dans l'éditeur de step.

    F-10 (cohérence) — l'éditeur de workflow est un outil d'administration.
    Exposer le catalogue des actions à un viewer permet de cartographier la
    logique interne (au même titre que le simulate). Soumis au même contrôle
    de rôle que les autres endpoints d'action de workflow.
    """
    _require_admin(ctx)
    return list_actions()


class ActionDetail(BaseModel):
    name: str                           # nom technique (ex. "ocr_extract_recto")
    display_label: str = ""             # libellé humain français pour l'UI
    service: Optional[str] = None       # clé du service lié (mindee_ocr…)
    branches: list[str] = []            # branch_keys que l'action peut retourner
    branch_labels: dict[str, str] = {}  # {branch_key: libellé français}
    description: str = ""
    category: str = "Autre"


@router.get("/_meta/actions/detailed", response_model=list[ActionDetail])
async def list_registered_actions_detailed(
    ctx: AuthContext = Depends(get_auth_context),
):
    """Liste enrichie des actions avec leurs métadonnées (service lié, branches
    disponibles, catégorie). Consommée par le modal d'édition de step pour :
    - regrouper visuellement les actions par catégorie (Identification, OCR, OTP…)
    - afficher le service associé + son état d'activation
    - proposer les branch_keys déjà connues quand l'admin ajoute une branche

    F-10 (cohérence) — même contrôle admin que `/_meta/actions`.
    """
    _require_admin(ctx)
    return list_actions_detailed()
