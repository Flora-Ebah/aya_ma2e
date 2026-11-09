"""Actions workflow branchées sur la base des sociétaires importée (backlog 03/04).

`lookup_societaire_base` retrouve un sociétaire MA2E existant (table `societaires`)
à partir de ce que l'utilisateur tape : matricule, ID client, code client ou
n° de pièce d'identité (CNI).

Confidentialité : la saisie n'est pas authentifiée (n'importe qui connaissant un
matricule peut la faire). Le message renvoyé au sociétaire ne contient donc que
le minimum : prénom + initiale du nom, statut d'adhésion, employeur, date
d'adhésion. Jamais de téléphone, email, adresse ou n° de pièce.
"""
from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.conversation.workflow_actions import ActionResult, workflow_action
from app.models import Societaire
from app.services.societaire_import import norm_cni, norm_matricule

logger = logging.getLogger(__name__)

_MAX_CANDIDATES = 3


def _fmt_date(d) -> str:
    return d.strftime("%d/%m/%Y") if d else "—"


def display_name(s: Societaire) -> str:
    """« Falikou S. » : prénom + initiale du nom, pour ne pas exposer l'identité complète."""
    prenom = (s.prenoms or "").strip().title()
    initiale = f"{s.nom[0].upper()}." if s.nom else ""
    return f"{prenom} {initiale}".strip() or "Sociétaire"


def statut_label(s: Societaire) -> str:
    if s.actif:
        return "✅ Sociétaire actif"
    return f"⛔ Adhésion clôturée le {_fmt_date(s.date_depart)}"


async def find_societaires(
    db: AsyncSession, tenant_id: UUID, query: str, limit: int = _MAX_CANDIDATES + 1
) -> list[Societaire]:
    """Sociétaires dont matricule, ID client, code client ou CNI correspond à `query`."""
    q = (query or "").strip()
    if not q:
        return []
    mat = norm_matricule(q)
    cni = norm_cni(q)
    raw_id = q.upper().replace(" ", "")

    conds = [Societaire.id_client == raw_id, Societaire.code_client == raw_id]
    if mat:
        conds.append(Societaire.matricule_norm == mat)
    if cni:
        conds.append(Societaire.cni_norm == cni)

    res = await db.execute(
        select(Societaire)
        .where(Societaire.tenant_id == tenant_id, or_(*conds))
        .order_by(Societaire.id_client)
        .limit(limit)
    )
    return list(res.scalars().all())


@workflow_action(
    "lookup_societaire_base",
    branches=["not_found", "ambiguous"],
    branch_labels={
        "not_found": "Aucun sociétaire trouvé",
        "ambiguous": "Plusieurs sociétaires correspondent",
    },
    display_label="Rechercher le sociétaire (base MA2E importée)",
    description=(
        "Cherche dans la base importée par matricule, ID client, code client "
        "ou CNI. Peuple soc_display_name, soc_statut, soc_employeur, "
        "soc_date_adhesion, societaire_id."
    ),
    category="Consultation",
)
async def lookup_societaire_base(
    db: AsyncSession,
    context: dict,
    last_input: Optional[str],
) -> ActionResult:
    tenant_id = context.get("_tenant_id")
    query = (
        last_input
        or context.get("consult_ask_matricule_input")
        or context.get("update_ask_matricule_input")
        or context.get("matricule")
    )
    if not query or not tenant_id:
        return ActionResult(branch_key="not_found")

    found = await find_societaires(db, UUID(tenant_id), query)
    if not found:
        logger.info("lookup_societaire_base : aucune correspondance")
        return ActionResult(branch_key="not_found")
    if len(found) > 1:
        # Ne jamais deviner : on demande un identifiant plus précis (ID client / CNI)
        logger.info("lookup_societaire_base : %d correspondances, ambigu", len(found))
        return ActionResult(branch_key="ambiguous")

    s = found[0]
    return ActionResult(
        branch_key=None,
        extra_context={
            "societaire_id": str(s.id),
            "soc_display_name": display_name(s),
            "soc_statut": statut_label(s),
            "soc_employeur": s.employeur_code or "—",
            "soc_date_adhesion": _fmt_date(s.date_adhesion),
            "matricule": s.matricule or query.strip(),
        },
    )


# ======================================================================
# Mise à jour de compte (backlog 04) — champs du formulaire papier MA2E
# « DEMANDE DE MISE A JOUR DE COMPTE »
# ======================================================================
import re  # noqa: E402
from datetime import datetime  # noqa: E402

from app.models import AuditAction, Employeur  # noqa: E402
from app.services import audit_service  # noqa: E402
from app.services.societaire_import import norm_phone  # noqa: E402

_MAX_DOB_ATTEMPTS = 3
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")
_MARITAL = {
    "c": "C", "celibataire": "C", "célibataire": "C",
    "m": "M", "marie": "M", "marié": "M", "mariee": "M", "mariée": "M", "marié(e)": "M",
    "d": "D", "divorce": "D", "divorcé": "D", "divorcee": "D", "divorcée": "D", "divorcé(e)": "D",
    "v": "V", "veuf": "V", "veuve": "V", "veuf/veuve": "V",
}
_YES = {"oui", "o", "yes", "y", "1", "j'accepte", "jaccepte", "d'accord"}
_NO = {"non", "n", "no", "2", "je refuse"}

# n° du menu -> définition. `kind` pilote la validation (voir _validate).
# Le RIB / coordonnées bancaires sont volontairement absents (voir note tâche 04).
FIELDS: dict[str, dict] = {
    "1": dict(col="email", label="Email", kind="email", hint="(ex. nom@exemple.com)"),
    "2": dict(col="telephone", label="Téléphone", kind="phone", hint="(10 chiffres, ex. 07 01 02 03 04)"),
    "3": dict(col="adresse", label="Domicile", kind="text", max=255, hint="(quartier, commune)"),
    "4": dict(col="boite_postale", label="Boîte postale", kind="text", max=128, hint="(ex. 01 BP 1234 Abidjan 01)"),
    "5": dict(col="statut_matrimonial", label="Situation matrimoniale", kind="marital",
              hint="(célibataire, marié(e), divorcé(e) ou veuf/veuve)"),
    "6": dict(col="nom_conjoint", label="Nom et prénoms du conjoint", kind="text", max=255, upper=True, hint=""),
    "7": dict(col="nom_mere", label="Nom de la mère", kind="text", max=255, upper=True, hint=""),
    "8": dict(col="profession", label="Fonction", kind="text", max=255, upper=True, hint=""),
    "9": dict(col="categorie_client", label="Catégorie", kind="text", max=64, upper=True,
              hint="(ex. CADRE, AGENT DE MAÎTRISE, EMPLOYÉ)"),
    "10": dict(col="employeur_code", label="Société / employeur", kind="employeur", hint="(ex. SODECI, CIE, GS2E)"),
    "11": dict(col="personne_a_prevenir", label="Personne à prévenir", kind="contact",
               hint="(nom puis numéro, ex. KONE Awa - 07 01 02 03 04)"),
    "12": dict(col="consentement_recu", label="Consentement au traitement de mes données", kind="bool",
               hint="— répondez *OUI* pour autoriser MA2E à traiter vos données personnelles, ou *NON*"),
}
MENU_SIZE = len(FIELDS)


def _parse_dob(text: str):
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d %m %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime((text or "").strip(), fmt).date()
        except ValueError:
            continue
    return None


def _mask(v) -> str:
    """Garde les 3 derniers caractères : traçable sans stocker la donnée en clair."""
    v = "" if v is None else str(v)
    return ("•" * max(len(v) - 3, 0)) + v[-3:] if v else ""


async def _load(db: AsyncSession, context: dict) -> Optional[Societaire]:
    sid, tid = context.get("societaire_id"), context.get("_tenant_id")
    if not sid or not tid:
        return None
    return (await db.execute(
        select(Societaire).where(Societaire.id == UUID(sid), Societaire.tenant_id == UUID(tid))
    )).scalar_one_or_none()


async def _validate(db: AsyncSession, tenant_id: UUID, f: dict, value: str):
    """Retourne (valeur_normalisée, None) ou (None, message_erreur)."""
    kind = f["kind"]
    if kind == "email":
        if not _EMAIL_RE.match(value) or len(value) > 255:
            return None, "Adresse email invalide."
        return value.lower(), None
    if kind == "phone":
        phone = norm_phone(value)
        return (phone, None) if phone else (None, "Numéro invalide : saisissez 10 chiffres (ex. 07 01 02 03 04).")
    if kind == "marital":
        m = _MARITAL.get(value.strip().lower())
        return (m, None) if m else (None, "Précisez : célibataire, marié(e), divorcé(e) ou veuf/veuve.")
    if kind == "bool":
        v = value.strip().lower()
        if v in _YES:
            return True, None
        if v in _NO:
            return False, None
        return None, "Répondez par OUI ou par NON."
    if kind == "employeur":
        q = value.strip().lower()
        rows = (await db.execute(
            select(Employeur).where(Employeur.tenant_id == tenant_id, Employeur.is_active.is_(True))
        )).scalars().all()
        for e in rows:
            if q in (e.code.lower(), e.name.lower()):
                return e.code.upper(), None
        return None, "Société non reconnue. Choisissez parmi : " + ", ".join(sorted(e.code for e in rows)) + "."
    if kind == "contact":
        if len(value) > 255:
            return None, "Texte trop long (255 caractères max)."
        phone = norm_phone(value)
        if not phone:
            return None, "Indiquez le nom puis un numéro à 10 chiffres (ex. KONE Awa - 07 01 02 03 04)."
        name = re.sub(r"[\d\s/;,.+()-]+$", "", value).strip().upper()
        return (f"{name} - {phone}" if name else phone), None
    # texte libre
    if len(value) > f.get("max", 255):
        return None, f"Texte trop long ({f.get('max', 255)} caractères max)."
    return (value.upper() if f.get("upper") else value), None


@workflow_action(
    "verify_societaire_identity",
    branches=["mismatch", "no_birthdate", "locked"],
    branch_labels={
        "mismatch": "Date de naissance incorrecte",
        "no_birthdate": "Date de naissance absente de la base",
        "locked": "Trop de tentatives",
    },
    display_label="Vérifier l'identité (date de naissance)",
    description="Compare la date saisie à la date de naissance du sociétaire trouvé (3 essais max).",
    category="Mise à jour",
)
async def verify_societaire_identity(
    db: AsyncSession, context: dict, last_input: Optional[str],
) -> ActionResult:
    s = await _load(db, context)
    if s is None:
        return ActionResult(branch_key="mismatch")
    if s.date_naissance is None:
        # Pas de second facteur possible : on refuse plutôt que de laisser modifier
        return ActionResult(branch_key="no_birthdate")

    attempts = int(context.get("dob_attempts", 0)) + 1
    given = _parse_dob(last_input or context.get("update_ask_dob_input") or "")
    if given == s.date_naissance:
        return ActionResult(branch_key=None, extra_context={"dob_attempts": 0, "identity_verified": True})
    logger.warning("verify_societaire_identity : échec %d/%d (societaire=%s)",
                   attempts, _MAX_DOB_ATTEMPTS, s.id)
    return ActionResult(
        branch_key="locked" if attempts >= _MAX_DOB_ATTEMPTS else "mismatch",
        extra_context={"dob_attempts": attempts, "identity_verified": False},
    )


@workflow_action(
    "prepare_societaire_field",
    branches=["invalid"],
    branch_labels={"invalid": "Choix de champ invalide"},
    display_label="Préparer le champ à modifier",
    description=(
        "Valide le numéro choisi dans le menu et expose field_label / field_hint "
        "pour la question suivante."
    ),
    category="Mise à jour",
)
async def prepare_societaire_field(
    db: AsyncSession, context: dict, last_input: Optional[str],
) -> ActionResult:
    choice = (last_input or context.get("update_choose_field_input") or "").strip()
    f = FIELDS.get(choice)
    if f is None:
        return ActionResult(branch_key="invalid", message=f"⚠️ Choix invalide. Tapez un numéro de 1 à {MENU_SIZE}.")
    return ActionResult(
        branch_key=None,
        extra_context={"field_choice": choice, "field_label": f["label"], "field_hint": f["hint"]},
    )


@workflow_action(
    "apply_societaire_update",
    branches=["invalid"],
    branch_labels={"invalid": "Valeur refusée"},
    display_label="Appliquer la modification (base sociétaires)",
    description=(
        "Met à jour le champ choisi du sociétaire (après vérification d'identité). "
        "Valide la valeur, historise l'ancienne et écrit l'audit."
    ),
    category="Mise à jour",
)
async def apply_societaire_update(
    db: AsyncSession, context: dict, last_input: Optional[str],
) -> ActionResult:
    if not context.get("identity_verified"):
        return ActionResult(branch_key="invalid", message="⚠️ Identité non vérifiée. Modification refusée.")
    s = await _load(db, context)
    if s is None:
        return ActionResult(branch_key="invalid", message="⚠️ Sociétaire introuvable.")

    f = FIELDS.get(str(context.get("field_choice") or ""))
    value = (last_input or context.get("update_ask_new_value_input") or "").strip()
    if f is None:
        return ActionResult(branch_key="invalid", message=f"⚠️ Choix invalide. Tapez un numéro de 1 à {MENU_SIZE}.")
    if not value:
        return ActionResult(branch_key="invalid", message="⚠️ Valeur vide.")

    tenant_id = UUID(context["_tenant_id"])
    new, err = await _validate(db, tenant_id, f, value)
    if err:
        return ActionResult(branch_key="invalid", message=f"⚠️ {err}")

    col = f["col"]
    old = getattr(s, col)
    setattr(s, col, new)
    if col == "telephone":
        s.telephone_norm = new  # `new` est déjà le numéro normalisé à 10 chiffres

    extra = dict(s.extra or {})
    hist = list(extra.get("_modifications", []))[-19:]
    hist.append({"date": datetime.utcnow().isoformat(timespec="seconds"), "champ": col,
                 "ancien": old, "nouveau": new, "via": "chat"})
    extra["_modifications"] = hist
    s.extra = extra

    if col == "consentement_recu":
        action = AuditAction.consent_given if new else AuditAction.consent_refused
        details = {"champ": col, "valeur": bool(new), "canal": "chat"}
    else:
        action = AuditAction.user_updated
        details = {"champ": col, "ancien": _mask(old), "nouveau": _mask(new), "canal": "chat"}
    await audit_service.log(
        db, tenant_id=tenant_id, action=action, resource_type="societaire",
        resource_id=str(s.id), actor_type="end_user", details=details,
    )
    await db.flush()
    return ActionResult(branch_key=None, message=f"✅ *{f['label']}* mis à jour.")
