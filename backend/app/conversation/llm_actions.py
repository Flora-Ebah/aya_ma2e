"""Actions dédiées aux parcours générés par le LLM (ingestion Word/PDF).

Le LLM émet typiquement les noms d'action : `send_otp`, `verify_otp`,
`build_recap`, `lookup_societaire`. On enregistre ici de quoi exécuter
chacune d'elles, en déléguant aux actions historiques quand c'est possible.
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.conversation.workflow_actions import ActionResult, workflow_action

logger = logging.getLogger(__name__)


# Libellés lisibles pour chaque clé du contexte dans le récap final.
# Ordre choisi = ordre d'affichage à l'utilisateur.
_RECAP_LABELS: list[tuple[str, str]] = [
    ("civilite", "Civilité"),
    ("nom_de_famille", "Nom"),
    ("nom", "Nom"),
    ("prenoms", "Prénoms"),
    ("date_de_naissance", "Date de naissance"),
    ("lieu_de_naissance", "Lieu de naissance"),
    ("situation_matrimoniale", "Situation matrimoniale"),
    ("type_de_piece_d_identite", "Type de pièce"),
    ("type_piece_identite", "Type de pièce"),
    ("numero_de_la_piece_d_identite", "N° pièce"),
    ("numero_piece_identite", "N° pièce"),
    ("numero_cni", "N° CNI"),
    ("profession", "Profession"),
    ("fonction_actuelle", "Fonction"),
    ("service_d_affectation", "Service"),
    ("adresse_de_domicile", "Domicile"),
    ("domicile", "Domicile"),
    ("boite_postale", "Boîte postale"),
    ("numero_de_telephone", "Téléphone"),
    ("telephone", "Téléphone"),
    ("telephone_cellulaire", "Cellulaire"),
    ("telephone_domicile", "Téléphone domicile"),
    ("telephone_bureau", "Téléphone bureau"),
    ("adresse_email", "Email"),
    ("email", "Email"),
    ("matricule_gs2e", "Matricule GS2E"),
    ("matricule", "Matricule"),
    ("categorie_professionnelle", "Catégorie"),
    ("employeur", "Employeur"),
    ("societe", "Société"),
    ("direction", "Direction"),
    ("exploitation_site", "Exploitation"),
    ("date_d_embauche", "Date d'embauche"),
    ("nom_et_prenoms_du_conjoint", "Conjoint"),
    ("conjoint", "Conjoint"),
    ("nom_de_jeune_fille_de_la_mere", "Mère (nom de jeune fille)"),
    ("mere", "Mère"),
    ("personne_a_prevenir", "Personne à prévenir"),
    ("ayant_droit_declare", "Ayant droit"),
    ("ayants_droit", "Ayants droit"),
]


def _format_recap(ctx: dict) -> str:
    """Produit un récap texte sobre à partir du contexte accumulé.

    - Parcourt les clés dans l'ordre `_RECAP_LABELS`
    - N'affiche que les valeurs non vides, non internes (`_`), non boilerplate
    - Ne duplique pas si plusieurs clés mappent le même libellé
    """
    seen_labels: set[str] = set()
    lines: list[str] = []
    for key, label in _RECAP_LABELS:
        if label in seen_labels:
            continue
        value = ctx.get(key)
        if value in (None, ""):
            continue
        if not isinstance(value, (str, int, float)):
            continue
        lines.append(f"- {label} : {value}")
        seen_labels.add(label)

    if not lines:
        return "Récapitulatif indisponible (aucune information collectée)."

    return "Récapitulatif de votre demande :\n\n" + "\n".join(lines)


@workflow_action(
    "build_recap",
    display_label="Préparer le récapitulatif",
    description="Formate les informations collectées en un récapitulatif lisible.",
    category="Finalisation",
)
async def build_recap(
    db: AsyncSession,
    context: dict,
    last_input: Optional[str],
) -> ActionResult:
    recap = _format_recap(context)
    # On garde le récap dans le contexte pour qu'un éventuel template de
    # confirmation puisse le réinjecter via {{recap}}.
    return ActionResult(extra_context={"recap": recap}, message=recap)


# ---------------------------------------------------------------------------
# Alias OTP : le LLM émet souvent `send_otp` / `verify_otp` au lieu des noms
# historiques `send_email_otp` / `verify_email_otp`. On déduplique en
# déléguant.
# ---------------------------------------------------------------------------


@workflow_action(
    "send_otp",
    display_label="Envoyer un code OTP",
    description="Alias de send_email_otp pour les parcours générés par IA.",
    category="OTP",
)
async def send_otp(
    db: AsyncSession,
    context: dict,
    last_input: Optional[str],
) -> ActionResult:
    from app.conversation import default_actions
    return await default_actions.send_email_otp(db, context, last_input)


@workflow_action(
    "verify_otp",
    display_label="Vérifier le code OTP",
    description="Alias de verify_email_otp pour les parcours générés par IA.",
    category="OTP",
)
async def verify_otp(
    db: AsyncSession,
    context: dict,
    last_input: Optional[str],
) -> ActionResult:
    from app.conversation import default_actions
    return await default_actions.verify_email_otp(db, context, last_input)


# ---------------------------------------------------------------------------
# Recherche d'un dossier existant par matricule (parcours "Mise à jour").
# ---------------------------------------------------------------------------


@workflow_action(
    "lookup_societaire",
    branches=["not_found"],
    branch_labels={"not_found": "Matricule introuvable"},
    display_label="Rechercher le dossier sociétaire",
    description="Cherche un dossier existant par matricule GS2E et le charge dans le contexte.",
    category="Mise à jour",
)
async def lookup_societaire(
    db: AsyncSession,
    context: dict,
    last_input: Optional[str],
) -> ActionResult:
    """Cherche un dossier par matricule. Résout plusieurs variantes de clés
    (nouveau LLM : `matricule_gs2e`, ancien : `ask_matricule`, ou dernière
    saisie utilisateur)."""
    from sqlalchemy import select
    from app.models import Dossier, EndUser

    def _first(keys: list[str]) -> str:
        for k in keys:
            v = context.get(k)
            if v and str(v).strip():
                return str(v).strip()
        return ""

    matricule = _first([
        "matricule_gs2e", "matricule", "ask_matricule",
        "matricule_societaire", "matricule_sor_sip",
    ]) or (last_input or "").strip()

    if not matricule:
        return ActionResult(
            branch_key="not_found",
            message="❌ Matricule manquant. Merci de saisir à nouveau votre matricule GS2E.",
        )

    # Recherche insensible à la casse
    from sqlalchemy.orm import selectinload
    row = (
        await db.execute(
            select(Dossier)
            .options(selectinload(Dossier.donnees_pro))
            .where(Dossier.matricule.ilike(matricule))
        )
    ).scalars().first()

    if row is None:
        logger.info("lookup_societaire : matricule '%s' introuvable", matricule)
        return ActionResult(
            branch_key="not_found",
            message=(
                f"❌ Aucun dossier trouvé pour le matricule « {matricule} ». "
                "Vérifiez votre saisie et réessayez."
            ),
        )

    end_user = (
        await db.execute(select(EndUser).where(EndUser.id == row.end_user_id))
    ).scalar_one_or_none()

    # Pré-charge les valeurs actuelles sous des clés `current_<name>` pour que
    # _build_ui_hint puisse pré-remplir les forms de modification.
    extra_data = (row.donnees_pro.extra if row.donnees_pro else {}) or {}
    nom = ""
    prenoms = ""
    if end_user and end_user.name:
        parts = end_user.name.strip().split()
        nom = parts[-1] if parts else ""
        prenoms = " ".join(parts[:-1]) if len(parts) > 1 else ""

    pre: dict[str, str] = {
        # Champs utilisés par form_coordonnees / form_contact
        "current_telephone":          (end_user.phone if end_user else "") or "",
        "current_numero_de_telephone":(end_user.phone if end_user else "") or "",
        "current_email":              ((end_user.extra or {}).get("email") if end_user else "") or "",
        "current_adresse_email":      ((end_user.extra or {}).get("email") if end_user else "") or "",
        "current_domicile":           extra_data.get("domicile") or extra_data.get("adresse_domicile", ""),
        "current_adresse_de_domicile":extra_data.get("domicile") or extra_data.get("adresse_domicile", ""),
        "current_boite_postale":      extra_data.get("boite_postale_choisie") or extra_data.get("boite_postale", ""),
        # Pro
        "current_matricule":          row.matricule or "",
        "current_matricule_gs2e":     row.matricule or "",
        "current_employeur":          row.employeur_code or "",
        "current_societe":            row.employeur_code or "",
        "current_categorie":          extra_data.get("categorie", ""),
        "current_categorie_professionnelle": extra_data.get("categorie", ""),
        "current_direction":          extra_data.get("direction_service", ""),
        "current_service":            extra_data.get("direction_service", ""),
        # Identité
        "current_nom":                nom,
        "current_prenoms":            prenoms,
        "current_civilite":           extra_data.get("civilite", ""),
        "current_date_naissance":     extra_data.get("date_naissance", ""),
        "current_lieu_naissance":     extra_data.get("lieu_naissance", ""),
        "current_situation_matrimoniale": (row.donnees_pro.situation_familiale if row.donnees_pro else "") or "",
        # Pièce
        "current_type_piece_identite":extra_data.get("type_piece", ""),
        "current_numero_piece_identite":extra_data.get("numero_piece", ""),
    }

    extra = {
        "loaded_dossier_id": str(row.id),
        "loaded_dossier_number": row.dossier_number,
        "loaded_societaire_name": end_user.name if end_user else None,
        # Permet au save suivant de patcher le dossier existant au lieu
        # d'en créer un nouveau.
        "_update_mode": True,
        "_update_dossier_id": str(row.id),
        **pre,
    }
    return ActionResult(
        extra_context=extra,
        message=(
            f"✅ Dossier retrouvé : *{end_user.name if end_user else row.dossier_number}* "
            f"({row.dossier_number}). Vous pouvez maintenant choisir ce que vous souhaitez modifier."
        ),
    )
