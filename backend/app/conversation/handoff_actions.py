"""Actions backend pour les parcours Consultation / Mise à jour / Chat libre.

Complète `default_actions.py` (dédié à l'Inscription) avec :
  - `lookup_dossier_by_matricule` : cherche un dossier existant
  - `apply_dossier_update` : applique une modification d'information
  - `rag_answer_question` : réponse RAG sur la base de connaissances

Chaque action suit la convention `@workflow_action` : lit le contexte,
peut muter les données, retourne une `ActionResult` avec branche + message.
"""
from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.conversation.workflow_actions import ActionResult, workflow_action
from app.models import Dossier, DossierStatus, EndUser

logger = logging.getLogger(__name__)


STATUS_LABEL = {
    DossierStatus.en_cours: "En cours de constitution",
    DossierStatus.soumis: "Soumis, en attente de validation",
    DossierStatus.en_validation: "En cours de validation par un gestionnaire",
    DossierStatus.valide: "✅ Validé",
    DossierStatus.rejete: "❌ Rejeté",
    DossierStatus.complement_requis: "📎 Complément demandé",
}


def _fmt_date(dt) -> str:
    """Format court FR d'une datetime (ou '—' si None)."""
    return dt.strftime("%d/%m/%Y") if dt else "—"


def _last_input_for(context: dict, step_code: str) -> Optional[str]:
    """Récupère la dernière réponse utilisateur pour un step donné."""
    return context.get(f"{step_code}_input")


# ======================================================================
# 1. Consultation — lookup dossier par matricule
# ======================================================================
@workflow_action(
    "lookup_dossier_by_matricule",
    branches=["not_found"],
    branch_labels={"not_found": "Aucun dossier trouvé pour ce matricule"},
    display_label="Rechercher le dossier par matricule",
    description=(
        "Cherche un dossier existant pour le matricule saisi. Peuple le "
        "contexte avec dossier_number, status_label, submitted_date, updated_date."
    ),
    category="Consultation",
)
async def lookup_dossier_by_matricule(
    db: AsyncSession,
    context: dict,
    last_input: Optional[str],
) -> ActionResult:
    tenant_id = context.get("_tenant_id")
    matricule = (
        last_input
        or _last_input_for(context, "consult_ask_matricule")
        or _last_input_for(context, "update_ask_matricule")
        or context.get("matricule")
    )
    if not matricule or not tenant_id:
        return ActionResult(branch_key="not_found")

    matricule = matricule.strip()
    result = await db.execute(
        select(Dossier)
        .where(Dossier.tenant_id == UUID(tenant_id))
        .where(Dossier.matricule.ilike(matricule))
        .order_by(Dossier.created_at.desc())
    )
    dossier = result.scalars().first()
    if dossier is None:
        logger.info("lookup_dossier_by_matricule : matricule %s absent", matricule)
        return ActionResult(branch_key="not_found")

    return ActionResult(
        branch_key=None,
        extra_context={
            "dossier_id": str(dossier.id),
            "dossier_number": dossier.dossier_number,
            "status": dossier.status.value,
            "status_label": STATUS_LABEL.get(dossier.status, dossier.status.value),
            "submitted_date": _fmt_date(dossier.submitted_at),
            "updated_date": _fmt_date(dossier.updated_at),
            "matricule": dossier.matricule or matricule,
        },
    )


# ======================================================================
# 2. Mise à jour — application d'une modification
# ======================================================================
FIELD_CHOICES = {
    "1": ("email", "email"),
    "2": ("téléphone", "phone"),
    "3": ("adresse postale", "adresse"),
    "4": ("situation familiale", "situation_familiale"),
    "5": ("coordonnées bancaires", "rib"),
}


@workflow_action(
    "apply_dossier_update",
    branches=[],
    display_label="Appliquer la modification demandée",
    description=(
        "Enregistre la nouvelle valeur du champ choisi. Le mapping choix→champ "
        "est : 1=email, 2=téléphone, 3=adresse, 4=situation familiale, 5=RIB."
    ),
    category="Mise à jour",
)
async def apply_dossier_update(
    db: AsyncSession,
    context: dict,
    last_input: Optional[str],
) -> ActionResult:
    field_choice = _last_input_for(context, "update_choose_field") or ""
    new_value = last_input or _last_input_for(context, "update_ask_new_value") or ""
    dossier_id = context.get("dossier_id")

    field_choice = field_choice.strip()
    new_value = new_value.strip()

    if field_choice not in FIELD_CHOICES:
        return ActionResult(
            branch_key=None,
            message="⚠️ Choix de champ invalide. Modification ignorée.",
        )
    if not new_value:
        return ActionResult(
            branch_key=None,
            message="⚠️ Nouvelle valeur vide. Modification ignorée.",
        )
    if not dossier_id:
        return ActionResult(
            branch_key=None,
            message="⚠️ Dossier introuvable dans le contexte. Recommencez la consultation.",
        )

    label, extra_key = FIELD_CHOICES[field_choice]

    # Récupère le dossier + end_user associé pour muter le bon endroit
    dossier = (
        await db.execute(select(Dossier).where(Dossier.id == UUID(dossier_id)))
    ).scalar_one_or_none()
    if dossier is None:
        return ActionResult(
            branch_key=None,
            message="⚠️ Dossier introuvable. Modification ignorée.",
        )

    end_user = (
        await db.execute(select(EndUser).where(EndUser.id == dossier.end_user_id))
    ).scalar_one_or_none()
    if end_user is None:
        return ActionResult(
            branch_key=None,
            message="⚠️ Sociétaire introuvable. Modification ignorée.",
        )

    # Applique dans le bon champ (phone en direct, le reste dans extra)
    if extra_key == "phone":
        end_user.phone = new_value
    else:
        extra = dict(end_user.extra or {})
        extra[extra_key] = new_value
        end_user.extra = extra

    logger.info(
        "apply_dossier_update : dossier=%s field=%s → %s",
        dossier.dossier_number, extra_key, new_value[:40],
    )
    await db.flush()

    return ActionResult(
        branch_key=None,
        message=f"✅ *{label.capitalize()}* mis à jour.",
    )


# ======================================================================
# 3. Chat libre — réponse RAG
# ======================================================================
@workflow_action(
    "rag_answer_question",
    branches=[],
    display_label="Répondre à la question via RAG",
    description=(
        "Interroge la base de connaissances MA2E (vecteurs pgvector) et "
        "génère une réponse via Azure OpenAI. Fallback poli si aucune donnée."
    ),
    category="FAQ",
)
async def rag_answer_question(
    db: AsyncSession,
    context: dict,
    last_input: Optional[str],
) -> ActionResult:
    tenant_id = context.get("_tenant_id")
    question = (
        last_input
        or _last_input_for(context, "chat_ask_question")
        or ""
    ).strip()

    if not question or not tenant_id:
        return ActionResult(
            branch_key=None,
            message="Je n'ai pas bien compris la question. Pouvez-vous reformuler ?",
        )

    try:
        # Import tardif : rag charge des modèles lourds au boot
        from app.services import rag
        result = await rag.answer_question(
            db,
            tenant_id=UUID(tenant_id),
            tenant_name="MA2E",
            question=question,
        )
        answer_text = result.answer or (
            "Désolée, je n'ai pas trouvé d'information dans la base pour "
            "répondre à cette question. Contactez le support MA2E."
        )
    except Exception as e:
        logger.warning("RAG a échoué : %s", e)
        answer_text = (
            "🛠️ Le service de réponse est temporairement indisponible. "
            "Réessayez dans quelques instants."
        )

    return ActionResult(
        branch_key=None,
        extra_context={"rag_answer": answer_text},
        message=answer_text,
    )
