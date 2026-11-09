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
        "items": [
            {"code": "gs2e", "label": "GS2E", "synonyms": []},
            {"code": "cie", "label": "CIE", "synonyms": ["compagnie ivoirienne d'electricite"]},
            {"code": "sodeci", "label": "SODECI", "synonyms": []},
            {"code": "eranove", "label": "ERANOVE", "synonyms": []},
            {"code": "smb", "label": "SMB", "synonyms": []},
            {"code": "sde", "label": "SDE", "synonyms": []},
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
) -> ReferenceList:
    rl = await get_list(db, tenant_id, list_id)
    if label is not None:
        rl.label = label.strip()
    if items is not None:
        rl.items = _normalize_items(items)
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
        out.append({"code": code, "label": label, "synonyms": synonyms})
    return out


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
