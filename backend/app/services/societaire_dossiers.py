"""Synchronisation « sociétaire importé » -> dossier (page Dossiers du back-office).

Chaque ligne de la table `societaires` (base MA2E importée depuis le fichier source
Perfect Vision) possède UN dossier, lié par `Dossier.societaire_id`, afin d'apparaître
dans la page « Dossiers » (liste, fiche détail, fiche PDF, export Excel).

- `societaires` reste la SOURCE DE VÉRITÉ : le dossier n'en est qu'une projection.
  À chaque import (nouvelle ligne ou ré-import) et à chaque modification par le chat,
  les données du dossier sont réécrites depuis le sociétaire.
- Le STATUT du dossier n'est fixé qu'à la création (« valide » : le sociétaire est déjà
  adhérent). Il n'est jamais écrasé ensuite, pour respecter une décision d'un agent.
- Pas de canal de conversation : l'utilisateur final créé n'a ni téléphone ni telegram_id
  (le téléphone est dans `extra`), pour qu'aucun message WhatsApp réel ne soit rattaché
  par erreur à ce dossier.
"""
from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, time, timezone
from typing import Iterable, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import DonneesPro, Dossier, DossierStatus, EndUser, Societaire

logger = logging.getLogger(__name__)

BATCH = 300
ORIGINE_IMPORT = "import_base_ma2e"

# Code stocké dans le sociétaire -> valeur attendue par la fiche / les dossiers existants
_SITUATION = {"C": "celibataire", "M": "marie", "D": "divorce", "V": "veuf"}
_CIVILITE = {"M": "M.", "MR": "M.", "MME": "Mme", "MLLE": "Mlle", "MELLE": "Mlle"}


def _dt(d: Optional[date]) -> Optional[datetime]:
    return datetime.combine(d, time.min, tzinfo=timezone.utc) if d else None


def _clean(d: dict) -> dict:
    """Retire les valeurs vides (None / '') pour ne pas écraser avec du vide."""
    return {k: v for k, v in d.items() if v not in (None, "")}


def end_user_values(s: Societaire) -> dict:
    """Champs de l'utilisateur final : nom affiché + coordonnées (dans `extra`)."""
    return {
        "name": f"{s.prenoms or ''} {s.nom}".strip(),
        "extra": _clean({
            "origine": ORIGINE_IMPORT,
            "nom": s.nom,
            "prenoms": s.prenoms,
            "email": s.email,
            "telephone": s.telephone_norm or s.telephone,
            "id_client": s.id_client,
        }),
    }


def donnees_values(s: Societaire) -> dict:
    """Données professionnelles / familiales, aux clés lues par la fiche PDF et la fiche détail."""
    personne, contact = s.personne_a_prevenir, None
    if personne and " - " in personne:  # format écrit par le chat : « NOM - 0701020304 »
        personne, contact = personne.rsplit(" - ", 1)
    extra = _clean({
        "origine": ORIGINE_IMPORT,
        "civilite": _CIVILITE.get((s.civilite or "").upper().rstrip("."), s.civilite),
        "date_naissance": s.date_naissance.isoformat() if s.date_naissance else None,
        "lieu_naissance": s.lieu_naissance,
        "type_piece": s.type_piece,
        "numero_piece": s.numero_piece,
        "domicile": s.adresse,
        "boite_postale": s.boite_postale,
        "nom_conjoint": s.nom_conjoint,
        "personne_a_prevenir": personne,
        "contact_prevenir_1": contact,
        "categorie": s.categorie_client,
        "nom_mere": s.nom_mere,
        "type_client": s.employeur_code,
        "date_depart": s.date_depart.isoformat() if s.date_depart else None,
        "motif_depart": s.motif_depart,
    })
    if s.consentement_recu is not None:
        extra["consentement_recu"] = s.consentement_recu
    return {
        "fonction": s.profession,
        "situation_familiale": _SITUATION.get((s.statut_matrimonial or "").upper(), s.statut_matrimonial),
        "extra": extra,
    }


async def sync_dossiers(db: AsyncSession, tenant_id: UUID, societaires: Iterable[Societaire]) -> tuple[int, int]:
    """Crée / met à jour le dossier de chaque sociétaire. Retourne (créés, mis_à_jour).

    Ne commit pas (c'est le rôle de l'appelant). Un sociétaire déjà lié à un dossier voit
    ses données réécrites ; son statut, ses verrous et ses pièces ne sont pas touchés.
    """
    rows = list(societaires)
    created = updated = 0
    for k in range(0, len(rows), BATCH):
        batch = rows[k:k + BATCH]
        ids = [s.id for s in batch]

        existing = {
            d.societaire_id: d
            for d in (await db.execute(
                select(Dossier).options(selectinload(Dossier.donnees_pro))
                .where(Dossier.societaire_id.in_(ids))
            )).scalars()
        }
        eu_ids = [d.end_user_id for d in existing.values()]
        end_users = {
            u.id: u for u in (await db.execute(select(EndUser).where(EndUser.id.in_(eu_ids)))).scalars()
        } if eu_ids else {}

        # numero_societaire est unique GLOBALEMENT : on reprend le « code client » (la fiche de
        # référence l'affiche dans « Code ») sauf s'il est déjà pris par un autre dossier.
        wanted = {s.code_client[:32] for s in batch if s.code_client and s.id not in existing}
        taken = set((await db.execute(
            select(Dossier.numero_societaire).where(Dossier.numero_societaire.in_(wanted))
        )).scalars()) if wanted else set()

        for s in batch:
            eu_v, dp_v = end_user_values(s), donnees_values(s)
            d = existing.get(s.id)
            if d is not None:
                eu = end_users.get(d.end_user_id)
                if eu is not None:
                    eu.name = eu_v["name"]
                    eu.extra = {**(eu.extra or {}), **eu_v["extra"]}
                d.matricule = (s.matricule or "")[:32] or None
                d.employeur_code = (s.employeur_code or "")[:32] or None
                if d.donnees_pro is not None:
                    d.donnees_pro.fonction = dp_v["fonction"]
                    d.donnees_pro.situation_familiale = dp_v["situation_familiale"]
                    d.donnees_pro.extra = {**(d.donnees_pro.extra or {}), **dp_v["extra"]}
                else:
                    db.add(DonneesPro(tenant_id=tenant_id, dossier_id=d.id, **dp_v))
                updated += 1
                continue

            eu = EndUser(id=uuid.uuid4(), tenant_id=tenant_id, **eu_v)
            numero = s.code_client[:32] if s.code_client and s.code_client[:32] not in taken else None
            if numero:
                taken.add(numero)
            d = Dossier(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                dossier_number=f"IMP-{s.id_client}"[:64],
                end_user_id=eu.id,
                societaire_id=s.id,
                status=DossierStatus.valide,
                matricule=(s.matricule or "")[:32] or None,
                employeur_code=(s.employeur_code or "")[:32] or None,
                numero_societaire=numero,
                submitted_at=_dt(s.date_adhesion),   # « Soumis le » = date d'adhésion
                validated_at=_dt(s.date_adhesion),
            )
            db.add_all([eu, d])
            db.add(DonneesPro(tenant_id=tenant_id, dossier_id=d.id, **dp_v))
            created += 1
        await db.flush()
    logger.info("sync dossiers sociétaires : %d créés, %d mis à jour", created, updated)
    return created, updated
