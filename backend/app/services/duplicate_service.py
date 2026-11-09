"""Service de détection des doublons d'identification (US-36 anti-fraude).

Deux types de doublons :

- **Strict** : matricule OU numéro CNI déjà associé à un dossier en cours ou
  validé. Blocage IMMÉDIAT — seul un administrateur peut le lever.

- **Souple** : combinaison nom + prénoms + date de naissance déjà connue.
  Alerte agent — visible dans l'onglet « Doublons à arbitrer ».

Conformité backlog US-36 :
- Doublon strict → blocage automatique au moment de la soumission
- Doublon souple → marque le dossier pour arbitrage
- Audit des deux cas pour traçabilité ARTCI
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Dossier, DossierStatus, PieceIdentite

logger = logging.getLogger(__name__)


@dataclass
class DuplicateMatch:
    dossier_id: str
    dossier_number: str
    status: str
    matched_on: str  # 'matricule' | 'numero_cni' | 'identity_combo'


@dataclass
class DuplicateCheckResult:
    strict_matches: list[DuplicateMatch] = field(default_factory=list)
    soft_matches: list[DuplicateMatch] = field(default_factory=list)

    @property
    def has_strict(self) -> bool:
        return len(self.strict_matches) > 0

    @property
    def has_soft(self) -> bool:
        return len(self.soft_matches) > 0


# ====================================================================== #
# Public API
# ====================================================================== #
# Statuts considérés comme "occupant" le matricule / la CNI (pas un nouveau
# dossier soumis par la même personne, mais une vraie collision).
BLOCKING_STATUSES = {
    DossierStatus.en_cours,
    DossierStatus.soumis,
    DossierStatus.en_validation,
    DossierStatus.valide,
    DossierStatus.complement_requis,
}


async def check_duplicates(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    exclude_dossier_id: Optional[UUID] = None,
    matricule: Optional[str] = None,
    numero_cni: Optional[str] = None,
    nom: Optional[str] = None,
    prenoms: Optional[str] = None,
    date_naissance: Optional[str] = None,
) -> DuplicateCheckResult:
    """Vérifie les doublons stricts (matricule, CNI) et souples (nom+prénoms+date).

    `exclude_dossier_id` permet d'exclure le dossier courant lors d'une
    re-vérification post-correction.
    """
    result = DuplicateCheckResult()

    # --- Strict : matricule ---
    if matricule:
        stmt = select(Dossier).where(
            Dossier.tenant_id == tenant_id,
            func.lower(Dossier.matricule) == matricule.lower().strip(),
            Dossier.status.in_(BLOCKING_STATUSES),
        )
        if exclude_dossier_id is not None:
            stmt = stmt.where(Dossier.id != exclude_dossier_id)
        rows = (await db.execute(stmt)).scalars().all()
        result.strict_matches.extend(
            DuplicateMatch(
                dossier_id=str(d.id),
                dossier_number=d.dossier_number,
                status=d.status.value,
                matched_on="matricule",
            )
            for d in rows
        )

    # --- Strict : numéro CNI ---
    # Le numéro CNI est dans `ocr_data` ou `user_corrections` d'une pièce.
    # On cherche dans le JSONB en suivant la clé `numero` ou `id_card_number`.
    if numero_cni:
        cni = numero_cni.strip().upper()
        stmt = (
            select(Dossier)
            .join(PieceIdentite, PieceIdentite.dossier_id == Dossier.id)
            .where(
                Dossier.tenant_id == tenant_id,
                Dossier.status.in_(BLOCKING_STATUSES),
                or_(
                    PieceIdentite.ocr_data["numero"].astext == cni,
                    PieceIdentite.ocr_data["id_card_number"].astext == cni,
                    PieceIdentite.user_corrections["numero"].astext == cni,
                    PieceIdentite.user_corrections["id_card_number"].astext == cni,
                ),
            )
            .distinct()
        )
        if exclude_dossier_id is not None:
            stmt = stmt.where(Dossier.id != exclude_dossier_id)
        rows = (await db.execute(stmt)).scalars().all()
        result.strict_matches.extend(
            DuplicateMatch(
                dossier_id=str(d.id),
                dossier_number=d.dossier_number,
                status=d.status.value,
                matched_on="numero_cni",
            )
            for d in rows
        )

    # --- Souple : nom + prénoms + date_naissance ---
    if nom and prenoms and date_naissance:
        nom_n = nom.lower().strip()
        prenoms_n = prenoms.lower().strip()
        date_n = date_naissance.strip()
        stmt = (
            select(Dossier)
            .join(PieceIdentite, PieceIdentite.dossier_id == Dossier.id)
            .where(
                Dossier.tenant_id == tenant_id,
                Dossier.status.in_(BLOCKING_STATUSES),
                and_(
                    func.lower(PieceIdentite.ocr_data["nom"].astext) == nom_n,
                    func.lower(PieceIdentite.ocr_data["prenoms"].astext) == prenoms_n,
                    PieceIdentite.ocr_data["date_naissance"].astext == date_n,
                ),
            )
            .distinct()
        )
        if exclude_dossier_id is not None:
            stmt = stmt.where(Dossier.id != exclude_dossier_id)
        rows = (await db.execute(stmt)).scalars().all()
        result.soft_matches.extend(
            DuplicateMatch(
                dossier_id=str(d.id),
                dossier_number=d.dossier_number,
                status=d.status.value,
                matched_on="identity_combo",
            )
            for d in rows
        )

    return result


async def list_soft_duplicates_for_arbitration(
    db: AsyncSession,
    tenant_id: UUID,
) -> list[dict]:
    """Liste les paires/groupes de dossiers en doublon souple à arbitrer.

    Pour l'instant, on parcourt les dossiers `en_validation` et on remonte
    ceux qui matchent un autre dossier sur (nom, prénoms, date_naissance).
    """
    stmt = (
        select(Dossier, PieceIdentite)
        .join(PieceIdentite, PieceIdentite.dossier_id == Dossier.id)
        .where(
            Dossier.tenant_id == tenant_id,
            Dossier.status.in_(BLOCKING_STATUSES),
        )
    )
    rows = list((await db.execute(stmt)).all())

    # Regroupe par identity_key
    groups: dict[tuple, list[dict]] = {}
    for dossier, piece in rows:
        oc = piece.ocr_data or {}
        key = (
            (oc.get("nom") or "").strip().lower(),
            (oc.get("prenoms") or "").strip().lower(),
            (oc.get("date_naissance") or "").strip(),
        )
        if not all(key):  # ignore les pièces sans identité complète
            continue
        groups.setdefault(key, []).append(
            {
                "dossier_id": str(dossier.id),
                "dossier_number": dossier.dossier_number,
                "status": dossier.status.value,
                "matricule": dossier.matricule,
                "employeur_code": dossier.employeur_code,
                "nom": oc.get("nom"),
                "prenoms": oc.get("prenoms"),
                "date_naissance": oc.get("date_naissance"),
            }
        )

    # Ne garde que les groupes avec ≥ 2 dossiers
    return [
        {"identity_key": " | ".join(k), "dossiers": v}
        for k, v in groups.items()
        if len(v) >= 2
    ]
