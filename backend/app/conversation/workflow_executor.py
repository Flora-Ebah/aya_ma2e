"""Moteur d'exécution des workflows conversationnels dynamiques.

Lit le workflow actif depuis la BD et avance pas à pas. L'état conversationnel
est porté par `Conversation.state` (= code de l'étape courante) et
`Conversation.context` (= dict du contexte métier accumulé).

Cycle d'exécution :
1. Pour un step `message` : envoie le template puis enchaîne immédiatement
   sur `next_step_code` (boucle interne, sans retour à l'utilisateur).
2. Pour un step `question` : envoie le template, retourne au caller pour
   attendre la réponse utilisateur. À la prochaine entrée, valide + transition.
3. Pour un step `action` : appelle la fonction registered, transitionne selon
   `branch_key` ou `next_step_code`. Enchaîne immédiatement.
4. Pour un step `decision` : évalue la règle, transitionne. Enchaîne.

Le caller (webhook ou simulateur) appelle `advance(user_input)` à chaque
message reçu. La méthode retourne :
- le texte à envoyer
- l'état suivant à persister
- des indications de fin de parcours
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.conversation.workflow_actions import ActionResult, get_action
from app.models.workflow import Workflow, WorkflowStep, WorkflowStepType
from app.services import workflow_template_service
from app.services.message_template_service import render as render_template

logger = logging.getLogger(__name__)

# Garde-fou : évite les boucles infinies si un workflow mal câblé pointe sur
# lui-même via une chaîne d'actions/messages sans question.
MAX_INTERNAL_STEPS = 25


@dataclass
class ExecuteResult:
    """Résultat d'une étape d'exécution renvoyée au caller."""

    messages: list[str] = field(default_factory=list)
    """Tous les textes à envoyer à l'utilisateur (concaténation des steps
    `message` enchaînés)."""

    next_step_code: Optional[str] = None
    """Le code de l'étape qui attend la prochaine entrée utilisateur.
    None = fin du parcours."""

    is_terminal: bool = False
    """True si le parcours est terminé (plus aucune étape suivante)."""

    switch_to_step: Optional[str] = None
    """Si non-None : le dispatcher doit charger le workflow contenant ce step
    et relancer execute() dessus (transition inter-parcours depuis le menu)."""

    context: dict = field(default_factory=dict)
    """Le contexte mis à jour, à persister dans `Conversation.context`."""

    error: Optional[str] = None
    """Message d'erreur lisible (workflow inconnu, step manquante…)."""

    ui: Optional[dict] = None
    """Hint UI structuré (rendu riche côté web). Voir BotReply.ui."""


async def list_active_workflows(db: AsyncSession) -> list[Workflow]:
    """Tous les workflows actifs, triés par position puis date de création.
    Utilisé pour construire le menu d'accueil WhatsApp."""
    result = await db.execute(
        select(Workflow)
        .where(Workflow.active.is_(True))
        .order_by(Workflow.position.asc(), Workflow.created_at.asc())
    )
    return list(result.scalars().all())


async def load_active_workflow(db: AsyncSession) -> Optional[Workflow]:
    """Retourne le workflow actif de plus petite position.

    ORDER BY position garantit un choix stable quand plusieurs workflows
    sont marqués actifs (sinon Postgres renvoie n'importe lequel).
    """
    result = await db.execute(
        select(Workflow)
        .options(selectinload(Workflow.steps))
        .where(Workflow.active.is_(True))
        .order_by(Workflow.position.asc(), Workflow.created_at.asc())
    )
    return result.scalars().first()


async def load_workflow(db: AsyncSession, workflow_id: UUID) -> Optional[Workflow]:
    result = await db.execute(
        select(Workflow)
        .options(selectinload(Workflow.steps))
        .where(Workflow.id == workflow_id)
    )
    return result.scalars().first()


async def load_workflow_by_step_code(db: AsyncSession, step_code: str) -> Optional[Workflow]:
    """Trouve le workflow qui contient un step avec ce code.

    Utile pour :
    - reprendre une conversation dans le bon workflow via son state
    - basculer d'un workflow à un autre depuis un menu inter-parcours
    """
    step = (
        await db.execute(
            select(WorkflowStep).where(WorkflowStep.code == step_code).limit(1)
        )
    ).scalar_one_or_none()
    if step is None:
        return None
    return await load_workflow(db, step.workflow_id)


def _build_step_index(workflow: Workflow) -> dict[str, WorkflowStep]:
    return {step.code: step for step in workflow.steps}


async def _validate_question_input(
    db: AsyncSession,
    tenant_id: UUID,
    step: WorkflowStep,
    user_input: str,
    ctx: dict,
) -> Optional[str]:
    """Retourne `None` si valide, sinon un message d'erreur lisible.

    Si valide, enrichit `ctx` avec les valeurs résolues via référentiel
    (code + label canonique) le cas échéant.
    """
    from app.services import reference_list_service

    rules = step.validation_rules or {}
    text = (user_input or "").strip()

    # Mode multi-select : l'utilisateur envoie une liste CSV de codes/labels
    # ("coordonnees,employeur"). On stocke la liste dans ctx[step.code+"_items"]
    # pour que les steps conditionnels puissent filtrer dessus.
    multi_opts = rules.get("multi_select")
    multi_ref = rules.get("multi_select_ref")
    if multi_opts or multi_ref:
        parts = [p.strip() for p in text.split(",") if p.strip()]
        if not parts:
            return "Merci de sélectionner au moins une option."
        min_s = int(rules.get("min_selected", 1))
        max_s = int(rules.get("max_selected", 99))
        if len(parts) < min_s:
            return f"Veuillez sélectionner au moins {min_s} option(s)."
        if len(parts) > max_s:
            return f"Veuillez sélectionner au plus {max_s} option(s)."
        # Résolution contre options disponibles
        if multi_ref:
            rl = await reference_list_service.get_list_by_key(db, tenant_id, multi_ref)
            allowed = [it for it in (rl.items or [])] if rl else []
        else:
            allowed = list(multi_opts or [])
        resolved_codes: list[str] = []
        resolved_labels: list[str] = []
        for part in parts:
            match = None
            low = part.lower()
            for it in allowed:
                code = str(it.get("code") or it.get("label") or "").lower()
                label = str(it.get("label") or it.get("code") or "").lower()
                if low == code or low == label:
                    match = it
                    break
            if match is None:
                return f"Option « {part} » non reconnue."
            resolved_codes.append(str(match.get("code") or match.get("label")))
            resolved_labels.append(str(match.get("label") or match.get("code")))
        ctx[f"{step.code}_items"] = resolved_codes
        ctx[f"{step.code}_items_labels"] = resolved_labels
        ctx[step.code] = ", ".join(resolved_labels)
        return None

    # Mode « form batch » : la question envoie un modèle à copier/remplir,
    # l'utilisateur renvoie plusieurs lignes `Label: valeur`.
    form_fields = rules.get("form_fields")
    if form_fields and isinstance(form_fields, list):
        parsed, errors = _parse_form_response(text, form_fields)
        # Validation complémentaire : pour chaque field lié à un référentiel,
        # on résout la valeur fournie contre la liste.
        for f in form_fields:
            opts_ref = f.get("options_ref")
            if not opts_ref:
                continue
            key = str(f.get("key") or "").strip()
            if not key or key not in parsed:
                continue  # champ manquant → déjà couvert par _parse_form_response
            value = parsed[key]
            rl = await reference_list_service.get_list_by_key(db, tenant_id, opts_ref)
            if rl is None:
                continue
            resolved = reference_list_service.resolve_value(rl, value)
            if resolved is None and not rl.allow_other:
                items_hint = ", ".join(it.get("label", "") for it in (rl.items or [])[:6])
                errors.append(
                    f"« {f.get('label') or key} » : valeur « {value} » non reconnue. "
                    f"Attendu : {items_hint}."
                )
            elif resolved is not None:
                # Normalise la valeur dans le contexte (code technique) +
                # version lisible.
                ctx[key] = resolved["label"]
                ctx[f"{key}_code"] = resolved["code"]
        if errors:
            return "\n".join(f"- {e}" for e in errors)
        # Les valeurs normalisées remplacent celles brutes dans parsed.
        return None

    # Validation d'un step « question » simple avec options_ref
    opts_ref = rules.get("options_ref")
    if opts_ref:
        rl = await reference_list_service.get_list_by_key(db, tenant_id, opts_ref)
        if rl is not None:
            resolved = reference_list_service.resolve_value(rl, text)
            if resolved is None and not rl.allow_other:
                items_hint = ", ".join(it.get("label", "") for it in (rl.items or [])[:6])
                return (
                    f"Valeur « {text} » non reconnue. "
                    f"Attendu : {items_hint} (ou tapez le numéro)."
                )
            if resolved is not None:
                ctx[step.code] = resolved["label"]
                ctx[f"{step.code}_code"] = resolved["code"]
            return None

    min_len = rules.get("min_len")
    if min_len is not None and len(text) < int(min_len):
        return f"Au moins {min_len} caractère(s) attendu(s)."

    max_len = rules.get("max_len")
    if max_len is not None and len(text) > int(max_len):
        return f"Au plus {max_len} caractère(s) autorisé(s)."

    regex = rules.get("regex")
    if regex:
        try:
            if not re.match(regex, text):
                return rules.get("error_message", "Format invalide.")
        except re.error as e:
            logger.warning("Workflow step %s : regex invalide '%s' (%s)", step.code, regex, e)

    return None


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_DATE_RE = re.compile(r"^(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2,4})$")


def _parse_form_response(text: str, fields: list[dict]) -> tuple[dict, list[str]]:
    """Parse une réponse multi-lignes du type :

        Nom : KONATE
        Prénoms : Bakary
        Date de naissance : 12/05/1988

    Retourne ({key: value}, [erreurs lisibles]). La clé de chaque champ est
    `fields[i]["key"]` ; le `label` sert à retrouver la ligne dans la réponse.
    Les champs `optional=true` manquants ne génèrent pas d'erreur.
    """
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    collected: dict[str, str] = {}
    for line in lines:
        # Accepte « : » ou « ：» (fullwidth)
        for sep in (":", "："):
            if sep in line:
                k, _, v = line.partition(sep)
                key = _normalize_label(k)
                val = v.strip()
                if key and val:
                    collected[key] = val
                break

    out: dict[str, str] = {}
    errors: list[str] = []
    for f in fields:
        key = str(f.get("key") or "").strip()
        label = str(f.get("label") or key).strip()
        optional = bool(f.get("optional"))
        candidates = {_normalize_label(label), _normalize_label(key)}
        value = next((collected[c] for c in candidates if c in collected), None)

        if not value:
            if not optional:
                errors.append(f"« {label} » est manquant.")
            continue

        regex = f.get("regex")
        fmt = (f.get("format") or "").lower()
        msg = f.get("message") or f"« {label} » : format invalide."

        if regex:
            try:
                if not re.match(regex, value):
                    errors.append(msg)
                    continue
            except re.error:
                pass
        if fmt == "email" and not _EMAIL_RE.match(value):
            errors.append(f"« {label} » : adresse email invalide.")
            continue
        if fmt == "date" and not _DATE_RE.match(value):
            errors.append(f"« {label} » : format JJ/MM/AAAA attendu.")
            continue

        out[key] = value
    return out, errors


def _normalize_label(s: str) -> str:
    """Normalise un label pour la recherche : trim, lowercase, enlève accents
    et parenthèses de type « (JJ/MM/AAAA) »."""
    import unicodedata as _ud
    s = (s or "").strip().lower()
    s = re.sub(r"\s*\([^)]*\)", "", s)  # enlève les parenthèses
    s = _ud.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s


# Détection courte du type de parcours d'après son nom — pour afficher dans
# le menu welcome avec un libellé court et un emoji.
_PARCOURS_KINDS = [
    (re.compile(r"inscription", re.I), "✨", "M'inscrire"),
    (re.compile(r"consultation", re.I), "🔍", "Consulter mon dossier"),
    (re.compile(r"mise[- ]à[- ]jour|modification", re.I), "✏️", "Modifier mes informations"),
    (re.compile(r"chat|faq|question", re.I), "💬", "Poser une question libre"),
]

_DIGIT_EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]


def _short_label(name: str) -> str:
    """Retourne un libellé court selon le nom du workflow."""
    for pattern, _emoji, short in _PARCOURS_KINDS:
        if pattern.search(name):
            return short
    return name


def _parcours_emoji(name: str) -> str:
    for pattern, emoji, _short in _PARCOURS_KINDS:
        if pattern.search(name):
            return emoji
    return "▶️"


async def _build_parcours_list(db: AsyncSession) -> str:
    """Génère dynamiquement le menu des parcours à partir des workflows ACTIFS.

    Ordre = position. Format :
        1️⃣ ✨ *M'inscrire* (nouveau sociétaire)
        2️⃣ 🔍 *Consulter* mon dossier
        ...
    Un workflow désactivé disparaît du menu (cohérent avec _resolve_dynamic_router).
    """
    result = await db.execute(
        select(Workflow)
        .where(Workflow.active.is_(True))
        .order_by(Workflow.position.asc(), Workflow.created_at.asc())
    )
    workflows = list(result.scalars().all())

    lines = []
    for idx, wf in enumerate(workflows, start=1):
        digit = _DIGIT_EMOJIS[idx - 1] if idx <= 9 else f"{idx}."
        short = _short_label(wf.name)
        emoji = _parcours_emoji(wf.name)
        lines.append(f"{digit} {emoji} *{short}*")
    return "\n".join(lines)


async def _build_employeurs_list(db: AsyncSession, tenant_id: UUID) -> str:
    """Liste numérotée des sociétés actives, format :
        1️⃣ CIE
        2️⃣ SODECI
        ...
    Permet de garder le template `workflow.ask_employeur` synchro avec la BD.
    """
    from app.models import Employeur
    from sqlalchemy import select as _select
    result = await db.execute(
        _select(Employeur)
        .where(Employeur.tenant_id == tenant_id, Employeur.is_active.is_(True))
        .order_by(Employeur.name)
    )
    lines = []
    for idx, emp in enumerate(result.scalars().all(), start=1):
        digit = _DIGIT_EMOJIS[idx - 1] if idx <= 9 else f"{idx}."
        lines.append(f"{digit} {emp.name}")
    return "\n".join(lines)


async def _build_boites_postales_list(db: AsyncSession, tenant_id: UUID) -> str:
    """Construit la liste numérotée des boîtes postales par société, depuis
    la table Employeur. Affichée dans le template `workflow.ask_boite_postale`
    via la variable `{boites_postales_list}`.

    Format :
        1️⃣ CIE · 01 BP 6923 Abidjan 01
        2️⃣ SODECI · 01 BP 1843 Abidjan 01
        …
    Ne retient que les employeurs actifs ayant une boîte postale renseignée.
    """
    from app.models import Employeur
    from sqlalchemy import select as _select
    result = await db.execute(
        _select(Employeur)
        .where(
            Employeur.tenant_id == tenant_id,
            Employeur.is_active.is_(True),
        )
        .order_by(Employeur.name)
    )
    lines = []
    for idx, emp in enumerate(result.scalars().all(), start=1):
        if not emp.boite_postale:
            continue
        digit = _DIGIT_EMOJIS[idx - 1] if idx <= 9 else f"{idx}."
        lines.append(f"{digit} {emp.name} · {emp.boite_postale}")
    return "\n".join(lines)


async def _system_variables(db: AsyncSession, tenant_id: UUID) -> dict[str, str]:
    """Réutilise le helper du message_template_service pour injecter
    assistant_name, support_*, artci_url, dpo_email + un menu `parcours_list`
    dynamique généré à partir des workflows en BD + `boites_postales_list`."""
    try:
        from app.services.message_template_service import _system_variables as fn
        base = await fn(db, tenant_id)
    except Exception as e:
        logger.debug("system_variables indisponibles : %s", e)
        base = {}

    try:
        base["parcours_list"] = await _build_parcours_list(db)
    except Exception as e:
        logger.warning("Construction parcours_list échouée : %s", e)
        base.setdefault("parcours_list", "")

    try:
        base["boites_postales_list"] = await _build_boites_postales_list(db, tenant_id)
    except Exception as e:
        logger.warning("Construction boites_postales_list échouée : %s", e)
        base.setdefault("boites_postales_list", "")

    try:
        base["employeurs_list"] = await _build_employeurs_list(db, tenant_id)
    except Exception as e:
        logger.warning("Construction employeurs_list échouée : %s", e)
        base.setdefault("employeurs_list", "")

    return base


# Footer ajouté automatiquement à chaque QUESTION du workflow pour rappeler à
# l'utilisateur qu'il peut sortir d'une boucle (ex. attente d'une photo qu'il
# n'a pas sous la main). Vu en bas de chaque prompt sauf sur les start-steps
# qui sont déjà des menus.
ESCAPE_HINT = "\n\n_Tapez MENU, STOP, ANNULER ou RECOMMENCER à tout moment pour reprendre depuis le début._"

# Steps de démarrage des différents workflows — ils SONT déjà des menus, pas
# besoin d'ajouter un rappel "tapez MENU".
START_STEP_CODES = {
    "welcome",
    "consult_welcome",
    "update_welcome",
    "chat_welcome",
}


def _should_show_escape_hint(step: WorkflowStep, context: dict) -> bool:
    """True si on doit ajouter le rappel des mots-clés à la fin du message."""
    if step.type != WorkflowStepType.question:
        return False  # pas pour les actions / messages terminaux
    if step.code in START_STEP_CODES:
        return False  # le step de démarrage EST déjà un menu
    if context.get("_simulate"):
        # Mode simulateur : on ajoute quand même pour que l'admin voie
        # l'aspect final tel que le sociétaire le verra.
        return True
    return True


# F-09 — Un nom de variable interne (`{ocr_extracted_name}`, `{support_phone}`,
# etc.) ne doit JAMAIS fuiter vers l'utilisateur. Le regex matche uniquement
# les identifiants Python valides pour ne pas fusiller les accolades légitimes
# (JSON échantillon, code, snippets techniques).
_LEAKED_TOKEN_RE = re.compile(r"\{[a-zA-Z_][a-zA-Z0-9_]{0,63}\}")


def _scrub_leaked_tokens(text: str) -> str:
    """Remplace tout token `{xxx}` résiduel par un tiret discret.

    Défense en profondeur : même si `format_map` a échoué (accolade
    orpheline, JSON dans le template, brace non fermée) et laissé
    passer un identifiant en clair, on l'efface avant renvoi.
    """
    return _LEAKED_TOKEN_RE.sub("—", text)


async def _resolve_field_options(
    db: AsyncSession, tenant_id: UUID, field: dict,
) -> list[dict]:
    """Retourne la liste effective d'options {code, label} pour un champ,
    en résolvant éventuellement `options_ref` contre les référentiels."""
    opts = field.get("options") or []
    if opts:
        return [
            {
                "code": str(o.get("code") or o.get("label") or "").strip(),
                "label": str(o.get("label") or o.get("code") or "").strip(),
            }
            for o in opts
            if (o.get("code") or o.get("label"))
        ]
    ref = field.get("options_ref")
    if not ref:
        return []
    from app.services import reference_list_service
    rl = await reference_list_service.get_list_by_key(db, tenant_id, ref)
    if rl is None:
        return []
    return [
        {
            "code": str(it.get("code") or it.get("label") or "").strip(),
            "label": str(it.get("label") or it.get("code") or "").strip(),
        }
        for it in (rl.items or [])
        if (it.get("code") or it.get("label"))
    ]


async def _build_wa_field_message(
    db: AsyncSession,
    tenant_id: UUID,
    field: dict,
    idx: int,
    total: int,
    intro: str = "",
) -> tuple[str, Optional[dict]]:
    """Construit (texte, ui_hint) pour l'envoi WhatsApp d'un champ unique.

    - ≤3 options  → interactive buttons (ui_hint type `wa_buttons`)
    - 4..10       → interactive list (ui_hint type `wa_list`)
    - >10 / aucune → texte numéroté classique, ui_hint None

    Le texte de repli (`messages=[text]`) reste toujours cohérent si le canal
    décide d'ignorer le ui_hint.
    """
    label = field.get("label") or field.get("key") or "Information"
    optional_suffix = " (facultatif, tapez * pour passer)" if field.get("optional") else ""
    header_prefix = f"Question {idx + 1}/{total}"
    body_core = f"*{header_prefix}*\n{label}{optional_suffix}"
    body_with_intro = f"{intro}{body_core}" if intro else body_core

    options = await _resolve_field_options(db, tenant_id, field)
    if options:
        # Meta : buttons title ≤20, list row title ≤24, body ≤1024.
        if len(options) <= 3:
            buttons = [
                {"id": (o["code"] or o["label"])[:256], "title": (o["label"] or o["code"])[:20]}
                for o in options
            ]
            text_fallback = (
                f"{body_with_intro}\n\n"
                + "\n".join(f"{i + 1}. {o['label']}" for i, o in enumerate(options))
                + "\n\n_Touchez un bouton ou répondez par le numéro._"
            )
            ui = {
                "type": "wa_buttons",
                "body": body_with_intro[:1024],
                "buttons": buttons,
            }
            return text_fallback, ui
        if len(options) <= 10:
            rows = [
                {
                    "id": (o["code"] or o["label"])[:200],
                    "title": (o["label"] or o["code"])[:24],
                }
                for o in options
            ]
            text_fallback = (
                f"{body_with_intro}\n\n"
                + "\n".join(f"{i + 1}. {o['label']}" for i, o in enumerate(options))
                + "\n\n_Touchez « Choisir » ou répondez par le numéro._"
            )
            ui = {
                "type": "wa_list",
                "body": body_with_intro[:1024],
                "button": "Choisir",
                "rows": rows,
            }
            return text_fallback, ui
        # >10 : liste trop longue pour un composant natif, on dégrade en texte.
        block = "\n".join(
            f"{i + 1}. {o['label']}" for i, o in enumerate(options[:20])
        )
        return (
            f"{body_with_intro}\n\n{block}\n\n_Répondez par le numéro ou le nom._",
            None,
        )

    # Pas d'options : hint de format.
    fmt = field.get("format")
    hint_parts = []
    if fmt == "date":
        hint_parts.append("format JJ/MM/AAAA")
    elif fmt == "email":
        hint_parts.append("exemple : nom@domaine.com")
    placeholder = field.get("placeholder") or ""
    if placeholder:
        hint_parts.append(placeholder)
    hint = f"\n\n_({' · '.join(hint_parts)})_" if hint_parts else ""
    return f"{body_with_intro}{hint}", None


async def _normalize_wa_option_reply(
    db: AsyncSession, tenant_id: UUID, field: dict, raw: str,
) -> str:
    """Si la réponse WhatsApp est un `id` de bouton/liste (code d'option) ou
    un numéro dans la liste affichée, retourne le libellé correspondant. Sinon
    renvoie `raw` tel quel. `_validate_single_field` normalise ensuite via
    reference_list_service si un référentiel est en jeu.
    """
    text = (raw or "").strip()
    if not text:
        return text
    options = await _resolve_field_options(db, tenant_id, field)
    if not options:
        return text
    # Match par code exact (id de bouton)
    for o in options:
        if text == o["code"]:
            return o["label"] or o["code"]
    # Match par numéro
    if text.isdigit():
        n = int(text)
        if 1 <= n <= len(options):
            return options[n - 1]["label"] or options[n - 1]["code"]
    return text


async def _validate_single_field(
    db: AsyncSession,
    tenant_id: UUID,
    field: dict,
    value: str,
) -> Optional[str]:
    """Validation d'un seul champ (regex, format, options_ref). Retourne None
    si OK, sinon un message d'erreur lisible."""
    from app.services import reference_list_service
    text = (value or "").strip()
    if not text or text == "*":
        return None  # vide = facultatif ok, * = skip explicite
    # options_ref
    opts_ref = field.get("options_ref")
    if opts_ref:
        rl = await reference_list_service.get_list_by_key(db, tenant_id, opts_ref)
        if rl is not None:
            resolved = reference_list_service.resolve_value(rl, text)
            if resolved is None and not rl.allow_other:
                items_hint = ", ".join(it.get("label", "") for it in (rl.items or [])[:6])
                return f"Valeur « {text} » non reconnue. Attendu : {items_hint}."
            return None
    # regex
    regex = field.get("regex")
    if regex:
        import re as _re
        try:
            if not _re.search(regex, text):
                return field.get("message") or f"Format invalide pour « {field.get('label')} »."
        except Exception:
            pass
    # format email
    if field.get("format") == "email":
        if "@" not in text or "." not in text.split("@")[-1]:
            return "Adresse email invalide."
    return None


async def _build_ui_hint(
    db: AsyncSession,
    tenant_id: UUID,
    step: WorkflowStep,
    ctx: Optional[dict] = None,
) -> Optional[dict]:
    """Construit un hint UI structuré pour un step `question`.

    - `form_fields` → formulaire multi-champs, chaque champ lié ou non à une
      liste de référence (rendue en select).
    - `options_ref` simple → select mono-champ.
    - Rien de pertinent → None (le canal rend juste le texte).
    """
    if step.type != WorkflowStepType.question:
        return None
    rules = step.validation_rules or {}
    form_fields = rules.get("form_fields")
    opts_ref = rules.get("options_ref")

    # Détection « step de signature » : code ou label contient « signature ».
    # Le moteur attend un upload (media_url), on propose au front deux modes :
    # dessin au doigt/souris OU upload fichier.
    code_lo = (step.code or "").lower()
    label_lo = (step.label or "").lower()
    description = (step.meta or {}).get("description") or ""
    if "signature" in code_lo or "signature" in label_lo:
        if not form_fields and not opts_ref:
            return {
                "type": "signature",
                "title": step.label or "Signature",
                "description": description,
            }

    from app.services import reference_list_service

    async def _resolve_options(key: str) -> tuple[list[dict], bool]:
        rl = await reference_list_service.get_list_by_key(db, tenant_id, key)
        if rl is None:
            return [], False
        items = [
            {"code": it.get("code") or it.get("label"), "label": it.get("label") or it.get("code")}
            for it in (rl.items or [])
            if (it.get("code") or it.get("label"))
        ]
        return items, bool(rl.allow_other)

    # Détection multi-select (parcours de mise à jour par exemple).
    multi_opts = rules.get("multi_select")
    multi_ref = rules.get("multi_select_ref")
    if multi_opts or multi_ref:
        if multi_ref:
            m_options, _ = await _resolve_options(multi_ref)
        else:
            m_options = [
                {"code": o.get("code") or o.get("label"), "label": o.get("label") or o.get("code")}
                for o in (multi_opts or [])
                if o.get("code") or o.get("label")
            ]
        if m_options:
            return {
                "type": "multi-select",
                "title": step.label or "",
                "description": description,
                "options": m_options,
                "min": int(rules.get("min_selected", 1)),
                "max": int(rules.get("max_selected", len(m_options))),
                "name": step.code,
            }

    if form_fields and isinstance(form_fields, list):
        out_fields: list[dict] = []
        for f in form_fields:
            name = f.get("name") or f.get("key") or f.get("label") or ""
            label = f.get("label") or name
            ftype = (f.get("type") or "text").lower()
            # Compat : le LLM produit `optional: bool`, le front attend `required`.
            # On accepte les deux et on prend "required" prioritaire si présent.
            if "required" in f:
                required = bool(f.get("required"))
            else:
                required = not bool(f.get("optional", False))
            placeholder = f.get("placeholder") or ""
            field_opts_ref = f.get("options_ref")
            # Pré-remplissage : si ctx contient `current_<name>` ou `<name>`,
            # on l'injecte comme valeur par défaut (parcours de mise à jour).
            default_value = ""
            if ctx:
                key_norm = (f.get("key") or name).lower()
                for k in (f"current_{key_norm}", key_norm, f.get("key") or ""):
                    v = ctx.get(k)
                    if v not in (None, ""):
                        default_value = str(v)
                        break
            options: list[dict] = []
            allow_other = False
            if field_opts_ref:
                options, allow_other = await _resolve_options(field_opts_ref)
                if options and ftype in ("text", ""):
                    ftype = "select"
            out_fields.append({
                "name": name,
                "label": label,
                "type": ftype,
                "required": required,
                "placeholder": placeholder,
                "options": options,
                "allow_other": allow_other,
                "default": default_value,
            })
        return {
            "type": "form",
            "title": step.label or "",
            "description": description,
            "fields": out_fields,
        }

    if opts_ref:
        options, allow_other = await _resolve_options(opts_ref)
        if options:
            return {
                "type": "select",
                "name": step.code,
                "label": step.label or "",
                "description": description,
                "options": options,
                "allow_other": allow_other,
            }
    return None


async def _render_or_fallback(
    db: AsyncSession,
    tenant_id: UUID,
    step: WorkflowStep,
    context: dict,
) -> str:
    """Rend le template du step. Fallback safe sur le label si absent.

    Ajoute automatiquement le rappel des mots-clés universels (MENU / STOP /
    ANNULER / RECOMMENCER) en bas de chaque question — sauf sur les steps de
    démarrage qui sont déjà des menus.

    F-09 — tous les chemins de retour passent par `_scrub_leaked_tokens` :
    aucun `{xxx}` ne peut atteindre l'utilisateur, même quand `format_map`
    lève une exception ou quand le template contient des accolades JSON.
    """
    template_code = step.template_code or workflow_template_service.derive_code(step.code)
    sys_vars = await _system_variables(db, tenant_id)
    variables = {**sys_vars, **{k: str(v) for k, v in context.items() if v is not None}}

    # Pour un step simple lié à un référentiel, on prépare le bloc d'options
    # numérotées à concaténer à la question rendue.
    options_block = ""
    rules = step.validation_rules or {}
    opts_ref = rules.get("options_ref")
    if opts_ref and not rules.get("form_fields"):
        from app.services import reference_list_service
        rl = await reference_list_service.get_list_by_key(db, tenant_id, opts_ref)
        if rl is not None:
            block = reference_list_service.render_options_block(rl)
            if block:
                options_block = "\n\n" + block
                if rl.allow_other:
                    options_block += "\n\nVous pouvez aussi saisir votre propre réponse."

    # 1) Essai sur le service workflow (BD directe, sans registry)
    raw = await workflow_template_service.get_content(db, tenant_id, template_code)
    if raw is not None and raw.strip():
        # Substitution simple {var} dans le contenu
        try:
            body = raw.format_map(_SafeDict(variables))
        except Exception:
            body = raw
        body = _scrub_leaked_tokens(body)
        if options_block:
            body = body + options_block
        if _should_show_escape_hint(step, context):
            body = body + ESCAPE_HINT
        return body

    # 2) Fallback sur le registry standard (pour les codes système)
    if step.template_code:
        try:
            _, content = await render_template(
                db, tenant_id=tenant_id, code=step.template_code, variables=variables,
            )
            if content:
                content = _scrub_leaked_tokens(content)
                if options_block:
                    content = content + options_block
                if _should_show_escape_hint(step, context):
                    content = content + ESCAPE_HINT
                return content
        except Exception as e:
            logger.debug(
                "Template registry '%s' absent pour step %s (%s)",
                step.template_code, step.code, e,
            )

    # 3) Fallback ultime : libellé entre crochets
    fallback = f"[{_scrub_leaked_tokens(step.label or '')}]"
    if options_block:
        fallback += options_block
    if _should_show_escape_hint(step, context):
        fallback += ESCAPE_HINT
    return fallback


class _SafeDict(dict):
    """dict qui renvoie un placeholder discret au lieu de KeyError.

    F-09 — les gabarits internes (ex. `{ocr_extracted_name}` sans OCR
    disponible) ne doivent JAMAIS être affichés en clair à l'utilisateur ;
    le pentest a signalé ça comme fuite de gabarit interne. On renvoie
    donc un tiret pour signaler l'absence sans exposer le nom technique
    de la variable.
    """

    def __missing__(self, key):  # type: ignore[override]
        return "—"


async def _run_action(
    db: AsyncSession,
    step: WorkflowStep,
    context: dict,
    last_input: Optional[str] = None,
) -> ActionResult:
    name = step.action_name or step.code
    handler = get_action(name)
    if handler is None:
        logger.error("Action workflow inconnue : %s (step %s)", name, step.code)
        return ActionResult(
            branch_key=None,
            message=f"[Action backend non implémentée : {name}]",
        )
    try:
        return await handler(db, context, last_input)
    except Exception as e:
        logger.exception("Action %s a échoué : %s", name, e)
        return ActionResult(branch_key="error", message=f"Erreur action {name} : {e}")


def _resolve_next_code(step: WorkflowStep, branch_key: Optional[str]) -> Optional[str]:
    """Choisit l'étape suivante selon branch_key (priorité) puis next_step_code."""
    if branch_key and step.branches and branch_key in step.branches:
        return step.branches[branch_key]
    return step.next_step_code


def _kind_from_name(name: str) -> str:
    """Détecte le « kind » d'un workflow à partir de son nom (pour mapper
    vers le handoff correspondant, ex. workflow consultation → handoff_consultation)."""
    n = (name or "").lower()
    if "consultation" in n:
        return "consultation"
    if "mise" in n or "modification" in n or "update" in n:
        return "modification"
    if "chat" in n or "faq" in n or "question" in n:
        return "chat"
    if "inscription" in n or "enrôl" in n or "enrol" in n:
        return "inscription"
    return ""


async def _resolve_dynamic_router(
    db: AsyncSession,
    *,
    current_workflow_id: UUID,
    user_input: Optional[str],
    steps_index: dict[str, WorkflowStep],
) -> Optional[str]:
    """Pour les steps marqués `meta.dynamic_router = "by_workflow_position"` :
    résout le step suivant en fonction de la position du workflow choisi.

    - L'utilisateur tape un chiffre (1, 2, 3…)
    - On récupère la liste des workflows ordonnés par created_at
    - Le N-ième workflow détermine la destination :
      * Si c'est le workflow courant → next_step_code ou branche `self`
      * Sinon → cherche un step `handoff_<kind>` dans le workflow courant

    Retourne le code de step à utiliser, ou None si pas de match.
    """
    if not user_input:
        return None
    try:
        idx = int(user_input.strip())
    except ValueError:
        return None
    if idx < 1:
        return None

    # Ne considère QUE les workflows actifs : un handoff vers un workflow
    # désactivé mène à un cul-de-sac. Le compte doit rester cohérent avec
    # ce que l'utilisateur voit dans le menu.
    result = await db.execute(
        select(Workflow)
        .where(Workflow.active.is_(True))
        .order_by(Workflow.position.asc(), Workflow.created_at.asc())
    )
    workflows = list(result.scalars().all())
    if idx > len(workflows):
        return None

    target = workflows[idx - 1]
    # Cas 1 : la cible EST le workflow courant → continuer dans ce workflow
    if target.id == current_workflow_id:
        return "__self__"

    # Cas 2 : workflow différent → on veut TRANSITER vers le workflow cible.
    # On retourne son start_step_code sous forme `__switch__:code` que le
    # dispatcher détectera et utilisera pour changer de workflow.
    if target.start_step_code:
        return f"__switch__:{target.start_step_code}"
    return None


# ----------------------------------------------------------------------
# ENTRÉE PRINCIPALE
# ----------------------------------------------------------------------
async def execute(
    db: AsyncSession,
    *,
    workflow: Workflow,
    tenant_id: UUID,
    current_step_code: Optional[str],
    user_input: Optional[str],
    context: dict,
) -> ExecuteResult:
    """Avance le workflow d'un tour.

    Si `current_step_code` est None : démarre au `workflow.start_step_code`.
    Sinon : consomme `user_input` comme réponse à la question courante,
    valide, puis enchaîne les transitions automatiques (message/action/
    decision) jusqu'à la prochaine question.

    Le caller doit persister `result.next_step_code` et `result.context`.
    """
    steps_by_code = _build_step_index(workflow)
    ctx = dict(context or {})
    # Injecte tenant_id dans le contexte pour que les actions puissent
    # appeler les services tenant-scoped (settings, email, OTP, etc.)
    ctx["_tenant_id"] = str(tenant_id)
    out_messages: list[str] = []

    is_whatsapp = ctx.get("_channel") == "whatsapp"

    # ---- Phase 1 : si on est sur une question, consommer la réponse
    if current_step_code:
        current = steps_by_code.get(current_step_code)
        if current is None:
            return ExecuteResult(
                error=f"Étape '{current_step_code}' inexistante dans le workflow.",
                context=ctx,
            )

        # WhatsApp : si on est sur un step form_fields en cours de split,
        # on gère les champs UN PAR UN. ctx["_wa_form_step"] / ctx["_wa_form_idx"].
        wa_form_finished = False
        if is_whatsapp and current.type == WorkflowStepType.question:
            rules = current.validation_rules or {}
            form_fields = rules.get("form_fields")
            if form_fields and isinstance(form_fields, list):
                wa_state = ctx.get("_wa_form_step")
                wa_idx = int(ctx.get("_wa_form_idx") or 0)
                if wa_state == current.code and wa_idx < len(form_fields):
                    current_field = form_fields[wa_idx]
                    raw_input = (user_input or "").strip()
                    is_optional = bool(current_field.get("optional"))
                    if not raw_input and not is_optional:
                        reprompt_text, reprompt_ui = await _build_wa_field_message(
                            db, tenant_id, current_field, wa_idx, len(form_fields),
                            intro=f"« {current_field.get('label')} » : valeur attendue.\n\n",
                        )
                        return ExecuteResult(
                            messages=[reprompt_text],
                            next_step_code=current.code,
                            ui=reprompt_ui,
                            context=ctx,
                        )
                    # Normalise la réponse si c'est un id de bouton WhatsApp (code
                    # d'option) ou un numéro — on stocke la version propre.
                    normalized = await _normalize_wa_option_reply(
                        db, tenant_id, current_field, raw_input,
                    )
                    field_err = await _validate_single_field(db, tenant_id, current_field, normalized)
                    if field_err:
                        err_text, err_ui = await _build_wa_field_message(
                            db, tenant_id, current_field, wa_idx, len(form_fields),
                            intro=f"{field_err}\n\n",
                        )
                        return ExecuteResult(
                            messages=[err_text],
                            next_step_code=current.code,
                            ui=err_ui,
                            context=ctx,
                        )
                    field_key = current_field.get("key") or current_field.get("name") or f"field_{wa_idx}"
                    if normalized:
                        ctx[field_key] = normalized
                    wa_idx += 1
                    if wa_idx < len(form_fields):
                        ctx["_wa_form_idx"] = wa_idx
                        next_text, next_ui = await _build_wa_field_message(
                            db, tenant_id, form_fields[wa_idx], wa_idx, len(form_fields),
                        )
                        return ExecuteResult(
                            messages=[next_text],
                            next_step_code=current.code,
                            ui=next_ui,
                            context=ctx,
                        )
                    # Form terminé : nettoie l'état, laisse continuer normalement
                    ctx.pop("_wa_form_step", None)
                    ctx.pop("_wa_form_idx", None)
                    wa_form_finished = True

        if current.type == WorkflowStepType.question and not wa_form_finished:
            error = await _validate_question_input(
                db, tenant_id, current, user_input or "", ctx
            )
            if error:
                # Reste sur la même question, mais ajoute le message d'erreur
                # devant le re-prompt du template
                reprompt = await _render_or_fallback(db, tenant_id, current, ctx)
                ui_hint = await _build_ui_hint(db, tenant_id, current, ctx)
                return ExecuteResult(
                    messages=[f"{error}\n\n{reprompt}"],
                    next_step_code=current.code,
                    ui=ui_hint,
                    context=ctx,
                )
            # Stocke la réponse dans le contexte sous une clé déduite du code
            ctx[current.code] = (user_input or "").strip()
            ctx[f"{current.code}_input"] = (user_input or "").strip()

            # Si l'utilisateur a envoyé un média (upload / signature canvas), on
            # archive l'URL sous une clé spécifique à l'étape pour que les
            # actions suivantes (create_real_dossier, OCR…) puissent la retrouver
            # même après plusieurs uploads successifs (sinon `last_media_url`
            # est écrasé à chaque tour).
            media_url = ctx.get("last_media_url")
            if media_url and ctx.get("last_has_media"):
                ctx[f"{current.code}_media_url"] = media_url
                # Alias courants attendus par les actions existantes.
                code_lo = current.code.lower()
                if "recto" in code_lo and not ctx.get("recto_media_url"):
                    ctx["recto_media_url"] = media_url
                elif "verso" in code_lo and not ctx.get("verso_media_url"):
                    ctx["verso_media_url"] = media_url
                elif "signature" in code_lo and not ctx.get("signature_media_url"):
                    ctx["signature_media_url"] = media_url

            # Mode « form batch » : extrait chaque champ du formulaire dans
            # le contexte sous sa propre clé pour que les actions suivantes
            # (build_recap, OCR cross-check, sauvegarde dossier) y accèdent.
            form_fields = (current.validation_rules or {}).get("form_fields")
            if form_fields and isinstance(form_fields, list):
                parsed, _ = _parse_form_response(user_input or "", form_fields)
                for key, value in parsed.items():
                    ctx[key] = value

            # Résolveur dynamique : si le step est marqué `meta.dynamic_router =
            # "by_workflow_position"`, on résout vers le bon handoff selon le
            # numéro tapé par l'utilisateur (mappé à la liste réelle des
            # workflows en BD).
            next_code = None
            if (current.meta or {}).get("dynamic_router") == "by_workflow_position":
                resolved = await _resolve_dynamic_router(
                    db,
                    current_workflow_id=workflow.id,
                    user_input=user_input,
                    steps_index=steps_by_code,
                )
                if resolved == "__self__":
                    # L'utilisateur a tapé le numéro du workflow courant — on
                    # suit le chemin nominal (branche "self" si définie, sinon
                    # next_step_code).
                    next_code = current.branches.get("self") or current.next_step_code
                elif resolved and resolved.startswith("__switch__:"):
                    # Basculement inter-parcours : le dispatcher va charger le
                    # workflow contenant ce step et relancer execute() dessus.
                    return ExecuteResult(
                        messages=out_messages,
                        next_step_code=None,
                        is_terminal=False,
                        context=ctx,
                        switch_to_step=resolved.split(":", 1)[1],
                    )
                elif resolved:
                    next_code = resolved

            # Fallback : routage selon l'input utilisateur
            if next_code is None:
                normalised = (user_input or "").strip().lower()
                branch = None
                branches = current.branches or {}
                # Priorité 1 : "on_refused" pour "2"/"non" (cas certification ARTCI)
                if normalised in {"non", "no", "refus", "refuser", "2"} and "on_refused" in branches:
                    branch = "on_refused"
                # Priorité 2 : "on_correction" pour "2"/"corriger" (cas validation OCR)
                elif normalised in {"corriger", "correction", "2"} and "on_correction" in branches:
                    branch = "on_correction"
                # Priorité 3 : l'input matche directement une clé de branche
                # (ex. menu numérique : "1" → branches["1"], "2" → branches["2"]…)
                elif normalised in branches:
                    branch = normalised
                next_code = _resolve_next_code(current, branch)
        else:
            # current n'est pas une question — on enchaîne depuis lui (cas exotique)
            # OU on vient de terminer un form WhatsApp → on avance au next_step_code
            if wa_form_finished:
                next_code = current.next_step_code
            else:
                next_code = current.code
    else:
        # Démarrage du parcours
        next_code = workflow.start_step_code
        if not next_code:
            return ExecuteResult(
                error="Workflow sans étape de démarrage configurée.", context=ctx,
            )

    # ---- Phase 2 : enchaîne les transitions automatiques jusqu'à une question
    steps_run = 0
    while next_code is not None and steps_run < MAX_INTERNAL_STEPS:
        steps_run += 1
        step = steps_by_code.get(next_code)
        if step is None:
            return ExecuteResult(
                error=f"Étape '{next_code}' référencée mais inexistante.",
                messages=out_messages,
                next_step_code=None,
                is_terminal=True,
                context=ctx,
            )

        # Skip conditionnel : si `step.meta.show_when` = {"key": "...", "in": "..."}
        # et que ctx[key] ne contient pas la valeur, on saute ce step vers son
        # next_step_code. Utilisé par les parcours de mise à jour où chaque
        # domaine (coordonnées, employeur…) n'apparaît que si coché au multi-select.
        gate = (step.meta or {}).get("show_when")
        if isinstance(gate, dict):
            gate_key = gate.get("key")
            gate_val = gate.get("in") or gate.get("equals")
            if gate_key and gate_val is not None:
                ctx_val = ctx.get(gate_key)
                matches = False
                if isinstance(ctx_val, (list, tuple)):
                    matches = gate_val in ctx_val
                elif isinstance(ctx_val, str):
                    matches = gate_val == ctx_val or gate_val in [p.strip() for p in ctx_val.split(",")]
                if not matches:
                    logger.info(
                        "Step %s skippé (show_when %s=%s, ctx=%r)",
                        step.code, gate_key, gate_val, ctx_val,
                    )
                    next_code = step.next_step_code
                    continue

        if step.type == WorkflowStepType.message:
            text = await _render_or_fallback(db, tenant_id, step, ctx)
            out_messages.append(text)
            # Basculement inter-workflow : si `meta.switch_to_step = "code"`,
            # le dispatcher change de workflow et démarre sur ce code.
            switch_target = (step.meta or {}).get("switch_to_step")
            if switch_target:
                return ExecuteResult(
                    messages=out_messages,
                    next_step_code=None,
                    is_terminal=False,
                    context=ctx,
                    switch_to_step=switch_target,
                )
            next_code = step.next_step_code
            if next_code is None:
                # Message terminal — fin du parcours
                return ExecuteResult(
                    messages=out_messages,
                    next_step_code=None,
                    is_terminal=True,
                    context=ctx,
                )
            continue

        if step.type == WorkflowStepType.question:
            # WhatsApp + form_fields → initialise le split et demande le 1er champ
            if is_whatsapp:
                rules = step.validation_rules or {}
                form_fields = rules.get("form_fields")
                if form_fields and isinstance(form_fields, list) and len(form_fields) > 0:
                    intro = ""
                    desc = (step.meta or {}).get("description") or ""
                    if desc:
                        intro = f"*{step.label}*\n{desc}\n\n"
                    elif step.label:
                        intro = f"*{step.label}*\n\n"
                    ctx["_wa_form_step"] = step.code
                    ctx["_wa_form_idx"] = 0
                    first_text, first_ui = await _build_wa_field_message(
                        db, tenant_id, form_fields[0], 0, len(form_fields),
                        intro=intro,
                    )
                    # Si un ui interactif est émis, on garde seulement ce message
                    # (le body embarque déjà l'intro) pour éviter deux bulles.
                    if first_ui is not None:
                        return ExecuteResult(
                            messages=out_messages + [first_text],
                            next_step_code=step.code,
                            ui=first_ui,
                            context=ctx,
                        )
                    out_messages.append(first_text)
                    return ExecuteResult(
                        messages=out_messages,
                        next_step_code=step.code,
                        context=ctx,
                    )

            text = await _render_or_fallback(db, tenant_id, step, ctx)
            out_messages.append(text)
            ui_hint = await _build_ui_hint(db, tenant_id, step, ctx)
            return ExecuteResult(
                messages=out_messages,
                next_step_code=step.code,
                ui=ui_hint,
                context=ctx,
            )

        if step.type == WorkflowStepType.action:
            last_in = ctx.get(f"{current_step_code}_input") if current_step_code else None
            result = await _run_action(db, step, ctx, last_input=last_in)
            if result.extra_context:
                ctx.update(result.extra_context)
            if result.message:
                out_messages.append(result.message)
            next_code = _resolve_next_code(step, result.branch_key)
            if next_code is None:
                return ExecuteResult(
                    messages=out_messages,
                    next_step_code=None,
                    is_terminal=True,
                    context=ctx,
                )
            continue

        if step.type == WorkflowStepType.decision:
            # Pour la Phase 3 actuelle on traite decision comme un alias d'action
            # qui ne fait rien et suit next_step_code. À étendre avec un évaluateur
            # de conditions (jsonlogic, etc.) en Phase 3.5.
            next_code = _resolve_next_code(step, None)
            continue

        # Type inconnu : fin défensive
        return ExecuteResult(
            error=f"Type d'étape inconnu : {step.type}",
            messages=out_messages,
            next_step_code=None,
            is_terminal=True,
            context=ctx,
        )

    # Garde-fou anti-boucle
    return ExecuteResult(
        error="Boucle d'exécution interrompue (trop d'étapes automatiques enchaînées).",
        messages=out_messages,
        next_step_code=next_code,
        context=ctx,
    )
