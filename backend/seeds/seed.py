"""Seed initial pour la démo MA2E.

Crée :
- Tenant unique MA2E (la plateforme est mono-tenant — voir core/tenancy.py)
- Texte de consentement ARTCI conforme loi 2013-450 art.16 (versionné, hashé)
- Liste fermée des employeurs (SODECI, CIE, GS2E, SMB, SDE, etc.)
- 3 comptes utilisateurs (super_admin GS2E, tenant_admin MA2E, agent MA2E)
  → tous rattachés au tenant MA2E

Usage (depuis le dossier backend/) :
    python seeds/seed.py

Ou depuis la racine du projet :
    python backend/seeds/seed.py
"""
import asyncio
import hashlib
import os
import sys
from pathlib import Path

# Ce fichier vit dans backend/seeds/ → parents[1] = backend/
BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import load_dotenv
load_dotenv(BACKEND_ROOT / ".env")

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import hash_password
from app.models import (
    ConsentGate,
    CustomRole,
    Employeur,
    Tenant,
    TenantChannel,
    TexteConsentement,
    User,
    UserCustomRole,
    UserRole,
    Workflow,
    WorkflowStep,
    WorkflowStepType,
)
from app.services import rbac_service, workflow_template_service


# ----------------------------------------------------------------------
# Texte ARTCI v1.0 — Conforme loi n°2013-450 art.16
# ----------------------------------------------------------------------
ARTCI_CONSENT_V1 = """*Protection de vos données — Loi 2013-450*

MA2E collecte vos données d'identité, professionnelles et votre pièce d'identité pour gérer votre adhésion à la mutuelle.

🔐 Données chiffrées · Conservation : adhésion + 5 ans
✅ Vos droits (accès, rectification, effacement) : tapez *DROITS*
📋 Recours ARTCI : www.artci.ci

_En acceptant, vous confirmez avoir lu ces mentions._"""


OCR_CONSENT_V1 = """Je confirme que les données extraites automatiquement de ma pièce d'identité sont correctes et m'engage sur leur exactitude.

Aucune correction additionnelle n'est requise."""


CERTIFICATION_V1 = """Je certifie sur l'honneur l'exactitude de l'ensemble des informations fournies dans ce dossier.

Je suis informé(e) que toute fausse déclaration peut entraîner le rejet de mon adhésion et engage ma responsabilité conformément à la loi n°2013-546 sur les transactions électroniques."""


# ----------------------------------------------------------------------
# Tenants
# ----------------------------------------------------------------------
MA2E_BRANDING = {
    "bot_name": "MA2E Assistant",
    "color": "#1a5490",
    "logo": None,
    "welcome_message": "Bienvenue sur la plateforme digitale MA2E",
    "official_name": "Mutuelle des Agents de l'Eau et de l'Électricité",
    "agence_address": "Plateau, Abidjan, Côte d'Ivoire",
    "contact_phone": "+225 27 20 XX XX XX",
    "support_email": "support@ma2e.ci",
}

MA2E_LLM = {
    "model": settings.groq_model,
    "temperature": 0.2,
    "system_prompt": (
        "Tu es l'assistant officiel d'identification de MA2E. "
        "Tu guides les sociétaires dans leur parcours d'enrôlement digital. "
        "Tu réponds toujours en français, de manière professionnelle et bienveillante."
    ),
}


EMPLOYEURS = [
    ("SODECI", "Société de Distribution d'Eau de Côte d'Ivoire"),
    ("CIE", "Compagnie Ivoirienne d'Électricité"),
    ("GS2E", "Groupement de Services Eau et Électricité"),
    ("SMB", "Société Multinationale de Bitumes"),
    ("SDE", "Sénégalaise des Eaux"),
    ("CIPREL", "Compagnie Ivoirienne de Production d'Électricité"),
    ("ERANOVE", "Eranove Holding"),
    ("AUTRE", "Autre société du périmètre"),
]


def _hash(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


async def seed():
    engine = create_async_engine(settings.database_url, echo=False)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as db:
        # ============================================================
        #  TENANT MA2E (principal)
        # ============================================================
        ma2e = (await db.execute(select(Tenant).where(Tenant.slug == "ma2e"))).scalar_one_or_none()
        if not ma2e:
            ma2e = Tenant(
                slug="ma2e",
                name="MA2E",
                description="Mutuelle des Agents de l'Eau et de l'Électricité — Tenant principal",
                branding=MA2E_BRANDING,
                menu_config={},
                llm_config=MA2E_LLM,
            )
            db.add(ma2e)
            await db.flush()
            print(f"  ✅ Tenant MA2E créé : {ma2e.id}")
        else:
            print(f"  ↻  Tenant MA2E existe : {ma2e.id}")

        # ============================================================
        #  TEXTES DE CONSENTEMENT VERSIONNÉS (PRD §10.4)
        # ============================================================
        for gate, title, body, ref in [
            (ConsentGate.artci, "Consentement ARTCI", ARTCI_CONSENT_V1, "Loi 2013-450 art.16"),
            (ConsentGate.ocr_validation, "Validation OCR", OCR_CONSENT_V1, "Art.5 - exactitude"),
            (ConsentGate.certification_finale, "Certification finale", CERTIFICATION_V1, "Loi 2013-546"),
        ]:
            existing = (
                await db.execute(
                    select(TexteConsentement).where(
                        TexteConsentement.tenant_id == ma2e.id,
                        TexteConsentement.gate == gate,
                        TexteConsentement.version == "1.0",
                    )
                )
            ).scalar_one_or_none()
            if existing:
                existing.title = title
                existing.body = body
                existing.legal_reference = ref
                existing.content_hash = _hash(body)
                print(f"  ↻  Texte consentement mis à jour : {gate.value} v1.0")
            else:
                tc = TexteConsentement(
                    tenant_id=ma2e.id,
                    gate=gate,
                    version="1.0",
                    title=title,
                    body=body,
                    legal_reference=ref,
                    content_hash=_hash(body),
                    is_current=True,
                )
                db.add(tc)
                print(f"  ✅ Texte consentement créé : {gate.value} v1.0")

        # ============================================================
        #  EMPLOYEURS (liste fermée)
        # ============================================================
        for code, name in EMPLOYEURS:
            existing = (
                await db.execute(
                    select(Employeur).where(Employeur.tenant_id == ma2e.id, Employeur.code == code)
                )
            ).scalar_one_or_none()
            if not existing:
                db.add(Employeur(tenant_id=ma2e.id, code=code, name=name, is_active=True))
        print(f"  ✅ {len(EMPLOYEURS)} employeurs référencés")

        # ============================================================
        #  UTILISATEURS — tous rattachés au tenant MA2E unique
        # ============================================================
        for email, pwd, name, role, tenant_id in [
            ("admin@gs2e.ci", "admin123", "Super Admin GS2E", UserRole.super_admin, ma2e.id),
            ("admin@ma2e.ci", "ma2e123", "Konaté Bakary (Admin MA2E)", UserRole.tenant_admin, ma2e.id),
            ("agent@ma2e.ci", "agent123", "Akissi Brou (Gestionnaire MA2E)", UserRole.agent, ma2e.id),
        ]:
            existing = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
            if not existing:
                db.add(User(
                    email=email, password_hash=hash_password(pwd),
                    name=name, role=role, tenant_id=tenant_id,
                ))
                print(f"  ✅ Utilisateur : {email} / {pwd} ({role.value})")

        await db.commit()

        # ============================================================
        #  RÔLES MÉTIER RBAC (US-03 / US-04)
        # ============================================================
        created = await rbac_service.seed_default_roles(db, ma2e.id)
        await db.commit()
        if created > 0:
            print(f"  ✅ {created} rôle(s) métier créés (Agent Validateur, Superviseur, Lecteur, IT)")
        else:
            print("  ↻  Rôles métier déjà présents")

        # Assigne « Agent Validateur » à agent@ma2e.ci par défaut
        # (admins ont toutes les permissions sans rôle métier explicite)
        agent_user = (await db.execute(
            select(User).where(User.email == "agent@ma2e.ci")
        )).scalar_one_or_none()
        agent_role = (await db.execute(
            select(CustomRole).where(
                CustomRole.tenant_id == ma2e.id,
                CustomRole.name == "Agent Validateur",
            )
        )).scalar_one_or_none()
        if agent_user and agent_role:
            already = (await db.execute(
                select(UserCustomRole).where(
                    UserCustomRole.user_id == agent_user.id,
                    UserCustomRole.custom_role_id == agent_role.id,
                )
            )).scalar_one_or_none()
            if not already:
                db.add(UserCustomRole(
                    user_id=agent_user.id,
                    custom_role_id=agent_role.id,
                    granted_by=None,
                ))
                await db.commit()
                print(f"  ✅ Rôle « Agent Validateur » attribué à {agent_user.email}")
            else:
                print(f"  ↻  Rôle déjà attribué à {agent_user.email}")

        # ============================================================
        #  WORKFLOWS MA2E par défaut (4 parcours conversationnels)
        # ============================================================
        await _seed_default_workflow(db, ma2e.id)
        await _seed_consultation_workflow(db, ma2e.id)
        await _seed_modification_workflow(db, ma2e.id)
        await _seed_chat_libre_workflow(db, ma2e.id)
        await db.commit()

        # ============================================================
        #  CHANNELS
        # ============================================================
        # WhatsApp Cloud API (canal principal)
        whatsapp_phone_id = os.getenv("WHATSAPP_PHONE_ID_MA2E")
        await _seed_channel(
            db, ma2e.id, "whatsapp",
            whatsapp_phone_id, "MA2E WhatsApp",
            credentials={
                "access_token": os.getenv("WHATSAPP_ACCESS_TOKEN_MA2E", ""),
                # phone_number_id est requis par l'API Meta Cloud pour poster
                # les messages sortants. On duplique l'external_id ici pour
                # que notifications._send_whatsapp trouve tout dans creds.
                "phone_number_id": whatsapp_phone_id or "",
            },
        )
        # Web chat (canal secondaire, intégré à la plateforme)
        await _seed_channel(
            db, ma2e.id, "web",
            "ma2e", "MA2E Web Chat",
            credentials={},
        )
        await db.commit()

        print()
        print("=" * 70)
        print("  🎉 SEED COMPLET — MA2E Plateforme Digitale d'Identification")
        print("=" * 70)
        print(f"\n  Tenant ID : {ma2e.id}\n")
        print("  Comptes de connexion :")
        print("  ┌─────────────────────────────────────────────────────────┐")
        print("  │ Super Admin GS2E   admin@gs2e.ci    /  admin123         │")
        print("  │ Admin MA2E         admin@ma2e.ci    /  ma2e123          │")
        print("  │ Agent MA2E         agent@ma2e.ci    /  agent123         │")
        print("  └─────────────────────────────────────────────────────────┘")
        print()

    await engine.dispose()


async def _seed_default_workflow(db, tenant_id):
    """Workflow MA2E + contenus des templates de chaque step.

    Idempotent :
    - Crée le workflow s'il n'existe pas, sinon **migre** les steps existants
      pour utiliser l'auto-dérivation `workflow.<step_code>`
    - Upsert le contenu du template de chaque step de type message/question
      (pas d'écrasement silencieux : si l'utilisateur a personnalisé un template,
      l'upsert idempotent ne re-écrit que si `content == content` est faux —
      donc on garde la personnalisation côté admin)
    """
    from sqlalchemy.orm import selectinload

    # (code, label, type, action_name, next_step_code, branches, default_content)
    # template_code est laissé à None → le moteur dérive `workflow.<step_code>`
    steps_def = [
        ("welcome", "Menu principal", WorkflowStepType.question,
         None, "ask_consent_artci",
         {"1": "ask_consent_artci", "2": "handoff_consultation", "3": "handoff_modification", "4": "handoff_chat"},
         "👋 *Bienvenue chez MA2E !*\n\nJe suis {assistant_name}, votre assistante d'identification.\n\n*Que souhaitez-vous faire ?*\n\n1️⃣ *M'inscrire* (nouveau sociétaire)\n2️⃣ *Consulter* mon dossier\n3️⃣ *Modifier* mes informations\n4️⃣ *Poser une question libre* (FAQ)\n\n_Répondez par 1, 2, 3 ou 4._"),

        ("ask_consent_artci", "Demande du consentement ARTCI",
         WorkflowStepType.question, None, "ask_matricule",
         {"on_refused": "consent_refused"},
         "🔐 *Protection de vos données — Loi 2013-450 ARTCI*\n\nMA2E collecte vos données d'identité, professionnelles et votre pièce d'identité pour gérer votre adhésion.\n\n• Données chiffrées · Conservation : adhésion + 5 ans\n• Vos droits : tapez *DROITS*\n• Recours ARTCI : www.artci.ci\n\n*Acceptez-vous ?* (1 = oui, 2 = non)"),

        ("consent_refused", "Consentement refusé — sortie", WorkflowStepType.message,
         None, None, {},
         "Sans votre consentement, nous ne pouvons pas poursuivre l'inscription.\n\nPour toute question : {support_email} · {support_phone}\nVos droits : tapez *DROITS*."),

        ("ask_matricule", "Saisie du matricule", WorkflowStepType.question,
         None, "verify_matricule", {"on_invalid": "ask_matricule"},
         "Merci ! Pour vous identifier, saisissez votre *matricule employeur* (6 à 10 caractères alphanumériques)."),

        ("verify_matricule", "Vérification matricule (référentiel ERANOVE)",
         WorkflowStepType.action, "verify_matricule_referentiel",
         "ask_employeur",
         {"not_found": "ask_matricule", "anonymous": "anonyme_flow"},
         None),

        ("ask_employeur", "Choix de l'employeur", WorkflowStepType.question,
         None, "ask_fonction", {"on_invalid": "ask_employeur"},
         "Quel est votre *employeur* ?\n\n1️⃣ SODECI\n2️⃣ CIE\n3️⃣ GS2E\n4️⃣ SMB\n5️⃣ CIPREL\n6️⃣ ERANOVE\n7️⃣ Autre"),

        ("ask_fonction", "Fonction du sociétaire", WorkflowStepType.question,
         None, "ask_cni_recto", {},
         "Quelle est votre *fonction* au sein de l'entreprise ?"),

        ("ask_cni_recto", "Photo CNI recto", WorkflowStepType.question,
         None, "ask_cni_verso", {"on_invalid": "ask_cni_recto"},
         "📷 Envoyez-moi maintenant une *photo nette du recto* de votre pièce d'identité (CNI ou passeport)."),

        ("ask_cni_verso", "Photo CNI verso", WorkflowStepType.question,
         None, "ocr_extract", {"on_invalid": "ask_cni_verso"},
         "Parfait. À présent, le *verso* de votre pièce d'identité, s'il vous plaît."),

        ("ocr_extract", "Extraction OCR Mindee / mock", WorkflowStepType.action,
         "ocr_extract_cni", "verify_data_vs_ocr", {"low_score": "manual_review"},
         None),

        # F-06 — compare saisie utilisateur ↔ OCR AVANT d'afficher confirm_ocr.
        # match           → confirm_ocr (validation express)
        # partial_match   → confirm_ocr (l'usager voit les 2 côtés)
        # mismatch (≥3 champs) → manual_review (arbitrage humain forcé)
        ("verify_data_vs_ocr",
         "Comparaison saisie ↔ OCR (F-06)",
         WorkflowStepType.action, "verify_user_data_vs_ocr",
         "confirm_ocr",
         {"match": "confirm_ocr", "partial_match": "confirm_ocr",
          "mismatch": "manual_review"},
         None),

        ("confirm_ocr", "Confirmation données OCR (Gate 2)",
         WorkflowStepType.question, None, "anti_doublon_check",
         {"on_correction": "ask_cni_recto"},
         "🔎 *Confrontation saisie ↔ pièce d'identité :*\n\n{data_match_summary}\n\n*Ces informations sont-elles correctes ?*\n\n1️⃣ Oui, je confirme ma saisie\n2️⃣ Non, je veux corriger"),

        ("anti_doublon_check", "Vérification anti-doublon (US-36)",
         WorkflowStepType.action, "check_duplicates", "final_certification",
         {"duplicate": "duplicate_detected"},
         None),

        ("duplicate_detected", "Sortie : doublon détecté", WorkflowStepType.message,
         None, None, {},
         "⚠️ Un dossier existe déjà pour ce matricule.\n\nPour le consulter ou le mettre à jour, tapez *STATUT* ou contactez {support_email}."),

        ("final_certification", "Certification finale (Gate 3)",
         WorkflowStepType.question, None, "create_dossier",
         {"on_refused": "consent_refused"},
         "Avant la création de votre dossier, *je certifie sur l'honneur* l'exactitude de l'ensemble des informations fournies.\n\nToute fausse déclaration peut entraîner le rejet de l'adhésion (loi 2013-546).\n\n*Confirmez-vous ?* (1 = oui, 2 = annuler)"),

        ("create_dossier", "Création du dossier validé", WorkflowStepType.action,
         "create_validated_dossier", "completion", {}, None),

        ("manual_review", "OCR faible — basculement vers revue manuelle",
         WorkflowStepType.action, "queue_for_manual_review", "completion", {}, None),

        ("anonyme_flow", "Sociétaire anonyme (US-33 alternative)",
         WorkflowStepType.message, None, None, {},
         "Votre matricule n'a pas été reconnu dans notre référentiel.\n\nMerci de contacter le support MA2E ({support_phone} · {support_email}) pour finaliser votre inscription manuellement."),

        ("completion", "Message de fin — numéro sociétaire attribué",
         WorkflowStepType.message, None, None, {},
         "🎉 *Inscription validée !*\n\nVotre numéro sociétaire : *{numero_societaire}*\n\nVous recevrez bientôt un email de confirmation. Bienvenue chez MA2E !"),

        # ===== Handoffs depuis le menu welcome vers les 3 autres parcours =====
        ("handoff_consultation", "Bascule vers consultation",
         WorkflowStepType.message, None, None, {},
         "🔍 *Consultation de votre dossier*\n\nSaisissez votre *matricule employeur* pour que je retrouve votre dossier."),

        ("handoff_modification", "Bascule vers modification",
         WorkflowStepType.message, None, None, {},
         "✏️ *Mise à jour de vos informations*\n\nPour modifier vos données, saisissez d'abord votre *matricule employeur*."),

        ("handoff_chat", "Bascule vers chat libre",
         WorkflowStepType.message, None, None, {},
         "💬 *Espace questions libres*\n\nPosez-moi votre question sur MA2E (adhésion, prestations, garanties…).\nTapez *MENU* à tout moment pour revenir au choix initial."),
    ]

    # ---------- Workflow lui-même : create-or-migrate ----------
    existing = (
        await db.execute(
            select(Workflow)
            .options(selectinload(Workflow.steps))
            .where(Workflow.name == "Inscription sociétaire MA2E")
        )
    ).scalar_one_or_none()

    if existing is None:
        wf = Workflow(
            name="Inscription sociétaire MA2E",
            description=(
                "Parcours d'inscription conversationnel WhatsApp/Web — du consentement ARTCI "
                "à la création du dossier validé. Conforme loi 2013-450."
            ),
            active=True,
            version=1,
            start_step_code="welcome",
        )
        db.add(wf)
        await db.flush()

        position = 0
        for code, label, step_type, action_name, next_code, branches, _content in steps_def:
            position += 10
            db.add(WorkflowStep(
                workflow_id=wf.id,
                code=code,
                label=label,
                type=step_type,
                template_code=None,  # auto-dérivé → workflow.<code>
                action_name=action_name,
                next_step_code=next_code,
                branches=branches,
                position=position,
            ))
        print(f"  ✅ Workflow MA2E créé avec {len(steps_def)} étapes (actif)")
    else:
        # Migration : on remet template_code=None pour basculer sur l'auto-dérivation
        migrated = 0
        for step in existing.steps:
            if step.template_code is not None:
                step.template_code = None
                migrated += 1
        if migrated:
            print(f"  🔄 Workflow MA2E : {migrated} étapes migrées vers auto-dérivation (workflow.<code>)")
        else:
            print(f"  ↻  Workflow MA2E déjà à jour ({len(existing.steps)} étapes)")

    await db.flush()

    # ---------- Templates : upsert idempotent du contenu par défaut ----------
    inserted = 0
    for code, _label, step_type, _action, _next, _branches, content in steps_def:
        if content is None:
            continue  # type=action sans message
        template_code = workflow_template_service.derive_code(code)
        # Vérifie l'existence pour ne pas écraser une personnalisation
        existing_tpl = await workflow_template_service.get_content(db, tenant_id, template_code)
        if existing_tpl is not None:
            continue  # déjà personnalisé ou seedé — on ne touche pas
        await workflow_template_service.upsert(
            db, tenant_id, template_code, content,
        )
        inserted += 1
    if inserted:
        print(f"  ✅ {inserted} contenu(s) de template workflow seedés")
    else:
        print(f"  ↻  Contenus de template workflow déjà tous présents")


# ============================================================
# Helper générique pour les 3 autres parcours
# ============================================================
async def _seed_workflow(
    db,
    tenant_id,
    *,
    name: str,
    description: str,
    start_step_code: str,
    steps_def: list,
    active: bool = False,
):
    """Crée un workflow + seed ses templates. Idempotent."""
    from sqlalchemy.orm import selectinload

    existing = (
        await db.execute(
            select(Workflow)
            .options(selectinload(Workflow.steps))
            .where(Workflow.name == name)
        )
    ).scalar_one_or_none()

    if existing is None:
        wf = Workflow(
            name=name,
            description=description,
            active=active,
            version=1,
            start_step_code=start_step_code,
        )
        db.add(wf)
        await db.flush()
        position = 0
        for code, label, step_type, action_name, next_code, branches, _content in steps_def:
            position += 10
            db.add(WorkflowStep(
                workflow_id=wf.id,
                code=code,
                label=label,
                type=step_type,
                template_code=None,
                action_name=action_name,
                next_step_code=next_code,
                branches=branches,
                position=position,
            ))
        print(f"  ✅ Workflow « {name} » créé avec {len(steps_def)} étapes")
    else:
        print(f"  ↻  Workflow « {name} » déjà présent ({len(existing.steps)} étapes)")

    await db.flush()

    inserted = 0
    for code, _label, _type, _action, _next, _branches, content in steps_def:
        if content is None:
            continue
        template_code = workflow_template_service.derive_code(code)
        existing_tpl = await workflow_template_service.get_content(db, tenant_id, template_code)
        if existing_tpl is not None:
            continue
        await workflow_template_service.upsert(db, tenant_id, template_code, content)
        inserted += 1
    if inserted:
        print(f"     ↳ {inserted} template(s) seedé(s)")


async def _seed_consultation_workflow(db, tenant_id):
    """Parcours « Consultation de dossier » : le sociétaire vérifie l'état."""
    steps_def = [
        ("consult_welcome", "Accueil consultation", WorkflowStepType.message,
         None, "consult_ask_matricule", {},
         "🔍 *Consultation de votre dossier*\n\nJe vais vous donner l'état actuel de votre adhésion MA2E."),
        ("consult_ask_matricule", "Saisie du matricule", WorkflowStepType.question,
         None, "consult_lookup", {"on_invalid": "consult_ask_matricule"},
         "Saisissez votre *matricule employeur* (6 à 10 caractères alphanumériques)."),
        ("consult_lookup", "Recherche du dossier", WorkflowStepType.action,
         "lookup_dossier_by_matricule", "consult_show_status",
         {"not_found": "consult_not_found"}, None),
        ("consult_not_found", "Aucun dossier trouvé", WorkflowStepType.message,
         None, None, {},
         "❌ Aucun dossier trouvé pour ce matricule.\n\nSi vous n'êtes pas encore inscrit, tapez *INSCRIPTION* pour démarrer."),
        ("consult_show_status", "Affichage du statut", WorkflowStepType.message,
         None, "consult_ask_action", {},
         "📋 *Votre dossier MA2E*\n\n• N° dossier : {dossier_number}\n• Statut : *{status_label}*\n• Soumis le : {submitted_date}\n• Dernière mise à jour : {updated_date}"),
        ("consult_ask_action", "Action suivante ?", WorkflowStepType.question,
         None, "consult_end", {"2": "redirect_modify"},
         "Que souhaitez-vous faire ?\n\n1️⃣ *Terminer*\n2️⃣ *Modifier mes informations*"),
        ("redirect_modify", "Redirection vers modification", WorkflowStepType.message,
         None, None, {},
         "Très bien — je vous bascule vers le parcours de mise à jour. Tapez votre matricule à nouveau."),
        ("consult_end", "Fin de consultation", WorkflowStepType.message,
         None, None, {},
         "Merci ! N'hésitez pas à me solliciter si besoin. Tapez *MENU* pour revenir au point de départ."),
    ]
    await _seed_workflow(
        db, tenant_id,
        name="Consultation de dossier",
        description="Le sociétaire consulte l'état d'avancement de son adhésion (statut, dates, motif de refus le cas échéant).",
        start_step_code="consult_welcome",
        steps_def=steps_def,
        active=False,
    )

    # `redirect_modify` doit basculer vers le workflow Mise à jour après avoir
    # affiché son message. Le moteur lit `meta.switch_to_step` pour transitionner.
    await db.execute(
        text(
            "UPDATE workflow_steps SET meta = "
            "jsonb_set(COALESCE(meta, '{}'::jsonb), '{switch_to_step}', "
            "'\"update_ask_matricule\"'::jsonb) "
            "WHERE code = 'redirect_modify'"
        )
    )


async def _seed_modification_workflow(db, tenant_id):
    """Parcours « Mise à jour de dossier » : le sociétaire modifie ses infos."""
    steps_def = [
        ("update_welcome", "Accueil mise à jour", WorkflowStepType.message,
         None, "update_ask_matricule", {},
         "✏️ *Mise à jour de votre dossier MA2E*\n\nJe vais vous aider à modifier vos informations personnelles."),
        ("update_ask_matricule", "Identification", WorkflowStepType.question,
         None, "update_lookup", {"on_invalid": "update_ask_matricule"},
         "Pour retrouver votre dossier, saisissez votre *matricule employeur*."),
        ("update_lookup", "Recherche du dossier", WorkflowStepType.action,
         "lookup_dossier_by_matricule", "update_choose_field",
         {"not_found": "update_not_found"}, None),
        ("update_not_found", "Dossier introuvable", WorkflowStepType.message,
         None, None, {},
         "❌ Aucun dossier trouvé pour ce matricule. Veuillez d'abord vous inscrire (tapez *INSCRIPTION*)."),
        ("update_choose_field", "Champ à modifier", WorkflowStepType.question,
         None, "update_ask_new_value", {},
         "Quel champ souhaitez-vous modifier ?\n\n1️⃣ Email\n2️⃣ Téléphone\n3️⃣ Adresse postale\n4️⃣ Situation familiale\n5️⃣ Coordonnées bancaires"),
        ("update_ask_new_value", "Nouvelle valeur", WorkflowStepType.question,
         None, "update_apply", {"on_invalid": "update_ask_new_value"},
         "Saisissez la *nouvelle valeur* pour ce champ."),
        ("update_apply", "Application de la modification", WorkflowStepType.action,
         "apply_dossier_update", "update_confirm", {}, None),
        ("update_confirm", "Confirmation", WorkflowStepType.question,
         None, "update_end", {"1": "update_choose_field"},
         "✅ Modification enregistrée.\n\nUne autre modification ?\n1️⃣ *Oui*  2️⃣ *Non, terminer*"),
        ("update_end", "Fin de mise à jour", WorkflowStepType.message,
         None, None, {},
         "Merci ! Vos modifications ont été transmises. Un agent revalidera votre dossier si nécessaire."),
    ]
    await _seed_workflow(
        db, tenant_id,
        name="Mise à jour de dossier",
        description="Le sociétaire modifie ses informations personnelles (email, téléphone, adresse, RIB, ayants droit).",
        start_step_code="update_welcome",
        steps_def=steps_def,
        active=False,
    )


async def _seed_chat_libre_workflow(db, tenant_id):
    """Parcours « Chat libre / FAQ » : Q&A sur MA2E via RAG."""
    steps_def = [
        ("chat_welcome", "Accueil chat libre", WorkflowStepType.message,
         None, "chat_ask_question", {},
         "💬 *Espace questions libres*\n\nPosez-moi vos questions sur MA2E : adhésion, prestations, garanties, contact… Je puise dans la base de connaissances officielle."),
        ("chat_ask_question", "Question du sociétaire", WorkflowStepType.question,
         None, "chat_rag_search", {"on_exit": "chat_end"},
         "Quelle est votre question ? (tapez *FIN* pour terminer)"),
        ("chat_rag_search", "Recherche RAG", WorkflowStepType.action,
         "rag_answer_question", "chat_ask_more", {}, None),
        ("chat_ask_more", "Autre question ?", WorkflowStepType.question,
         None, "chat_end", {"1": "chat_ask_question"},
         "Souhaitez-vous poser une autre question ?\n1️⃣ *Oui*  2️⃣ *Non, terminer*"),
        ("chat_end", "Au revoir", WorkflowStepType.message,
         None, None, {},
         "Merci d'avoir utilisé l'assistante MA2E. À bientôt ! Pour toute urgence, contactez {support_phone}."),
    ]
    await _seed_workflow(
        db, tenant_id,
        name="Chat libre — Questions / FAQ",
        description="Le sociétaire (ou prospect) pose des questions libres sur MA2E. Réponses générées via RAG sur la base de connaissances.",
        start_step_code="chat_welcome",
        steps_def=steps_def,
        active=False,
    )


async def _seed_channel(db, tenant_id, channel: str, external_id, display_name: str, credentials: dict | None = None):
    if not external_id:
        print(f"  ⚠️  {channel} non configuré pour {display_name} (variables .env manquantes)")
        return

    if channel == "telegram":
        external_key = external_id.split(":")[0] if ":" in external_id else external_id
        creds = {"bot_token": external_id}
    else:
        external_key = external_id
        creds = credentials or {}

    existing = (
        await db.execute(
            select(TenantChannel).where(
                TenantChannel.channel == channel,
                TenantChannel.external_id == external_key,
            )
        )
    ).scalar_one_or_none()
    if existing:
        existing.credentials = creds
        existing.is_active = True
        print(f"  ↻  Channel {channel} pour {display_name} — credentials rafraîchis")
        return

    db.add(TenantChannel(
        tenant_id=tenant_id, channel=channel, external_id=external_key,
        display_name=display_name, credentials=creds,
    ))
    print(f"  ✅ Channel attaché : {display_name} ({channel})")


if __name__ == "__main__":
    asyncio.run(seed())
