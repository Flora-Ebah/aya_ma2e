"""Base des sociétaires MA2E existants (import du fichier source MA2E).

Contrairement à `Collaborateur` (référentiel RH ERANOVE), cette table reflète la
base de gestion historique de la mutuelle : une ligne = un sociétaire déjà
adhérent. Elle sert aux parcours « Vérification de statut » et « Mise à jour de
compte » (retrouver un sociétaire par matricule, ID client, CNI ou téléphone).

Clé d'upsert : (tenant_id, id_client). Un ré-import met à jour les lignes
existantes au lieu de les rejeter.

Les colonnes de recherche sont indexées et stockées sous forme normalisée
(`*_norm`) car les données sources sont sales (matricules de formats variables,
n° de pièce parfois égal au matricule, téléphones multiples...).
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class Societaire(Base):
    __tablename__ = "societaires"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id_client", name="uq_societaire_id_client"),
        Index("ix_soc_tenant_matricule", "tenant_id", "matricule_norm"),
        Index("ix_soc_tenant_code_client", "tenant_id", "code_client"),
        Index("ix_soc_tenant_cni", "tenant_id", "cni_norm"),
        Index("ix_soc_tenant_tel", "tenant_id", "telephone_norm"),
        Index("ix_soc_tenant_nom", "tenant_id", "nom"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )

    # --- Identifiants (colonnes sources : id_client, code_client, num_manuel)
    id_client: Mapped[str] = mapped_column(String(32), nullable=False)
    code_client: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    matricule: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)       # num_manuel
    matricule_norm: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # MAJ, sans séparateurs

    # --- État civil
    nom: Mapped[str] = mapped_column(String(255), nullable=False)
    prenoms: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sexe: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    civilite: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    statut_matrimonial: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    date_naissance: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    lieu_naissance: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    nationalite: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # --- Pièce d'identité
    type_piece: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    numero_piece: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    cni_norm: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # --- Contact
    telephone: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)       # brut (peut contenir 2 n°)
    telephone_norm: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)   # 1er n° valide, 10 chiffres
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    adresse: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ville: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    boite_postale: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    # --- Situation familiale / personnes liées (formulaire « Mise à jour de compte »)
    nom_conjoint: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    personne_a_prevenir: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # « NOM - 07xxxxxxxx »

    # --- Professionnel / adhésion
    profession: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    employeur_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)   # SODECI / CIE / GS2E...
    categorie_client: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    agence: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    date_adhesion: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    date_depart: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    motif_depart: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    actif: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)  # False si date_depart renseignée

    # --- Colonnes à compléter côté MA2E (4 dernières colonnes du fichier source)
    nom_mere: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    consentement_recu: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # --- Traçabilité de l'import + ligne source complète (rien n'est perdu)
    extra: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    source_file: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
