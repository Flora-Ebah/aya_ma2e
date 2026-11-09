"""Actions par défaut pour le WorkflowExecutor.

Implémente les `action_name` référencés par le workflow MA2E seedé.
Chaque action mute le contexte de conversation et retourne une `ActionResult`
qui indique vers quelle branche aller (ou None pour suivre next_step_code).

Importer ce module suffit à enregistrer toutes les actions (via le décorateur
@workflow_action).

Conventions :
- Les actions lisent `context["_tenant_id"]`, `context["_end_user_id"]`,
  `context["_channel"]` injectés par le dispatcher/executor.
- Le flag `context["_simulate"] is True` indique le mode simulateur : pas de
  persistance, pas d'envoi email réel, données fictives.
"""
from __future__ import annotations

import logging
import random
import re
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.conversation._ocr_runner import (
    OCRError,
    detect_filename_by_magic,
    is_ocr_compatible,
    run_ocr_recto,
    run_ocr_verso,
)
from app.conversation.workflow_actions import ActionResult, workflow_action
from app.models import (
    Collaborateur,
    ConsentDecision,
    ConsentGate,
    Conversation,
    Dossier,
    DossierStatus,
    Employeur,
    EndUser,
    PieceType,
    Tenant,
)

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Helpers internes
# ----------------------------------------------------------------------
def _tenant_id_from(context: dict) -> Optional[UUID]:
    raw = context.get("_tenant_id")
    if not raw:
        return None
    try:
        return UUID(raw)
    except (ValueError, TypeError):
        return None


def _end_user_id_from(context: dict) -> Optional[UUID]:
    raw = context.get("_end_user_id")
    if not raw:
        return None
    try:
        return UUID(raw)
    except (ValueError, TypeError):
        return None


async def _service_enabled(db: AsyncSession, context: dict, key: str) -> bool:
    """Lit le flag `services.<key>` pour le tenant courant. Défaut: True."""
    tenant_id = _tenant_id_from(context)
    if not tenant_id:
        return True  # pas de tenant → on n'empêche rien
    try:
        from app.services import settings_service
        return bool(await settings_service.get_value(db, tenant_id, "services", key))
    except Exception as e:
        logger.debug("Lecture flag services.%s impossible (%s) → on considère activé", key, e)
        return True


# ----------------------------------------------------------------------
# 1. Vérification matricule dans le référentiel ERANOVE (US-33)
# ----------------------------------------------------------------------
@workflow_action(
    "verify_matricule_referentiel",
    branches=["not_found"],
    branch_labels={"not_found": "Matricule inconnu dans le référentiel"},
    display_label="Vérifier matricule dans le référentiel ERANOVE",
    description="Vérifie le matricule dans le référentiel SI RH ERANOVE (table Collaborateur).",
    category="Identification",
)
async def verify_matricule_referentiel(
    db: AsyncSession,
    context: dict,
    last_input: Optional[str],
) -> ActionResult:
    """Cherche le matricule dans la table Collaborateur.

    NE valide PAS le format/longueur : c'est le step `ask_matricule` qui s'en
    charge via ses `validation_rules` (regex + min_len + max_len + error_message),
    éditables depuis la modal `/assistante/parcours`. Ainsi l'admin peut changer
    la règle ("matricule 8-12 chars", "matricule avec lettres uniquement", etc.)
    sans toucher au code de l'action.
    """
    matricule = (context.get("ask_matricule") or last_input or "").strip()
    if not matricule:
        return ActionResult(branch_key="not_found", message="Matricule manquant.")

    # Recherche dans le référentiel
    result = await db.execute(
        select(Collaborateur).where(
            Collaborateur.matricule.ilike(matricule),
            Collaborateur.statut == "actif",
        )
    )
    collab = result.scalar_one_or_none()

    if collab is None:
        # On accepte quand même (pas tous les sociétaires sont dans le référentiel)
        # mais on log et on marque "anonymous" pour parcours alternatif si désiré.
        logger.info("Matricule %s introuvable dans le référentiel", matricule)
        return ActionResult(
            branch_key=None,  # suit next_step_code
            extra_context={"matricule_verified": False, "matricule": matricule},
        )

    return ActionResult(
        branch_key=None,
        extra_context={
            "matricule_verified": True,
            "matricule": matricule,
            "prenom": collab.prenoms or "",
            "nom": collab.nom or "",
            "employeur_code_default": collab.employeur_code or "",
            "fonction_default": collab.fonction or "",
            "collaborateur_id": str(collab.id),
        },
    )


# ----------------------------------------------------------------------
# 2. Anti-doublon (US-36)
# ----------------------------------------------------------------------
@workflow_action(
    "check_duplicates",
    branches=["duplicate"],
    branch_labels={"duplicate": "Doublon détecté (dossier existant)"},
    display_label="Vérifier qu'il n'y a pas de doublon",
    description="Vérifie qu'aucun dossier validé/soumis n'existe déjà pour ce matricule.",
    category="Identification",
)
async def check_duplicates(
    db: AsyncSession,
    context: dict,
    last_input: Optional[str],
) -> ActionResult:
    """Branche 'duplicate' si un dossier validé existe déjà pour ce matricule."""
    matricule = context.get("matricule")
    if not matricule:
        return ActionResult(branch_key=None)

    existing = (
        await db.execute(
            select(Dossier).where(
                Dossier.matricule.ilike(matricule),
                Dossier.status.in_([DossierStatus.valide, DossierStatus.soumis]),
            )
        )
    ).scalar_one_or_none()

    if existing:
        return ActionResult(
            branch_key="duplicate",
            extra_context={"existing_dossier_id": str(existing.id)},
            message=(
                f"Un dossier existe déjà pour le matricule {matricule} "
                f"(N° {existing.dossier_number})."
            ),
        )

    return ActionResult(branch_key=None)


# ----------------------------------------------------------------------
# 3. OCR — version mock conservée (rétro-compat) + actions Mindee réelles
# ----------------------------------------------------------------------
@workflow_action(
    "ocr_extract_cni",
    branches=["low_score"],
    branch_labels={"low_score": "Score OCR faible"},
    display_label="[LEGACY] OCR mock (données fictives)",
    description="[LEGACY MOCK] Données OCR aléatoires. Utiliser ocr_extract_recto + ocr_extract_verso.",
    category="OCR",
)
async def ocr_extract_cni(
    db: AsyncSession,
    context: dict,
    last_input: Optional[str],
) -> ActionResult:
    """LEGACY MOCK — utilise `ocr_extract_recto` + `ocr_extract_verso` à la place."""
    fake_score = round(0.70 + random.random() * 0.25, 2)
    return ActionResult(
        branch_key="low_score" if fake_score < 0.75 else None,
        extra_context={
            "ocr_score": fake_score,
            "ocr_extracted_name": context.get("nom") or "OUATTARA",
            "ocr_extracted_firstname": context.get("prenom") or "AHMED",
            "ocr_extracted_birthdate": "1985-04-12",
            "ocr_document_number": "C00123456",
        },
        message=f"OCR effectuée — MOCK (score {fake_score:.2f}).",
    )


def _piece_type_from_context(context: dict) -> PieceType:
    """Détermine le type de pièce demandé. Défaut : CNI UEMOA."""
    raw = (context.get("piece_type") or "cni_uemoa").lower()
    try:
        return PieceType(raw)
    except ValueError:
        return PieceType.cni_uemoa


@workflow_action(
    "ocr_extract_recto",
    service="mindee_ocr",
    branches=["disabled", "no_media", "not_configured", "unreadable", "low_score"],
    branch_labels={
        "disabled": "Service OCR désactivé",
        "no_media": "Aucune photo reçue",
        "not_configured": "OCR non configuré (clé API manquante)",
        "unreadable": "Photo illisible",
        "low_score": "Score OCR faible",
    },
    display_label="Analyser le recto de la pièce (OCR)",
    description="OCR Mindee + Groq sur le RECTO de la pièce d'identité.",
    category="OCR",
)
async def ocr_extract_recto(
    db: AsyncSession,
    context: dict,
    last_input: Optional[str],
) -> ActionResult:
    """OCR Mindee réel sur la dernière photo reçue (recto).

    Branches : `disabled`, `no_media`, `not_configured`, `unreadable`, `low_score`.
    En mode simulateur ou si Mindee n'est pas configuré → mock.
    """
    if not await _service_enabled(db, context, "mindee_ocr_enabled"):
        return ActionResult(branch_key="disabled")

    media_url = context.get("last_media_url")
    if not media_url:
        return ActionResult(
            branch_key="no_media",
            message="📷 Je n'ai pas reçu de photo. Merci de renvoyer le *recto* de votre pièce.",
        )

    # Simulateur ou Mindee non configuré → mock pour ne pas bloquer
    if context.get("_simulate") is True:
        return ActionResult(
            branch_key=None,
            extra_context={
                "ocr_recto": {
                    "fields": {
                        "nom": "OUATTARA",
                        "prenoms": "AHMED",
                        "numero_piece": "C00123456",
                        "date_naissance": "1985-04-12",
                        "nationalite": "Ivoirienne",
                    },
                    "confidence": 0.92,
                },
                "ocr_recto_score": 0.92,
                "ocr_extracted_name": "OUATTARA",
                "ocr_extracted_firstname": "AHMED",
                "ocr_extracted_birthdate": "1985-04-12",
                "ocr_document_number": "C00123456",
            },
            message="OCR recto effectuée (simulateur).",
        )

    piece_type = _piece_type_from_context(context)
    try:
        result = await run_ocr_recto(
            media_url, piece_type, tenant_id=_tenant_id_from(context),
        )
    except OCRError as e:
        logger.warning("OCR recto a échoué : %s", e)
        return ActionResult(
            branch_key="not_configured" if "non configurée" in str(e).lower() else "unreadable",
            message=(
                "❌ Impossible d'analyser cette photo. Réessayez avec un cadrage net, "
                "bonne lumière et la pièce à plat."
            ),
        )

    fields = result.get("fields") or {}
    confidence = float(result.get("confidence") or 0.0)
    if not fields.get("nom") and not fields.get("numero_piece"):
        return ActionResult(
            branch_key="unreadable",
            message="⚠️ Photo illisible. Renvoyez une image plus nette du *recto*.",
        )

    branch = "low_score" if confidence < 0.7 else None
    return ActionResult(
        branch_key=branch,
        extra_context={
            "ocr_recto": result,
            "ocr_recto_score": confidence,
            "ocr_extracted_name": fields.get("nom"),
            "ocr_extracted_firstname": fields.get("prenoms"),
            "ocr_extracted_birthdate": fields.get("date_naissance"),
            "ocr_document_number": fields.get("numero_piece"),
            # ⚡ Indispensable : on sauve l'URL du recto AVANT que le verso
            # n'écrase last_media_url. create_real_dossier en a besoin pour
            # attacher la PieceIdentite au dossier.
            "recto_media_url": media_url,
        },
        message=f"✅ Recto analysé (confiance {int(confidence*100)}%).",
    )


@workflow_action(
    "ocr_extract_verso",
    service="mindee_ocr",
    branches=["disabled", "no_media", "not_configured", "unreadable", "incoherent", "low_score"],
    branch_labels={
        "disabled": "Service OCR désactivé",
        "no_media": "Aucune photo reçue",
        "not_configured": "OCR non configuré (clé API manquante)",
        "unreadable": "Photo illisible",
        "incoherent": "Recto et verso ne correspondent pas",
        "low_score": "Score OCR faible",
    },
    display_label="Analyser le verso de la pièce (OCR + MRZ)",
    description="OCR Mindee + Groq sur le VERSO de la pièce (avec lecture MRZ).",
    category="OCR",
)
async def ocr_extract_verso(
    db: AsyncSession,
    context: dict,
    last_input: Optional[str],
) -> ActionResult:
    """OCR Mindee réel sur la dernière photo reçue (verso, avec MRZ).

    Branches : `disabled`, `no_media`, `not_configured`, `unreadable`, `incoherent`, `low_score`.
    """
    if not await _service_enabled(db, context, "mindee_ocr_enabled"):
        return ActionResult(branch_key="disabled")

    media_url = context.get("last_media_url")
    if not media_url:
        return ActionResult(
            branch_key="no_media",
            message="📷 Je n'ai pas reçu de photo. Merci de renvoyer le *verso* de votre pièce.",
        )

    if context.get("_simulate") is True:
        return ActionResult(
            branch_key=None,
            extra_context={
                "ocr_verso": {
                    "mrz": {"line1": "IDCIV...", "line2": "...", "parsed": {}},
                    "confidence": 0.93,
                    "warnings": [],
                },
                "ocr_verso_score": 0.93,
            },
            message="OCR verso effectuée (simulateur).",
        )

    piece_type = _piece_type_from_context(context)
    recto_data = context.get("ocr_recto")
    try:
        result = await run_ocr_verso(
            media_url, piece_type, recto_data=recto_data,
            tenant_id=_tenant_id_from(context),
        )
    except OCRError as e:
        logger.warning("OCR verso a échoué : %s", e)
        return ActionResult(
            branch_key="not_configured" if "non configurée" in str(e).lower() else "unreadable",
            message=(
                "❌ Impossible de lire le verso. La zone MRZ doit être nette."
            ),
        )

    confidence = float(result.get("confidence") or 0.0)
    warnings = result.get("warnings") or []
    if "incoherence_recto_verso" in warnings:
        return ActionResult(
            branch_key="incoherent",
            message="⚠️ Les données du recto et du verso ne correspondent pas.",
            extra_context={"ocr_verso": result, "ocr_verso_score": confidence},
        )

    branch = "low_score" if confidence < 0.7 else None
    return ActionResult(
        branch_key=branch,
        extra_context={
            "ocr_verso": result,
            "ocr_verso_score": confidence,
            # ⚡ Idem que pour le recto : on sauve l'URL pour PieceIdentite
            "verso_media_url": media_url,
        },
        message=f"✅ Verso analysé (confiance {int(confidence*100)}%).",
    )


# ----------------------------------------------------------------------
# 3 bis. Vérification de cohérence — saisie utilisateur ↔ OCR
# ----------------------------------------------------------------------
def _normalize_name(s: Optional[str]) -> str:
    """Normalise un nom pour comparaison : retire accents, espaces, majuscules."""
    if not s:
        return ""
    import unicodedata
    nfkd = unicodedata.normalize("NFKD", str(s).strip().upper())
    no_diac = "".join(c for c in nfkd if not unicodedata.combining(c))
    return " ".join(no_diac.split())


def _normalize_doc_number(s: Optional[str]) -> str:
    """Normalise un n° de pièce : retire espaces, tirets, points, met en MAJ."""
    if not s:
        return ""
    return "".join(c for c in str(s).upper() if c.isalnum())


def _normalize_date(s: Optional[str]) -> str:
    """Convertit JJ/MM/AAAA ou ISO YYYY-MM-DD en YYYY-MM-DD pour comparaison."""
    if not s:
        return ""
    s = str(s).strip()
    # Format ISO ?
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return s
    # Format JJ/MM/AAAA ?
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", s)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    return s  # autre format inconnu


def _similarity(a: str, b: str) -> float:
    """Ratio de similarité 0.0-1.0 entre deux chaînes (SequenceMatcher)."""
    if not a or not b:
        return 0.0
    from difflib import SequenceMatcher
    return SequenceMatcher(None, a, b).ratio()


def _compare_field(user_value: str, ocr_value: str, strict: bool = False) -> str:
    """Compare 2 valeurs déjà normalisées. Retourne : 'match', 'close', 'mismatch'."""
    if not user_value and not ocr_value:
        return "mismatch"  # rien à comparer = pas confirmable
    if not user_value or not ocr_value:
        return "mismatch"  # une seule valeur dispo
    if user_value == ocr_value:
        return "match"
    if strict:
        return "mismatch"
    sim = _similarity(user_value, ocr_value)
    if sim >= 0.85:
        return "close"
    return "mismatch"


@workflow_action(
    "verify_user_data_vs_ocr",
    branches=["match", "partial_match", "mismatch"],
    branch_labels={
        "match": "Tout concorde — confirmation rapide",
        "partial_match": "Différences mineures — confirmer ou corriger",
        "mismatch": "Données saisies ≠ pièce d'identité — revue manuelle",
    },
    display_label="Comparer données saisies ↔ OCR",
    description=(
        "Compare ce que le sociétaire a saisi au clavier (nom, prénoms, "
        "date naissance, n° pièce) avec ce qui a été extrait par OCR sur "
        "le recto/verso. Stocke un résumé visuel dans le contexte pour "
        "affichage par confirm_ocr."
    ),
    category="Identification",
)
async def verify_user_data_vs_ocr(
    db: AsyncSession,
    context: dict,
    last_input: Optional[str],
) -> ActionResult:
    """Compare 4 champs clés saisis vs OCR. Décide d'une branche selon le score."""
    ocr_recto = context.get("ocr_recto") or {}
    ocr_recto_fields = ocr_recto.get("fields") or {}

    # Fallback sur les données issues du verso (parsed MRZ) si recto absent
    ocr_verso = context.get("ocr_verso") or {}
    mrz_parsed = (ocr_verso.get("mrz") or {}).get("parsed") or {}

    # Helper : lit le champ corrigé si présent, sinon la saisie initiale
    def user_field(name: str):
        return context.get(f"correct_{name}") or context.get(f"ask_{name}")

    user_nom      = _normalize_name(user_field("nom"))
    user_prenoms  = _normalize_name(user_field("prenoms"))
    user_numero   = _normalize_doc_number(user_field("numero_piece"))
    user_date     = _normalize_date(user_field("date_naissance"))

    ocr_nom     = _normalize_name(ocr_recto_fields.get("nom") or mrz_parsed.get("nom"))
    ocr_prenoms = _normalize_name(ocr_recto_fields.get("prenoms") or mrz_parsed.get("prenoms"))
    ocr_numero  = _normalize_doc_number(
        ocr_recto_fields.get("numero_piece") or mrz_parsed.get("document_number")
    )
    ocr_date    = _normalize_date(
        ocr_recto_fields.get("date_naissance") or mrz_parsed.get("date_naissance_iso")
    )

    results = {
        "nom":      _compare_field(user_nom, ocr_nom),
        "prenoms":  _compare_field(user_prenoms, ocr_prenoms),
        "numero":   _compare_field(user_numero, ocr_numero, strict=True),  # n° = strict
        "date":     _compare_field(user_date, ocr_date, strict=True),       # date = strict
    }

    # Construit un résumé visuel injecté dans le contexte pour confirm_ocr
    def icon(v: str) -> str:
        return {"match": "✅", "close": "⚠️", "mismatch": "❌"}.get(v, "❓")

    def label(v: str) -> str:
        return {"match": "concorde", "close": "proche (OCR ?)", "mismatch": "DIFFÉRENT"}.get(v, "—")

    summary_lines = [
        f"{icon(results['nom'])} *Nom* : « {user_field('nom') or '—'} » vs OCR « {ocr_recto_fields.get('nom') or '—'} » → {label(results['nom'])}",
        f"{icon(results['prenoms'])} *Prénoms* : « {user_field('prenoms') or '—'} » vs OCR « {ocr_recto_fields.get('prenoms') or '—'} » → {label(results['prenoms'])}",
        f"{icon(results['numero'])} *N° pièce* : « {user_field('numero_piece') or '—'} » vs OCR « {ocr_recto_fields.get('numero_piece') or '—'} » → {label(results['numero'])}",
        f"{icon(results['date'])} *Date naissance* : « {user_field('date_naissance') or '—'} » vs OCR « {ocr_recto_fields.get('date_naissance') or '—'} » → {label(results['date'])}",
    ]
    summary = "\n".join(summary_lines)

    # Décision : combien de champs en mismatch ?
    mismatches = sum(1 for v in results.values() if v == "mismatch")
    closes     = sum(1 for v in results.values() if v == "close")

    extra_context = {
        "data_match_results": results,
        "data_match_summary": summary,
        "data_match_mismatches": mismatches,
        "data_match_closes": closes,
    }

    if mismatches == 0 and closes == 0:
        return ActionResult(branch_key="match", extra_context=extra_context)
    if mismatches >= 3:
        # 3+ champs ne correspondent pas → très probablement un autre document
        return ActionResult(
            branch_key="mismatch",
            extra_context=extra_context,
            message=(
                "⚠️ *Vos informations saisies ne correspondent pas à votre pièce d'identité.*\n\n"
                f"{summary}\n\n"
                "Votre dossier va être examiné manuellement par un agent MA2E."
            ),
        )
    # 1-2 champs en différence (souvent OCR imparfait) → laisse confirmer
    return ActionResult(branch_key="partial_match", extra_context=extra_context)


# ----------------------------------------------------------------------
# 4. Création réelle du dossier + attribution N° sociétaire + consentements
# ----------------------------------------------------------------------
@workflow_action(
    "create_validated_dossier",
    display_label="[LEGACY] Créer le dossier validé (stub)",
    description="[LEGACY] Stub vers create_real_dossier en mode runtime.",
    category="Création dossier",
)
async def create_validated_dossier(
    db: AsyncSession,
    context: dict,
    last_input: Optional[str],
) -> ActionResult:
    """LEGACY STUB — utilise `create_real_dossier` pour persister réellement."""
    if context.get("_simulate") is True:
        fake_number = f"MEMB-2026-{random.randint(100000, 999999)}"
        return ActionResult(
            extra_context={"numero_societaire": fake_number, "dossier_created": True},
            message=f"Dossier créé (simulateur). Numéro sociétaire : {fake_number}",
        )
    return await create_real_dossier(db, context, last_input)


@workflow_action(
    "create_real_dossier",
    branches=["error"],
    branch_labels={"error": "Erreur lors de la création"},
    display_label="Créer le dossier sociétaire (enregistrement BD + N° sociétaire)",
    description="Persiste le dossier en BD + attribue le N° sociétaire + enregistre les consentements ARTCI.",
    category="Création dossier",
)
async def create_real_dossier(
    db: AsyncSession,
    context: dict,
    last_input: Optional[str],
) -> ActionResult:
    """Persiste le dossier en BD, attribue un N° sociétaire, enregistre les
    consentements ARTCI.

    Branches : `error` si échec, sinon next_step_code par défaut.
    """
    from app.services import consent_service, dossiers as dossier_service, member_number_service

    if context.get("_simulate") is True:
        fake_number = f"MEMB-2026-{random.randint(100000, 999999)}"
        fake_dossier_number = f"MA2E-2026-{random.randint(100000, 999999):06d}"
        return ActionResult(
            extra_context={
                "numero_societaire": fake_number,
                "dossier_number": fake_dossier_number,
                "dossier_created": True,
            },
            message=f"Dossier créé (simulateur). Numéro : {fake_number}",
        )

    tenant_id = _tenant_id_from(context)
    end_user_id = _end_user_id_from(context)
    if not tenant_id or not end_user_id:
        logger.error("create_real_dossier : tenant_id ou end_user_id manquant dans le contexte")
        return ActionResult(
            branch_key="error",
            message="Erreur interne : contexte de session incomplet.",
        )

    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
    end_user = (await db.execute(select(EndUser).where(EndUser.id == end_user_id))).scalar_one_or_none()
    if not tenant or not end_user:
        return ActionResult(
            branch_key="error",
            message="Erreur interne : tenant ou utilisateur introuvable.",
        )

    conversation_id = context.get("_conversation_id")
    conversation = None
    if conversation_id:
        conversation = (
            await db.execute(select(Conversation).where(Conversation.id == UUID(conversation_id)))
        ).scalar_one_or_none()
    if conversation is None:
        return ActionResult(
            branch_key="error",
            message="Erreur interne : conversation introuvable.",
        )

    try:
        # Mode mise à jour : si lookup_societaire a résolu un dossier existant,
        # on le patche au lieu d'en créer un nouveau.
        update_mode = bool(context.get("_update_mode"))
        update_dossier_id = context.get("_update_dossier_id")
        dossier = None
        if update_mode and update_dossier_id:
            from uuid import UUID as _UUID
            from sqlalchemy import select as _select
            from sqlalchemy.orm import selectinload as _selectinload
            try:
                dossier = (
                    await db.execute(
                        _select(Dossier)
                        .options(_selectinload(Dossier.donnees_pro))
                        .where(Dossier.id == _UUID(update_dossier_id))
                    )
                ).scalar_one_or_none()
            except Exception:
                dossier = None
            if dossier is not None:
                # Récupère l'EndUser du dossier existant plutôt que celui de la conversation
                existing_eu = (
                    await db.execute(select(EndUser).where(EndUser.id == dossier.end_user_id))
                ).scalar_one_or_none()
                if existing_eu:
                    end_user = existing_eu
                logger.info(
                    "create_real_dossier : mode UPDATE sur dossier existant %s",
                    dossier.dossier_number,
                )

        if dossier is None:
            dossier = await dossier_service.get_or_create_dossier(db, tenant, end_user, conversation)

        # Fonction helper pour chercher une clé dans plusieurs variantes.
        # Compat ancien schéma (`ask_xxx`) + nouveau schéma LLM (form_fields).
        def _ctx_first(keys: list[str]) -> str:
            for k in keys:
                v = context.get(k)
                if v and str(v).strip() and str(v).strip() != "*":
                    return str(v).strip()
            return ""

        # ── Matricule ──
        mat = _ctx_first([
            "ask_matricule", "matricule", "matricule_gs2e", "matricule_societaire",
        ])
        if mat:
            dossier.matricule = mat

        # ── Employeur : accepte un index numérique OU le libellé direct ──
        ask_emp = _ctx_first(["ask_employeur", "employeur", "societe_employeur"])
        if ask_emp:
            from app.models import Employeur
            from sqlalchemy import select as _select
            employeurs_q = await db.execute(
                _select(Employeur)
                .where(Employeur.tenant_id == tenant.id, Employeur.is_active.is_(True))
                .order_by(Employeur.name)
            )
            employeurs = list(employeurs_q.scalars().all())
            if ask_emp.isdigit():
                idx = int(ask_emp) - 1
                if 0 <= idx < len(employeurs):
                    dossier.employeur_code = employeurs[idx].code
            else:
                # Essaie match par code puis par name (insensible à la casse)
                low = ask_emp.lower()
                match = next(
                    (e for e in employeurs if e.code.lower() == low or e.name.lower() == low),
                    None,
                )
                dossier.employeur_code = match.code if match else ask_emp

        nom = _ctx_first([
            "ask_nom", "nom_de_famille", "nom", "nom_famille", "last_name",
        ])
        prenoms = _ctx_first([
            "ask_prenoms", "prenoms", "prenom", "first_name", "firstname",
        ])
        if nom or prenoms:
            end_user.name = f"{prenoms} {nom}".strip()

        # === Téléphones + email → EndUser ===
        # On accepte toutes les variantes (cellulaire, domicile, bureau, principal)
        # et on les stocke dans end_user.extra pour que la fiche sociétaire
        # puisse les afficher même quand le dossier existant n'en avait pas.
        tel_princ = _ctx_first([
            "ask_telephone1", "numero_de_telephone", "telephone", "num_telephone",
            "phone", "numero_telephone", "telephone_cellulaire",
            "telephone_principal", "numero_telephone_principal",
        ])
        if tel_princ:
            # Principal : on l'écrit toujours (update autorise à le changer)
            end_user.phone = tel_princ
        email = _ctx_first([
            "email_for_otp", "ask_email", "adresse_email", "email",
            "e_mail", "mail",
        ])
        extra = dict(end_user.extra or {})
        if email:
            extra["email"] = email
        for key, aliases in [
            ("telephone_domicile", ["telephone_du_domicile", "telephone_domicile", "tel_domicile"]),
            ("telephone_bureau",   ["telephone_du_bureau", "telephone_bureau", "tel_bureau"]),
            ("telephone_cellulaire", ["telephone_cellulaire", "cellulaire", "mobile"]),
            ("telephone2",         ["ask_telephone2", "telephone_secondaire", "telephone_2"]),
        ]:
            v = _ctx_first(aliases)
            if v:
                extra[key] = v
        end_user.extra = extra

        # === Données pro + champs additionnels → DonneesPro ===
        # Mapping utilisé pour les anciens parcours qui envoyaient des indices
        # numériques ("1"/"2"/"3"). Le nouveau schéma LLM envoie directement
        # les libellés résolus (ex. "Mlle", "Célibataire", "CNI"), d'où le
        # fallback sur la chaîne telle quelle.
        _CIVILITE_MAP = {"1": "M.", "2": "Mme", "3": "Mlle"}
        _SITUATION_MAP = {"1": "celibataire", "2": "marie", "3": "divorce", "4": "veuf"}
        _PIECE_MAP = {"1": "cni", "2": "passeport", "3": "attestation"}
        _CATEGORIE_MAP = {
            "1": "CADRE SUPERIEUR", "2": "CADRE", "3": "MAITRISE SUPERIEURE",
            "4": "M1-M2", "5": "EO",
        }

        def _norm_situation(val: str) -> str:
            v = (val or "").strip().lower().replace("(e)", "").replace("(ve)", "")
            if "cel" in v: return "celibataire"
            if "div" in v: return "divorce"
            if "veuf" in v or "veuv" in v: return "veuf"
            if "mari" in v or "union" in v: return "marie"
            return val

        extra_data = {}
        # Civilité (accepte "1"/"2"/"3" OU libellés "M.", "Mme", "Mlle")
        civ = _ctx_first(["ask_civilite", "civilite", "civility"])
        if civ:
            extra_data["civilite"] = _CIVILITE_MAP.get(civ, civ)

        date_n = _ctx_first([
            "ask_date_naissance", "date_de_naissance", "date_naissance",
            "birthday", "naissance_date",
        ])
        if date_n:
            extra_data["date_naissance"] = date_n

        lieu_n = _ctx_first([
            "ask_lieu_naissance", "lieu_de_naissance", "lieu_naissance",
            "ville_naissance", "birth_place",
        ])
        if lieu_n:
            extra_data["lieu_naissance"] = lieu_n

        type_p = _ctx_first([
            "ask_type_piece", "type_de_piece_identite", "type_piece", "type_piece_identite",
        ])
        if type_p:
            extra_data["type_piece"] = _PIECE_MAP.get(type_p, type_p.lower())

        num_p = _ctx_first([
            "ask_numero_piece", "numero_de_la_piece", "numero_piece", "numero_piece_identite",
            "cni_number", "piece_number",
        ])
        if num_p:
            extra_data["numero_piece"] = num_p

        dir_s = _ctx_first([
            "ask_direction_service", "direction_service", "direction", "service",
        ])
        if dir_s:
            extra_data["direction_service"] = dir_s

        bp = _ctx_first(["ask_boite_postale", "boite_postale", "bp"])
        if bp:
            extra_data["boite_postale_choisie"] = bp

        # Domicile (adresse physique)
        dom = _ctx_first([
            "ask_domicile", "domicile", "adresse_domicile", "adresse_de_domicile",
            "adresse", "lieu_residence",
        ])
        if dom:
            extra_data["domicile"] = dom

        # Exploitation / site
        expl = _ctx_first([
            "ask_exploitation", "exploitation_site", "exploitation", "site",
            "site_exploitation",
        ])
        if expl:
            extra_data["exploitation_site"] = expl

        # Date d'embauche
        date_emb = _ctx_first([
            "ask_date_embauche", "date_d_embauche", "date_embauche",
            "date_entree", "date_recrutement",
        ])
        if date_emb:
            extra_data["date_embauche"] = date_emb

        conj = _ctx_first([
            "ask_nom_conjoint", "nom_et_prenoms_du_conjoint", "nom_conjoint", "conjoint",
        ])
        if conj:
            extra_data["nom_conjoint"] = conj

        pers_prev = _ctx_first([
            "ask_nom_personne_prev", "personne_a_prevenir_en_cas_d_urgence",
            "personne_a_prevenir", "contact_urgence_nom",
        ])
        if pers_prev:
            extra_data["personne_a_prevenir"] = pers_prev

        c1 = _ctx_first(["ask_contact1_prev", "contact_urgence", "tel_urgence"])
        if c1:
            extra_data["contact_prevenir_1"] = c1
        c2 = _ctx_first(["ask_contact2_prev", "contact_urgence_2"])
        if c2:
            extra_data["contact_prevenir_2"] = c2

        ayant = _ctx_first([
            "ask_ayant_droit", "ayant_droit_declare", "ayants_droit", "ayant_droit",
        ])
        if ayant:
            extra_data["ayants_droit"] = ayant

        cat = _ctx_first([
            "ask_categorie", "categorie_professionnelle", "categorie",
        ])
        if cat:
            extra_data["categorie"] = _CATEGORIE_MAP.get(cat, cat)

        nom_m = _ctx_first([
            "ask_nom_mere", "nom_de_jeune_fille_de_la_mere", "nom_mere", "nom_jeune_fille_mere",
        ])
        if nom_m:
            extra_data["nom_mere"] = nom_m

        # Persiste : fonction (= profession), situation matri, extra JSON
        fonction = _ctx_first([
            "ask_profession", "ask_fonction", "fonction", "profession", "metier",
        ])
        situation_raw = _ctx_first([
            "ask_situation_matri", "situation_matrimoniale", "situation",
        ])
        situation = None
        if situation_raw:
            situation = _SITUATION_MAP.get(situation_raw, _norm_situation(situation_raw))

        # Résolution robuste des URLs de médias : on accepte les anciennes
        # clés (`recto_media_url`, …) ET on scanne le contexte pour trouver
        # toute clé `<step>_media_url` dont le code contient recto/verso/
        # signature. Permet de fonctionner avec n'importe quel parcours LLM
        # qui nomme ses steps `piece_identite_recto`, `photo_recto`, etc.
        def _find_media(hints: list[str]) -> Optional[str]:
            for h in hints:
                v = context.get(f"{h}_media_url") or context.get(h)
                if isinstance(v, str) and v.startswith(("http://", "https://", "/", "s3://")):
                    return v
            for key, val in context.items():
                if not isinstance(key, str) or not key.endswith("_media_url"):
                    continue
                low = key.lower()
                if any(h in low for h in hints) and isinstance(val, str) and val:
                    return val
            return None

        recto_url = _find_media(["recto"])
        verso_url = _find_media(["verso"])
        signature_url = _find_media(["signature"])

        # Signature : stockée dans extra_data pour affichage dans la fiche
        if signature_url:
            extra_data["signature_url"] = signature_url

        await dossier_service.upsert_donnees_pro(
            db, tenant.id, dossier,
            fonction=fonction,
            situation_familiale=situation,
            extra=extra_data,
        )

        # ── Attache les pièces d'identité (recto + verso) au dossier ──
        from app.models import PieceFace, PieceIdentite, PieceType
        piece_type_str = extra_data.get("type_piece", "cni")
        try:
            ptype = PieceType.cni_uemoa
            if piece_type_str == "passeport":
                ptype = PieceType.passeport
            elif piece_type_str == "attestation":
                ptype = PieceType.carte_resident
        except Exception:
            ptype = PieceType.cni_uemoa

        for face_name, media_url, ocr_key in [
            ("recto", recto_url, "ocr_recto"),
            ("verso", verso_url, "ocr_verso"),
        ]:
            if not media_url:
                continue
            ocr_data = context.get(ocr_key) or {}
            ocr_conf = float(ocr_data.get("confidence") or 0.0)
            face = PieceFace.recto if face_name == "recto" else PieceFace.verso
            piece = PieceIdentite(
                tenant_id=tenant.id,
                dossier_id=dossier.id,
                piece_type=ptype,
                face=face,
                storage_key=media_url,
                mime_type="image/jpeg",
                ocr_status="completed" if ocr_data else "skipped",
                ocr_data=ocr_data,
                mrz_data=(ocr_data.get("mrz") or {}) if face == PieceFace.verso else {},
                ocr_confidence=ocr_conf if ocr_conf > 0 else None,
            )
            db.add(piece)
            logger.info("Pièce attachée : %s (%s) — %s", face_name, ptype.value, media_url)

        if signature_url:
            logger.info(
                "Signature attachée au dossier %s : %s",
                dossier.dossier_number, signature_url,
            )

        # F-06 — Si un écart saisie ↔ OCR a été détecté par
        # verify_user_data_vs_ocr, on force la revue humaine avant validation
        # finale. La saisie de l'usager reste la source de vérité pour tous les
        # champs texte, et l'agent en back-office arbitre.
        mismatches = int(context.get("data_match_mismatches") or 0)
        closes = int(context.get("data_match_closes") or 0)
        if mismatches > 0 or closes > 0:
            dossier.priority_review = True
            reason = (
                f"Écart saisie utilisateur ↔ OCR "
                f"({mismatches} champ(s) différent(s), {closes} champ(s) proche(s)). "
                f"Détail : {context.get('data_match_summary') or 'n/a'}"
            )
            dossier.priority_reason = reason[:255]
            logger.info(
                "Dossier %s marqué priority_review (F-06) : %d mismatch, %d close",
                dossier.dossier_number, mismatches, closes,
            )

        # F-03 (mitigation) — un dossier avec des marqueurs de contrefaçon
        # remontés par ocr_guardrails.detect_counterfeit_markers (SPECIMEN,
        # numéro trivial, etc.) est bloqué en revue humaine, quel que soit
        # l'état des autres contrôles. En attendant l'intégration d'un
        # référentiel officiel (voir docs/DECISION_F03_referentiel.md),
        # cette heuristique évite au moins qu'une pièce marquée « SPECIMEN »
        # ne passe silencieusement.
        counterfeit_markers: list = []
        for face_key in ("ocr_recto", "ocr_verso"):
            face_data = context.get(face_key) or {}
            markers = face_data.get("_counterfeit_markers") or []
            counterfeit_markers.extend(markers)
        if counterfeit_markers:
            dossier.priority_review = True
            reason_f03 = (
                "Marqueurs de contrefaçon détectés sur la pièce : "
                + ", ".join(counterfeit_markers[:3])
            )
            # Si un motif F-06 était déjà positionné, on préfère garder le
            # motif F-03 qui est plus grave (potentielle fraude).
            dossier.priority_reason = reason_f03[:255]
            logger.warning(
                "Dossier %s marqué priority_review (F-03) : %s",
                dossier.dossier_number, counterfeit_markers,
            )

        # F-01 (Vague 2) — un dossier dont l'OCR a détecté une injection de
        # prompt dans le texte de la pièce est bloqué en revue humaine et
        # priority_reason porte explicitement ce motif. Ce motif prime sur
        # F-03 (tentative d'attaque active > document simplement fabriqué).
        injection_markers: list = []
        for face_key in ("ocr_recto", "ocr_verso"):
            face_data = context.get(face_key) or {}
            if face_data.get("_prompt_injection_detected"):
                injection_markers.extend(face_data.get("_prompt_injection_markers") or [])
        if injection_markers:
            dossier.priority_review = True
            reason_f01 = (
                "Injection de prompt détectée dans le texte OCR de la pièce : "
                + ", ".join(injection_markers[:3])
            )
            dossier.priority_reason = reason_f01[:255]
            logger.error(
                "Dossier %s marqué priority_review (F-01) — TENTATIVE D'ATTAQUE : %s",
                dossier.dossier_number, injection_markers,
            )

        # Soumission (status → soumis, submitted_at = now)
        await dossier_service.submit_dossier(db, dossier)

        # Pas d'attribution automatique du N° sociétaire : c'est l'agent MA2E
        # qui l'attribue à la validation finale (cohérent avec le message de fin
        # qui dit "vous recevrez votre N° sociétaire par email à la validation").
        numero = None

        # Enregistrement des consentements (ARTCI + certification finale)
        channel_value = context.get("_channel") or conversation.channel.value
        phone_or_id = end_user.phone or end_user.telegram_id
        try:
            await consent_service.record_consent(
                db, tenant.id, end_user.id, dossier.id,
                ConsentGate.artci, ConsentDecision.accepte,
                channel=channel_value, ip_or_phone=phone_or_id,
            )
        except Exception as e:
            logger.warning("Enregistrement consentement ARTCI échoué : %s", e)
        try:
            await consent_service.record_consent(
                db, tenant.id, end_user.id, dossier.id,
                ConsentGate.certification_finale, ConsentDecision.accepte,
                channel=channel_value, ip_or_phone=phone_or_id,
            )
        except Exception as e:
            logger.warning("Enregistrement consentement certification échoué : %s", e)

        await db.flush()
        msg = (
            f"✅ Mise à jour du dossier *{dossier.dossier_number}* enregistrée."
            if update_mode
            else f"✅ Dossier *{dossier.dossier_number}* enregistré."
        )
        return ActionResult(
            extra_context={
                "numero_societaire": numero or "",  # vide jusqu'à validation agent
                "dossier_id": str(dossier.id),
                "dossier_number": dossier.dossier_number,
                "dossier_created": True,
                # Libère le flag update pour le prochain parcours
                "_update_mode": False,
            },
            message=msg,
        )
    except Exception as e:
        logger.exception("create_real_dossier a échoué : %s", e)
        return ActionResult(
            branch_key="error",
            message="Erreur lors de la création du dossier. Notre support a été notifié.",
        )


# ----------------------------------------------------------------------
# 5. Revue manuelle (cas OCR faible / doublon souple)
# ----------------------------------------------------------------------
@workflow_action(
    "queue_for_manual_review",
    display_label="Mettre le dossier en revue manuelle",
    description="Marque le dossier en priority_review pour examen humain (cas OCR faible / doublon souple).",
    category="Création dossier",
)
async def queue_for_manual_review(
    db: AsyncSession,
    context: dict,
    last_input: Optional[str],
) -> ActionResult:
    """Marque le dossier en priority_review si on est en mode réel."""
    if context.get("_simulate") is True or not context.get("dossier_id"):
        return ActionResult(
            message=(
                "📋 Votre dossier va être revu par un agent humain. "
                "Vous recevrez une notification sous 48h."
            ),
            extra_context={"manual_review_queued": True},
        )

    try:
        dossier = (
            await db.execute(select(Dossier).where(Dossier.id == UUID(context["dossier_id"])))
        ).scalar_one_or_none()
        if dossier:
            dossier.priority_review = True
            dossier.priority_reason = "OCR faible — revue manuelle requise"
            await db.flush()
    except Exception as e:
        logger.warning("Mise en revue manuelle échouée : %s", e)

    return ActionResult(
        message=(
            "📋 Votre dossier va être revu par un agent humain. "
            "Vous recevrez une notification sous 48h."
        ),
        extra_context={"manual_review_queued": True},
    )


# ----------------------------------------------------------------------
# 6. OTP email — envoi du code
# ----------------------------------------------------------------------
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


@workflow_action(
    "send_email_otp",
    service="email_otp",
    branches=["disabled", "invalid_email", "rate_limited", "error"],
    branch_labels={
        "disabled": "Service OTP désactivé",
        "invalid_email": "Adresse email invalide",
        "rate_limited": "Trop de demandes (anti-spam)",
        "error": "Erreur d'envoi",
    },
    display_label="Envoyer le code OTP par email",
    description="Génère un code à 6 chiffres et l'envoie par email pour vérifier l'adresse du sociétaire.",
    category="OTP Email",
)
async def send_email_otp(
    db: AsyncSession,
    context: dict,
    last_input: Optional[str],
) -> ActionResult:
    """Génère un code OTP 6 chiffres et l'envoie à l'email saisi (last_input).

    Branches : `disabled`, `invalid_email`, `rate_limited`, `error`.
    """
    if not await _service_enabled(db, context, "email_otp_enabled"):
        return ActionResult(branch_key="disabled")

    from app.services import otp_service

    email = (last_input or context.get("ask_email") or "").strip().lower()
    if not email or not EMAIL_REGEX.match(email):
        return ActionResult(
            branch_key="invalid_email",
            message="⚠️ Adresse email invalide. Merci de saisir une adresse correcte (ex : prenom.nom@domaine.ci).",
        )

    if context.get("_simulate") is True:
        return ActionResult(
            extra_context={"email_for_otp": email, "otp_sent": True},
            message=f"📧 Code OTP envoyé à {email} (simulateur).",
        )

    tenant_id = _tenant_id_from(context)
    if not tenant_id:
        return ActionResult(branch_key="error", message="Erreur interne : tenant non identifié.")

    try:
        res = await otp_service.request_otp(db, tenant_id=tenant_id, email=email)
    except Exception as e:
        logger.exception("OTP request a échoué : %s", e)
        return ActionResult(branch_key="error", message="Erreur lors de l'envoi du code.")

    if res.get("rate_limited"):
        return ActionResult(
            branch_key="rate_limited",
            message=res.get("reason") or "Trop de demandes — réessayez plus tard.",
        )
    if not res.get("issued"):
        return ActionResult(branch_key="error", message="Impossible d'émettre le code.")

    return ActionResult(
        extra_context={"email_for_otp": email, "otp_sent": True},
        message=f"📧 Un code à 6 chiffres a été envoyé à *{email}*. Saisissez-le ci-dessous.",
    )


@workflow_action(
    "verify_email_otp",
    service="email_otp",
    branches=["disabled", "invalid_code", "max_attempts", "expired", "error"],
    branch_labels={
        "disabled": "Service OTP désactivé",
        "invalid_code": "Code incorrect",
        "max_attempts": "Trop de tentatives",
        "expired": "Code expiré",
        "error": "Erreur de vérification",
    },
    display_label="Vérifier le code OTP saisi",
    description="Vérifie le code OTP saisi par le sociétaire (Redis, 3 essais max).",
    category="OTP Email",
)
async def verify_email_otp(
    db: AsyncSession,
    context: dict,
    last_input: Optional[str],
) -> ActionResult:
    """Vérifie le code OTP saisi (last_input).

    Branches : `disabled`, `invalid_code`, `max_attempts`, `expired`, `error`.
    """
    if not await _service_enabled(db, context, "email_otp_enabled"):
        return ActionResult(branch_key="disabled")

    from app.services import otp_service

    code = (last_input or "").strip()
    email = (context.get("email_for_otp") or "").strip().lower()

    if not email:
        return ActionResult(branch_key="error", message="Aucun email associé. Reprenez la saisie de l'email.")

    if context.get("_simulate") is True:
        if code == "000000":
            return ActionResult(extra_context={"email_verified": True}, message="✅ Code vérifié.")
        return ActionResult(branch_key="invalid_code", message="Code incorrect (mode simulateur : tapez 000000).")

    tenant_id = _tenant_id_from(context)
    if not tenant_id:
        return ActionResult(branch_key="error", message="Erreur interne : tenant non identifié.")

    try:
        res = await otp_service.verify_otp(db, tenant_id=tenant_id, email=email, code=code)
    except Exception as e:
        logger.exception("OTP verify a échoué : %s", e)
        return ActionResult(branch_key="error", message="Erreur lors de la vérification.")

    if res.get("ok"):
        return ActionResult(
            extra_context={"email_verified": True, "email_verified_address": email},
            message=f"✅ Email *{email}* vérifié.",
        )

    if res.get("attempts_remaining", 0) == 0:
        return ActionResult(
            branch_key="max_attempts",
            message=res.get("reason") or "Trop de tentatives. Demandez un nouveau code.",
        )

    return ActionResult(
        branch_key="invalid_code",
        message=f"❌ {res.get('reason') or 'Code incorrect'}. Réessayez.",
    )


# ----------------------------------------------------------------------
# 7. Notification de fin de parcours
# ----------------------------------------------------------------------
@workflow_action(
    "notify_end_of_enrolment",
    service="notifications_end",
    branches=["disabled"],
    branch_labels={"disabled": "Service notifications désactivé"},
    display_label="Envoyer la notification de fin d'inscription",
    description="Envoie le récap final (N° sociétaire + dossier) sur WhatsApp + email.",
    category="Notification",
)
async def notify_end_of_enrolment(
    db: AsyncSession,
    context: dict,
    last_input: Optional[str],
) -> ActionResult:
    """Envoie le récap final au sociétaire sur son canal d'origine + email.

    Branches : `disabled`.
    Ne bloque jamais le parcours : si la notification échoue, on log et on
    continue (le sociétaire voit quand même le message du step suivant).
    """
    if not await _service_enabled(db, context, "notifications_end_enabled"):
        return ActionResult(branch_key="disabled")

    if context.get("_simulate") is True:
        return ActionResult(message="📨 Notification fin de parcours envoyée (simulateur).")

    from app.services import notifications

    tenant_id = _tenant_id_from(context)
    end_user_id = _end_user_id_from(context)
    if not tenant_id or not end_user_id:
        return ActionResult()  # silent — ne pas casser le parcours

    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
    end_user = (await db.execute(select(EndUser).where(EndUser.id == end_user_id))).scalar_one_or_none()
    if not tenant or not end_user:
        return ActionResult()

    numero = context.get("numero_societaire") or "—"
    dossier_number = context.get("dossier_number") or "—"

    text = (
        f"🎉 *Inscription validée !*\n\n"
        f"• N° sociétaire : *{numero}*\n"
        f"• Dossier : *{dossier_number}*\n\n"
        f"Vous recevrez une confirmation par email dans quelques minutes. "
        f"Bienvenue chez MA2E !"
    )

    try:
        await notifications.notify_end_user(
            db, tenant=tenant, end_user=end_user, text=text,
            also_send_email=True,
            email_subject="Bienvenue chez MA2E — Inscription validée",
        )
    except Exception as e:
        logger.warning("notify_end_of_enrolment a échoué : %s", e)

    return ActionResult()
