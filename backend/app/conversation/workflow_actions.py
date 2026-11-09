"""Action registry pour le WorkflowExecutor.

Les steps de type `action` référencent une fonction par son `action_name`. Ces
fonctions sont enregistrées ici via le décorateur `@workflow_action(name)`.

Signature d'une action :
    async def my_action(
        db: AsyncSession,
        context: dict,
        last_input: str | None,
    ) -> ActionResult

Le `context` est le dict `Conversation.context` ; les inputs précédents y sont
stockés (ex. `context["matricule"] = "12345"`). L'action peut le muter.

Le résultat porte :
- `branch_key` : clé optionnelle pour brancher sur `WorkflowStep.branches[key]`
  (ex. "duplicate", "not_found"). Si None, on suit `next_step_code`.
- `extra_context` : dict à fusionner dans le context (ex. {"dossier_id": ...}).
- `message` : texte à envoyer à l'utilisateur en complément (optionnel).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Optional

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class ActionResult:
    branch_key: Optional[str] = None
    extra_context: dict = field(default_factory=dict)
    message: Optional[str] = None


@dataclass
class ActionMetadata:
    """Métadonnées exposées au workflow editor pour décrire une action.

    - `service` : clé de service (ex. "mindee_ocr"). Si défini, le toggle
      `services.<service>_enabled` peut désactiver l'action depuis l'UI.
    - `branches` : liste des `branch_key` que l'action peut retourner. Sert
      à proposer les bonnes options dans l'éditeur visuel de branches.
    - `branch_labels` : dict {branch_key: libellé français court} pour
      afficher des choix lisibles dans le dropdown (ex. "Code incorrect"
      au lieu de "invalid_code").
    - `display_label` : nom affiché dans le dropdown (français), le nom
      technique étant le sous-titre.
    - `description` : phrase descriptive sous le dropdown.
    - `category` : groupement visuel ("Identification", "OCR", "OTP"…).
    """

    service: Optional[str] = None
    branches: list[str] = field(default_factory=list)
    branch_labels: dict = field(default_factory=dict)
    display_label: str = ""
    description: str = ""
    category: str = "Autre"


ActionFn = Callable[[AsyncSession, dict, Optional[str]], Awaitable[ActionResult]]

_REGISTRY: dict[str, ActionFn] = {}
_METADATA: dict[str, ActionMetadata] = {}


def workflow_action(
    name: str,
    *,
    service: Optional[str] = None,
    branches: Optional[list[str]] = None,
    branch_labels: Optional[dict[str, str]] = None,
    display_label: str = "",
    description: str = "",
    category: str = "Autre",
):
    """Décorateur d'enregistrement.

    Usage :
        @workflow_action(
            "ocr_extract_recto",
            service="mindee_ocr",
            branches=["disabled", "no_media", "unreadable", "low_score"],
            branch_labels={
                "disabled": "Service désactivé",
                "no_media": "Aucune photo reçue",
                "unreadable": "Photo illisible",
                "low_score": "Score OCR faible",
            },
            display_label="Analyser le recto (OCR Mindee)",
            description="OCR Mindee + Groq sur le recto de la pièce",
            category="OCR",
        )
        async def ocr_extract_recto(db, context, last_input): ...
    """

    def decorator(fn: ActionFn) -> ActionFn:
        if name in _REGISTRY:
            logger.warning("Action workflow '%s' redéfinie (ancienne écrasée).", name)
        _REGISTRY[name] = fn
        _METADATA[name] = ActionMetadata(
            service=service,
            branches=list(branches or []),
            branch_labels=dict(branch_labels or {}),
            display_label=display_label or name,  # fallback sur le nom technique
            description=description,
            category=category,
        )
        return fn

    return decorator


def get_action(name: str) -> Optional[ActionFn]:
    return _REGISTRY.get(name)


def get_metadata(name: str) -> Optional[ActionMetadata]:
    return _METADATA.get(name)


def list_actions() -> list[str]:
    return sorted(_REGISTRY.keys())


def list_actions_detailed() -> list[dict]:
    """Retourne chaque action avec ses métadonnées, triée par catégorie puis nom."""
    out = []
    for name in sorted(_REGISTRY.keys()):
        meta = _METADATA.get(name) or ActionMetadata(display_label=name)
        out.append({
            "name": name,
            "service": meta.service,
            "branches": meta.branches,
            "branch_labels": meta.branch_labels,
            "display_label": meta.display_label or name,
            "description": meta.description,
            "category": meta.category,
        })
    return out
