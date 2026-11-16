"""Service CRUD + seed des référentiels fermés.

Les référentiels alimentent :
- Le system prompt de l'extraction LLM (`parcours_llm.py`) → le modèle sait
  quelles listes existent et doit émettre `options_ref: "<key>"` quand un
  champ y correspond.
- Le post-processeur fuzzy-match → sécurise la détection si le LLM a oublié.
- Le `workflow_executor` → affiche les options numérotées, valide l'input
  utilisateur contre codes/labels/synonymes.

Les listes `is_system=True` sont seedées automatiquement au boot si absentes.
"""
from __future__ import annotations

import logging
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reference_list import ReferenceList

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Seed des référentiels système
# ---------------------------------------------------------------------------

SYSTEM_LISTS: List[Dict[str, Any]] = [
    {
        "key": "civilites",
        "label": "Civilités",
        "aliases": ["civilite", "titre", "sexe", "genre"],
        "description": "Civilité du sociétaire (titre de courtoisie).",
        "allow_other": False,
        "items": [
            {"code": "mlle", "label": "Mlle", "synonyms": ["mademoiselle"]},
            {"code": "mme", "label": "Mme", "synonyms": ["madame"]},
            {"code": "m", "label": "M.", "synonyms": ["monsieur", "mr", "mr."]},
        ],
    },
    {
        "key": "situations_matrimoniales",
        "label": "Situations matrimoniales",
        "aliases": [
            "situation matrimoniale",
            "statut marital",
            "etat civil",
            "etat matrimonial",
        ],
        "description": "Situation familiale déclarée.",
        "allow_other": False,
        "items": [
            {"code": "celibataire", "label": "Célibataire", "synonyms": ["single"]},
            {"code": "marie", "label": "Marié(e)", "synonyms": ["marie", "mariee"]},
            {"code": "divorce", "label": "Divorcé(e)", "synonyms": ["divorce", "divorcee"]},
            {"code": "veuf", "label": "Veuf(ve)", "synonyms": ["veuf", "veuve"]},
            {"code": "union_libre", "label": "Union libre", "synonyms": ["concubinage"]},
        ],
    },
    {
        "key": "types_piece_identite",
        "label": "Types de pièce d'identité",
        "aliases": [
            "type de piece",
            "type de piece d'identite",
            "piece d'identite",
            "document d'identite",
        ],
        "description": "Nature du justificatif d'identité fourni.",
        "allow_other": False,
        "items": [
            {"code": "cni", "label": "CNI", "synonyms": ["carte d'identite", "carte nationale"]},
            {"code": "passeport", "label": "Passeport", "synonyms": []},
            {"code": "permis", "label": "Permis de conduire", "synonyms": ["permis conduire"]},
            {"code": "attestation", "label": "Attestation d'identité", "synonyms": ["attestation"]},
        ],
    },
    {
        "key": "categories_professionnelles",
        "label": "Catégories professionnelles",
        "aliases": ["categorie", "categorie professionnelle", "grade", "echelon"],
        "description": "Catégorie du personnel du groupe ERANOVE.",
        "allow_other": True,
        "items": [
            {"code": "m1", "label": "Catégorie M1", "synonyms": ["m1"]},
            {"code": "m2", "label": "Catégorie M2", "synonyms": ["m2"]},
            {"code": "m3", "label": "Catégorie M3", "synonyms": ["m3"]},
            {"code": "m4", "label": "Catégorie M4", "synonyms": ["m4"]},
            {"code": "m5", "label": "Catégorie M5", "synonyms": ["m5"]},
        ],
    },
    {
        "key": "employeurs",
        "label": "Employeurs du groupe",
        "aliases": ["employeur", "societe", "entreprise", "filiale"],
        "description": "Sociétés du groupe ERANOVE éligibles à MA2E.",
        "allow_other": False,
        # Ordre d'AJOUT (le 1er = le plus ancien) ; la liste est affichée du plus récent au plus ancien
        # une fois datée par ensure_employeurs_chronology.
        "items": [
            {"code": "gs2e", "label": "GS2E", "synonyms": []},
            {"code": "cie", "label": "CIE", "synonyms": ["compagnie ivoirienne d'electricite"]},
            {"code": "sodeci", "label": "SODECI", "synonyms": []},
            {"code": "eranove", "label": "ERANOVE", "synonyms": []},
            {"code": "smb", "label": "SMB", "synonyms": []},
            {"code": "sde", "label": "SDE", "synonyms": []},
            {"code": "ciprel", "label": "CIPREL", "synonyms": []},
        ],
    },
    {
        "key": "reponses_oui_non",
        "label": "Oui / Non",
        "aliases": ["accord", "confirmation", "consentement"],
        "description": "Réponse binaire — utilisée pour consentement ARTCI, confirmation finale.",
        "allow_other": False,
        "items": [
            {"code": "oui", "label": "OUI", "synonyms": ["yes", "o", "ok", "d'accord", "accepte"]},
            {"code": "non", "label": "NON", "synonyms": ["no", "n", "refuse", "pas d'accord"]},
        ],
    },
]


async def seed_system_lists(db: AsyncSession, tenant_id: UUID) -> int:
    """Insère les référentiels système manquants pour un tenant.

    Idempotent : ne touche pas aux listes existantes (`is_system=True` ou non).
    Retourne le nombre de listes créées.
    """
    created = 0
    for spec in SYSTEM_LISTS:
        existing = (
            await db.execute(
                select(ReferenceList).where(
                    ReferenceList.tenant_id == tenant_id,
                    ReferenceList.key == spec["key"],
                )
            )
        ).scalar_one_or_none()
        if existing:
            continue
        rl = ReferenceList(
            tenant_id=tenant_id,
            key=spec["key"],
            label=spec["label"],
            aliases=list(spec.get("aliases") or []),
            items=list(spec.get("items") or []),
            is_system=True,
            allow_other=bool(spec.get("allow_other")),
            description=spec.get("description"),
        )
        db.add(rl)
        created += 1
    if created:
        await db.commit()
        log.info("Référentiels système seedés pour tenant %s : %d listes.", tenant_id, created)
    return created


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


async def list_lists(db: AsyncSession, tenant_id: UUID) -> List[ReferenceList]:
    result = await db.execute(
        select(ReferenceList)
        .where(ReferenceList.tenant_id == tenant_id)
        .order_by(ReferenceList.is_system.desc(), ReferenceList.label.asc())
    )
    return list(result.scalars().all())


async def get_list(db: AsyncSession, tenant_id: UUID, list_id: UUID) -> ReferenceList:
    rl = (
        await db.execute(
            select(ReferenceList).where(
                ReferenceList.id == list_id,
                ReferenceList.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if not rl:
        raise HTTPException(404, "Référentiel introuvable.")
    return rl


async def get_list_by_key(
    db: AsyncSession, tenant_id: UUID, key: str
) -> Optional[ReferenceList]:
    return (
        await db.execute(
            select(ReferenceList).where(
                ReferenceList.tenant_id == tenant_id,
                ReferenceList.key == key,
            )
        )
    ).scalar_one_or_none()


async def create_list(
    db: AsyncSession,
    tenant_id: UUID,
    *,
    key: str,
    label: str,
    items: List[Dict[str, Any]],
    aliases: Optional[List[str]] = None,
    description: Optional[str] = None,
    allow_other: bool = False,
) -> ReferenceList:
    key = _slug(key)
    if not key:
        raise HTTPException(400, "Clé technique vide.")
    if await get_list_by_key(db, tenant_id, key):
        raise HTTPException(409, f"La clé '{key}' est déjà utilisée.")
    rl = ReferenceList(
        tenant_id=tenant_id,
        key=key,
        label=label.strip(),
        aliases=list(aliases or []),
        items=_normalize_items(items),
        is_system=False,
        allow_other=allow_other,
        description=(description or "").strip() or None,
    )
    db.add(rl)
    await db.commit()
    await db.refresh(rl)
    return rl


async def update_list(
    db: AsyncSession,
    tenant_id: UUID,
    list_id: UUID,
    *,
    label: Optional[str] = None,
    items: Optional[List[Dict[str, Any]]] = None,
    aliases: Optional[List[str]] = None,
    description: Optional[str] = None,
    allow_other: Optional[bool] = None,
    matricule_rule: Optional[Dict[str, Optional[int]]] = None,
    actor_id: Optional[UUID] = None,
) -> ReferenceList:
    rl = await get_list(db, tenant_id, list_id)
    if matricule_rule is not None:
        await _apply_matricule_rule(db, tenant_id, rl, matricule_rule, actor_id)
    if label is not None:
        rl.label = label.strip()
    if items is not None:
        new_items = _normalize_items(items)
        if rl.key == EMPLOYEURS_KEY:
            new_items = sort_by_added_at(stamp_new_items(new_items))
            await sync_employeurs(db, tenant_id, list(rl.items or []), new_items)
        rl.items = new_items
    if aliases is not None:
        rl.aliases = list(aliases)
    if description is not None:
        rl.description = description.strip() or None
    if allow_other is not None:
        rl.allow_other = bool(allow_other)
    await db.commit()
    await db.refresh(rl)
    return rl


async def delete_list(db: AsyncSession, tenant_id: UUID, list_id: UUID) -> None:
    rl = await get_list(db, tenant_id, list_id)
    if rl.is_system:
        raise HTTPException(
            400, "Les référentiels système ne peuvent pas être supprimés (seulement édités)."
        )
    await db.delete(rl)
    await db.commit()


# ---------------------------------------------------------------------------
# Helpers normalisation + fuzzy match
# ---------------------------------------------------------------------------


def _slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s


def _normalize_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    seen_codes: set[str] = set()
    for raw in items or []:
        label = str(raw.get("label") or "").strip()
        if not label:
            continue
        code = _slug(str(raw.get("code") or label))
        if not code or code in seen_codes:
            # suffixer en cas de doublon de code
            i = 2
            base = code or "item"
            while f"{base}_{i}" in seen_codes:
                i += 1
            code = f"{base}_{i}"
        seen_codes.add(code)
        syns_raw = raw.get("synonyms") or []
        if isinstance(syns_raw, str):
            syns_raw = [s.strip() for s in syns_raw.split(",")]
        synonyms = [str(s).strip() for s in syns_raw if str(s).strip()]
        item = {"code": code, "label": label, "synonyms": synonyms}
        if raw.get("added_at"):  # date d'ajout (liste « Employeurs du groupe ») : conservée telle quelle
            item["added_at"] = str(raw["added_at"])
        out.append(item)
    return out


# ---------------------------------------------------------------------------
# Liste « Employeurs du groupe » : ordre chronologique + lien avec la table `employeurs`
# ---------------------------------------------------------------------------

EMPLOYEURS_KEY = "employeurs"


async def _apply_matricule_rule(
    db: AsyncSession, tenant_id: UUID, rl: ReferenceList,
    changes: Dict[str, Optional[int]], actor_id: Optional[UUID],
) -> None:
    """Longueur des matricules commune au groupe (min / max), portée par la liste « Employeurs du groupe »."""
    from app.services.matricule_format import check_rule

    if rl.key != EMPLOYEURS_KEY:
        raise HTTPException(400, "La longueur des matricules ne se règle que sur la liste « Employeurs du groupe ».")
    cfg = dict(rl.config or {})
    new = {k: changes.get(k, cfg.get(k)) for k in ("matricule_min_len", "matricule_max_len")}
    try:
        check_rule(new["matricule_min_len"], new["matricule_max_len"])
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    before = {k: cfg.get(k) for k in new}
    if before == new:
        return
    for k, v in new.items():
        if v is None:
            cfg.pop(k, None)
        else:
            cfg[k] = v
    rl.config = cfg
    from app.models import AuditAction
    from app.services import audit_service
    await audit_service.log(
        db, tenant_id=tenant_id, action=AuditAction.setting_changed,
        resource_type="reference_list", resource_id=str(rl.id),
        actor_type="user" if actor_id else "system", actor_id=str(actor_id) if actor_id else None,
        details={"action": "longueur_matricule", "from": before, "to": new},
    )


def stamp_new_items(items: List[Dict[str, Any]], now: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """Donne une date d'ajout aux items qui n'en ont pas (items ajoutés lors de cet enregistrement)."""
    stamp = (now or datetime.now(timezone.utc)).isoformat()
    return [it if it.get("added_at") else {**it, "added_at": stamp} for it in items]


def sort_by_added_at(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Plus récent en haut, plus ancien en bas. Tri stable : à date égale, l'ordre saisi est gardé."""
    return sorted(items, key=lambda it: str(it.get("added_at") or ""), reverse=True)


async def sync_employeurs(
    db: AsyncSession, tenant_id: UUID, old_items: List[Dict[str, Any]], new_items: List[Dict[str, Any]]
) -> None:
    """Chaque employeur de la liste existe dans la table `employeurs` (qui porte sa règle de matricule) :
    - ajouté à la liste  -> créé (ou réactivé) dans la table ;
    - retiré de la liste -> DÉSACTIVÉ (jamais supprimé : des dossiers peuvent y être rattachés).
    Les employeurs de la table absents de la liste avant ce changement ne sont pas touchés."""
    from sqlalchemy import func

    from app.models import Employeur

    rows = {
        e.code.upper(): e
        for e in (await db.execute(select(Employeur).where(Employeur.tenant_id == tenant_id))).scalars()
    }
    names = {e.name.strip().lower() for e in rows.values()}
    new_codes = set()
    for it in new_items:
        code = str(it["code"]).upper()[:32]
        new_codes.add(code)
        emp = rows.get(code)
        if emp is None:
            name = it["label"][:255]
            if name.strip().lower() in names:  # nom déjà pris par un autre code
                name = f"{name} ({code})"[:255]
            emp = Employeur(tenant_id=tenant_id, code=code, name=name, is_active=True)
            db.add(emp)
            rows[code] = emp
            names.add(name.strip().lower())
        elif not emp.is_active:
            emp.is_active = True
    for it in old_items:
        code = str(it.get("code") or "").upper()[:32]
        if code and code not in new_codes and code in rows:
            rows[code].is_active = False
    await db.flush()


async def ensure_employeurs_chronology(db: AsyncSession, tenant_id: UUID) -> bool:
    """Migration unique : date d'ajout pour les items existants (l'ordre enregistré = ordre d'ajout,
    le 1er étant le plus ancien), ajout de CIPREL, tri du plus récent au plus ancien.
    Ne fait rien dès que tous les items ont une date. Retourne True si la liste a été modifiée."""
    rl = await get_list_by_key(db, tenant_id, EMPLOYEURS_KEY)
    if rl is None:
        return False
    items = list(rl.items or [])
    if items and all(it.get("added_at") for it in items):
        return False
    base = rl.created_at or datetime.now(timezone.utc)
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    dated = [
        it if it.get("added_at") else {**it, "added_at": (base + timedelta(seconds=i)).isoformat()}
        for i, it in enumerate(items)
    ]
    if not any(str(it.get("code", "")).lower() == "ciprel" for it in dated):
        dated.append({"code": "ciprel", "label": "CIPREL", "synonyms": [],
                      "added_at": datetime.now(timezone.utc).isoformat()})
    dated = sort_by_added_at(dated)
    await sync_employeurs(db, tenant_id, items, dated)
    rl.items = dated
    await db.commit()
    return True


def _norm_text(s: str) -> str:
    s = unicodedata.normalize("NFKD", (s or "").lower()).encode("ascii", "ignore").decode()
    s = re.sub(r"\s*\([^)]*\)", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return s


def resolve_value(rl: ReferenceList, user_input: str) -> Optional[Dict[str, str]]:
    """Résout l'input utilisateur contre les items du référentiel.

    Accepte :
    - Un numéro (1-based) → l'item correspondant
    - Le code exact (ex: "m1")
    - Le label (ex: "Catégorie M1")
    - Un synonyme (ex: "monsieur" → "M.")

    Retourne `{"code": ..., "label": ...}` ou None si rien ne matche.
    """
    raw = (user_input or "").strip()
    if not raw:
        return None
    items = list(rl.items or [])
    # 1. Numéro 1-based
    if raw.isdigit():
        idx = int(raw) - 1
        if 0 <= idx < len(items):
            it = items[idx]
            return {"code": it["code"], "label": it["label"]}
    needle = _norm_text(raw)
    # 2. Match exact code / label / synonyme
    for it in items:
        if _norm_text(it.get("code", "")) == needle:
            return {"code": it["code"], "label": it["label"]}
        if _norm_text(it.get("label", "")) == needle:
            return {"code": it["code"], "label": it["label"]}
        for syn in it.get("synonyms") or []:
            if _norm_text(syn) == needle:
                return {"code": it["code"], "label": it["label"]}
    # 3. Match fuzzy sur label si assez proche
    best: Optional[Dict[str, str]] = None
    best_ratio = 0.0
    for it in items:
        for candidate in [it.get("label", "")] + list(it.get("synonyms") or []):
            ratio = SequenceMatcher(None, needle, _norm_text(candidate)).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best = {"code": it["code"], "label": it["label"]}
    if best and best_ratio >= 0.82:
        return best
    return None


def match_list_for_label(lists: List[ReferenceList], field_label: str) -> Optional[str]:
    """Trouve le `key` de la liste la plus proche d'un libellé de champ.

    Utilisé par le post-processeur de `parcours_llm.py` pour attacher
    automatiquement un `options_ref` quand le LLM a oublié.
    Retourne `None` si rien ne matche assez.
    """
    needle = _norm_text(field_label)
    if len(needle) < 3:
        return None
    best_key: Optional[str] = None
    best_ratio = 0.0
    for rl in lists:
        candidates = [rl.label] + list(rl.aliases or [])
        for cand in candidates:
            ratio = SequenceMatcher(None, needle, _norm_text(cand)).ratio()
            # Boost : si la candidate est contenue dans le label de champ
            cand_norm = _norm_text(cand)
            if cand_norm and cand_norm in needle:
                ratio = max(ratio, 0.9)
            if ratio > best_ratio:
                best_ratio = ratio
                best_key = rl.key
    if best_key and best_ratio >= 0.78:
        return best_key
    return None


def render_options_block(rl: ReferenceList) -> str:
    """Rend la liste numérotée pour inclusion dans la question au chatbot."""
    lines: List[str] = []
    for idx, it in enumerate(rl.items or [], start=1):
        lines.append(f"{idx}. {it['label']}")
    return "\n".join(lines)
