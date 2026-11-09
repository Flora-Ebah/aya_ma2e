"""Modèle en mémoire d'un parcours conversationnel + logique de diff.

Détaché de la source (Excel historique → remplacé par extraction LLM depuis
Word/PDF/texte libre). Toute la logique dépendante du format Excel a été
supprimée ; ne reste ici que la structure, la validation et le diff.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ParcoursMeta:
    name: str = "Parcours MA2E"
    description: str = ""
    language: str = "fr"


@dataclass
class ParcoursStep:
    order: int
    code: str
    label: str
    type: str  # message | question | action | decision
    question: Optional[str] = None
    template_code: Optional[str] = None
    action_name: Optional[str] = None
    next_step_code: Optional[str] = None
    branches: Dict[str, str] = field(default_factory=dict)
    validation_rules: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    """Phrase courte expliquant à l'utilisateur ce que fait cette étape.
    Affichée en sous-titre du formulaire/sélecteur dans le chat web."""
    meta: Dict[str, Any] = field(default_factory=dict)
    """Métadonnées libres (show_when, switch_to_step, dynamic_router…).
    `description` est injectée automatiquement dedans à la persistance."""


@dataclass
class ParcoursDocument:
    meta: ParcoursMeta
    steps: List[ParcoursStep]
    messages: Dict[str, str]

    def ensure_valid(self) -> List[str]:
        errors: List[str] = []
        codes = [s.code for s in self.steps]
        if not codes:
            errors.append("Le parcours doit contenir au moins une étape.")
        if len(codes) != len(set(codes)):
            dup = {c for c in codes if codes.count(c) > 1}
            errors.append(f"Codes d'étape dupliqués : {', '.join(sorted(dup))}.")
        valid_types = {"message", "question", "action", "decision"}
        for step in self.steps:
            if step.type not in valid_types:
                errors.append(
                    f"Étape {step.code} : type « {step.type} » invalide "
                    f"(attendu : {', '.join(sorted(valid_types))})."
                )
            if step.next_step_code and step.next_step_code not in codes:
                errors.append(
                    f"Étape {step.code} : étape suivante « {step.next_step_code} » introuvable."
                )
            for cond, target in step.branches.items():
                if target and target not in codes:
                    errors.append(
                        f"Étape {step.code} : branche « {cond} » pointe vers "
                        f"« {target} » qui n'existe pas."
                    )
        return errors


@dataclass
class ParcoursDiff:
    added_steps: List[str] = field(default_factory=list)
    removed_steps: List[str] = field(default_factory=list)
    modified_steps: List[str] = field(default_factory=list)
    added_messages: List[str] = field(default_factory=list)
    removed_messages: List[str] = field(default_factory=list)
    modified_messages: List[str] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not any(
            [
                self.added_steps,
                self.removed_steps,
                self.modified_steps,
                self.added_messages,
                self.removed_messages,
                self.modified_messages,
            ]
        )


def diff_parcours(before: Optional[ParcoursDocument], after: ParcoursDocument) -> ParcoursDiff:
    diff = ParcoursDiff()
    before_steps = {s.code: s for s in (before.steps if before else [])}
    after_steps = {s.code: s for s in after.steps}

    for code in after_steps:
        if code not in before_steps:
            diff.added_steps.append(code)
        elif _steps_differ(before_steps[code], after_steps[code]):
            diff.modified_steps.append(code)
    for code in before_steps:
        if code not in after_steps:
            diff.removed_steps.append(code)

    before_msgs = (before.messages if before else {}) or {}
    after_msgs = after.messages or {}
    for code, txt in after_msgs.items():
        if code not in before_msgs:
            diff.added_messages.append(code)
        elif before_msgs[code] != txt:
            diff.modified_messages.append(code)
    for code in before_msgs:
        if code not in after_msgs:
            diff.removed_messages.append(code)
    return diff


def _steps_differ(a: ParcoursStep, b: ParcoursStep) -> bool:
    for attr in (
        "order",
        "label",
        "type",
        "question",
        "template_code",
        "action_name",
        "next_step_code",
        "branches",
        "validation_rules",
        "description",
        "meta",
    ):
        if getattr(a, attr) != getattr(b, attr):
            return True
    return False


def document_to_dict(doc: ParcoursDocument) -> Dict[str, Any]:
    return {
        "meta": {
            "name": doc.meta.name,
            "description": doc.meta.description,
            "language": doc.meta.language,
        },
        "steps": [
            {
                "order": s.order,
                "code": s.code,
                "label": s.label,
                "type": s.type,
                "question": s.question,
                "template_code": s.template_code,
                "action_name": s.action_name,
                "next_step_code": s.next_step_code,
                "branches": s.branches,
                "validation_rules": s.validation_rules,
                "description": s.description,
                "meta": s.meta,
            }
            for s in doc.steps
        ],
        "messages": doc.messages,
    }


def document_from_dict(payload: Dict[str, Any]) -> ParcoursDocument:
    meta_raw = payload.get("meta") or {}
    meta = ParcoursMeta(
        name=str(meta_raw.get("name") or "Parcours MA2E").strip(),
        description=str(meta_raw.get("description") or "").strip(),
        language=str(meta_raw.get("language") or "fr").strip() or "fr",
    )
    steps_raw = payload.get("steps") or []
    steps: List[ParcoursStep] = []
    for i, s in enumerate(steps_raw, start=1):
        code = str(s.get("code") or "").strip()
        if not code:
            raise ValueError(f"Étape {i} : code manquant.")
        steps.append(
            ParcoursStep(
                order=int(s.get("order") or i),
                code=code,
                label=str(s.get("label") or code).strip(),
                type=str(s.get("type") or "question").strip().lower(),
                question=(str(s.get("question")).strip() if s.get("question") else None),
                template_code=(str(s.get("template_code")).strip() if s.get("template_code") else None),
                action_name=(str(s.get("action_name")).strip() if s.get("action_name") else None),
                next_step_code=(str(s.get("next_step_code")).strip() if s.get("next_step_code") else None),
                branches=dict(s.get("branches") or {}),
                validation_rules=dict(s.get("validation_rules") or {}),
                description=str(s.get("description") or "").strip(),
                meta=dict(s.get("meta") or {}),
            )
        )
    steps.sort(key=lambda x: x.order)
    messages = {str(k): str(v) for k, v in (payload.get("messages") or {}).items()}
    doc = ParcoursDocument(meta=meta, steps=steps, messages=messages)
    errors = doc.ensure_valid()
    if errors:
        raise ValueError("\n".join(errors))
    return doc
