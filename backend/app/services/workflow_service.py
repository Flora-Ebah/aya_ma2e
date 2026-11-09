"""WorkflowService — CRUD des workflows conversationnels.

Le workflow actif (`Workflow.active = True`) est celui que le moteur exécutera
en runtime (à venir Phase 3). En attendant, l'éditeur back-office peut créer,
modifier, dupliquer et activer/désactiver des workflows.
"""
from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.workflow import Workflow, WorkflowStep, WorkflowStepType

logger = logging.getLogger(__name__)

POSITION_STEP = 10  # incrément entre positions pour permettre l'insertion


# ----------------------------------------------------------------------
# WORKFLOWS
# ----------------------------------------------------------------------
async def list_workflows(db: AsyncSession) -> list[Workflow]:
    """Liste les workflows ordonnés par `position` (puis created_at en fallback)."""
    result = await db.execute(
        select(Workflow).order_by(Workflow.position.asc(), Workflow.created_at.asc())
    )
    return list(result.scalars().all())


async def reorder_workflows(db: AsyncSession, ordered_ids: list[UUID]) -> list[Workflow]:
    """Réindexe les positions des workflows selon l'ordre fourni.

    `ordered_ids` doit lister tous les IDs de workflow dans le nouvel ordre
    désiré. Positions régénérées par tranches de 10.
    """
    result = await db.execute(select(Workflow))
    workflows = list(result.scalars().all())
    by_id = {w.id: w for w in workflows}

    requested = set(ordered_ids)
    existing = set(by_id.keys())
    if requested != existing:
        missing = sorted(str(i) for i in existing - requested)
        extras = sorted(str(i) for i in requested - existing)
        raise HTTPException(
            status_code=400,
            detail=(
                f"Liste d'ordre invalide. Manquants : {missing}, "
                f"inconnus : {extras}."
            ),
        )

    for idx, wid in enumerate(ordered_ids, start=1):
        by_id[wid].position = idx * POSITION_STEP
    await db.commit()
    # `updated_at` a onupdate=func.now() côté serveur — refresh ciblé pour
    # éviter un lazy-load qui crash en contexte async (MissingGreenlet).
    for w in workflows:
        await db.refresh(w, attribute_names=["updated_at"])
    return sorted(workflows, key=lambda w: w.position)


async def set_active(db: AsyncSession, workflow_id: UUID, active: bool) -> Workflow:
    """Active ou désactive UN workflow sans toucher aux autres.

    Contrairement à `activate_workflow` qui rend ce workflow exclusivement actif,
    cette fonction est un simple toggle on/off. Utilisée pour les architectures
    multi-parcours où plusieurs workflows coexistent.
    """
    wf = await get_workflow(db, workflow_id)
    if active:
        if not wf.steps:
            raise HTTPException(
                status_code=400,
                detail="Impossible d'activer un parcours vide. Ajoutez au moins une étape.",
            )
        if wf.start_step_code:
            valid_codes = {s.code for s in wf.steps}
            if wf.start_step_code not in valid_codes:
                raise HTTPException(
                    status_code=400,
                    detail=f"L'étape de démarrage '{wf.start_step_code}' n'existe pas dans ce parcours.",
                )
    wf.active = active
    await db.commit()
    await db.refresh(wf, attribute_names=["updated_at"])
    logger.info("Workflow %s — actif=%s", wf.name, active)
    return wf


async def get_workflow(db: AsyncSession, workflow_id: UUID) -> Workflow:
    result = await db.execute(
        select(Workflow)
        .options(selectinload(Workflow.steps))
        .where(Workflow.id == workflow_id)
    )
    wf = result.scalar_one_or_none()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow introuvable.")
    return wf


async def get_active_workflow(db: AsyncSession) -> Optional[Workflow]:
    """Retourne le workflow actif courant (avec steps), ou None s'il n'y en a pas."""
    result = await db.execute(
        select(Workflow)
        .options(selectinload(Workflow.steps))
        .where(Workflow.active.is_(True))
        .order_by(Workflow.updated_at.desc())
    )
    return result.scalars().first()


async def create_workflow(
    db: AsyncSession,
    *,
    name: str,
    description: Optional[str] = None,
    start_step_code: Optional[str] = None,
) -> Workflow:
    wf = Workflow(
        name=name,
        description=description,
        start_step_code=start_step_code,
        active=False,
        version=1,
    )
    db.add(wf)
    await db.commit()
    await db.refresh(wf)
    return wf


async def update_workflow(
    db: AsyncSession,
    workflow_id: UUID,
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
    start_step_code: Optional[str] = None,
) -> Workflow:
    wf = await get_workflow(db, workflow_id)
    if name is not None:
        wf.name = name
    if description is not None:
        wf.description = description
    if start_step_code is not None:
        wf.start_step_code = start_step_code or None
    await db.commit()
    await db.refresh(wf)
    return wf


async def activate_workflow(db: AsyncSession, workflow_id: UUID) -> Workflow:
    """Active ce workflow. AUCUN autre workflow n'est désactivé — l'admin peut
    avoir plusieurs versions actives et choisit explicitement de supprimer les
    anciennes via l'icône corbeille s'il le souhaite.
    """
    wf = await get_workflow(db, workflow_id)
    if not wf.steps:
        raise HTTPException(
            status_code=400,
            detail="Impossible d'activer un workflow vide. Ajoutez au moins une étape.",
        )
    if not wf.start_step_code:
        raise HTTPException(
            status_code=400,
            detail="Définissez l'étape de démarrage avant d'activer ce workflow.",
        )
    valid_codes = {s.code for s in wf.steps}
    if wf.start_step_code not in valid_codes:
        raise HTTPException(
            status_code=400,
            detail=f"L'étape de démarrage '{wf.start_step_code}' n'existe pas dans ce workflow.",
        )
    wf.active = True
    await db.commit()
    await db.refresh(wf)
    logger.info("Workflow activé : %s (v%s)", wf.name, wf.version)
    return wf


async def deactivate_all(db: AsyncSession) -> int:
    """Désactive tous les workflows. Utile pour bascule manuelle. Retourne le nb désactivé."""
    res = await db.execute(
        update(Workflow).where(Workflow.active.is_(True)).values(active=False)
    )
    await db.commit()
    return res.rowcount or 0


async def delete_workflow(db: AsyncSession, workflow_id: UUID) -> None:
    """Supprime un workflow (actif ou non). Les étapes sont supprimées en
    cascade. Si le workflow était actif, le bot n'a plus de parcours jouable
    tant qu'un autre n'est pas activé — c'est au caller d'avertir l'utilisateur.
    """
    wf = await get_workflow(db, workflow_id)
    await db.delete(wf)
    await db.commit()


# ----------------------------------------------------------------------
# STEPS
# ----------------------------------------------------------------------
async def _next_position(db: AsyncSession, workflow_id: UUID) -> int:
    result = await db.execute(
        select(WorkflowStep.position)
        .where(WorkflowStep.workflow_id == workflow_id)
        .order_by(WorkflowStep.position.desc())
        .limit(1)
    )
    last = result.scalar_one_or_none()
    return (last or 0) + POSITION_STEP


async def create_step(
    db: AsyncSession,
    workflow_id: UUID,
    *,
    code: str,
    label: str,
    type: WorkflowStepType,
    template_code: Optional[str] = None,
    action_name: Optional[str] = None,
    next_step_code: Optional[str] = None,
    branches: Optional[dict] = None,
    validation_rules: Optional[dict] = None,
    prompt_variables: Optional[dict] = None,
    meta: Optional[dict] = None,
    position: Optional[int] = None,
) -> WorkflowStep:
    # Vérifie l'unicité du code dans le workflow
    existing = (
        await db.execute(
            select(WorkflowStep).where(
                WorkflowStep.workflow_id == workflow_id,
                WorkflowStep.code == code,
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Une étape avec le code '{code}' existe déjà dans ce workflow.",
        )

    pos = position if position is not None else await _next_position(db, workflow_id)
    step = WorkflowStep(
        workflow_id=workflow_id,
        code=code,
        label=label,
        type=type,
        template_code=template_code,
        action_name=action_name,
        next_step_code=next_step_code,
        branches=branches or {},
        validation_rules=validation_rules or {},
        prompt_variables=prompt_variables or {},
        meta=meta or {},
        position=pos,
    )
    db.add(step)
    await db.commit()
    await db.refresh(step)
    return step


async def update_step(
    db: AsyncSession,
    step_id: UUID,
    **patch,
) -> WorkflowStep:
    result = await db.execute(select(WorkflowStep).where(WorkflowStep.id == step_id))
    step = result.scalar_one_or_none()
    if not step:
        raise HTTPException(status_code=404, detail="Étape introuvable.")
    # Si on renomme le code, vérifier l'unicité
    new_code = patch.get("code")
    if new_code and new_code != step.code:
        conflict = (
            await db.execute(
                select(WorkflowStep).where(
                    WorkflowStep.workflow_id == step.workflow_id,
                    WorkflowStep.code == new_code,
                    WorkflowStep.id != step_id,
                )
            )
        ).scalar_one_or_none()
        if conflict:
            raise HTTPException(
                status_code=409,
                detail=f"Une autre étape utilise déjà le code '{new_code}'.",
            )
    for k, v in patch.items():
        if v is None:
            continue
        setattr(step, k, v)
    await db.commit()
    await db.refresh(step)
    return step


async def delete_step(db: AsyncSession, step_id: UUID) -> None:
    result = await db.execute(select(WorkflowStep).where(WorkflowStep.id == step_id))
    step = result.scalar_one_or_none()
    if not step:
        raise HTTPException(status_code=404, detail="Étape introuvable.")
    await db.delete(step)
    await db.commit()


async def reorder_steps(
    db: AsyncSession,
    workflow_id: UUID,
    ordered_codes: list[str],
) -> list[WorkflowStep]:
    """Réindexe les positions selon l'ordre fourni.

    `ordered_codes` doit lister tous les codes du workflow, dans le nouvel ordre
    désiré. Les positions sont régénérées par tranches de 10.
    """
    result = await db.execute(
        select(WorkflowStep).where(WorkflowStep.workflow_id == workflow_id)
    )
    steps = list(result.scalars().all())
    by_code = {s.code: s for s in steps}

    missing = set(by_code) - set(ordered_codes)
    extras = set(ordered_codes) - set(by_code)
    if missing or extras:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Liste d'ordre invalide. Manquants : {sorted(missing)}, "
                f"inconnus : {sorted(extras)}."
            ),
        )

    for idx, code in enumerate(ordered_codes, start=1):
        by_code[code].position = idx * POSITION_STEP
    await db.commit()
    return sorted(steps, key=lambda s: s.position)
