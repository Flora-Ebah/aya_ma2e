"""Migration : branche le parcours « Mise à jour de dossier » sur la base importée.

Pour une base DÉJÀ seedée. Idempotent. Usage :
    python seeds/patch_update_societaires.py [--activate]

Nouveau flux : identifiant -> recherche (lookup_societaire_base) -> date de
naissance (verify_societaire_identity) -> champ -> valeur -> apply_societaire_update.
Les messages personnalisés dans le back-office ne sont PAS écrasés.
"""
import asyncio
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import load_dotenv
load_dotenv(BACKEND_ROOT / ".env")

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models import Tenant, Workflow, WorkflowStep, WorkflowStepType
from app.services import workflow_template_service as wts

WF_NAME = "Mise à jour de dossier"
M, Q, A = WorkflowStepType.message, WorkflowStepType.question, WorkflowStepType.action

# Étapes à créer : code -> (label, type, action, next, branches, contenu message)
NEW_STEPS = {
    "update_ambiguous": ("Identifiant ambigu", M, None, None, {},
        "⚠️ Cet identifiant correspond à plusieurs dossiers. Merci de réessayer avec votre *ID client* ou votre *numéro de pièce d'identité*."),
    "update_ask_dob": ("Vérification d'identité", Q, None, "update_verify", {},
        "🔐 Pour votre sécurité, saisissez votre *date de naissance* (JJ/MM/AAAA)."),
    "update_verify": ("Contrôle de la date de naissance", A, "verify_societaire_identity", "update_choose_field",
        {"mismatch": "update_identity_failed", "no_birthdate": "update_identity_failed",
         "locked": "update_identity_failed"}, None),
    "update_identity_failed": ("Identité non vérifiée", M, None, None, {},
        "❌ Vérification impossible. Aucune modification n'a été faite.\n\nRelancez le parcours (tapez *MENU*) ou contactez MA2E."),
    "update_prepare": ("Préparation du champ", A, "prepare_societaire_field", "update_ask_new_value",
        {"invalid": "update_invalid"}, None),
    "update_invalid": ("Valeur refusée", M, None, "update_choose_field", {},
        "Reprenons : choisissez à nouveau le champ à modifier."),
}

# Messages existants : code étape -> (ancien défaut, nouveau)
CHANGED = {
    "update_ask_matricule": (
        "Pour retrouver votre dossier, saisissez votre *matricule employeur*.",
        "Pour retrouver votre dossier, saisissez votre *matricule*, votre *ID client* ou votre *numéro de pièce d'identité (CNI)*."),
    "update_not_found": (
        "❌ Aucun dossier trouvé pour ce matricule. Veuillez d'abord vous inscrire (tapez *INSCRIPTION*).",
        "❌ Aucun sociétaire trouvé avec cet identifiant. Vérifiez votre saisie, ou tapez *INSCRIPTION* si vous n'êtes pas encore inscrit."),
    # `old` peut être un tuple : tous les anciens défauts connus (menu d'origine, puis menu à 4 champs)
    "update_choose_field": (
        ("Quel champ souhaitez-vous modifier ?\n\n1️⃣ Email\n2️⃣ Téléphone\n3️⃣ Adresse postale\n4️⃣ Situation familiale\n5️⃣ Coordonnées bancaires",
         "Quel champ souhaitez-vous modifier ?\n\n1️⃣ Email\n2️⃣ Téléphone\n3️⃣ Adresse postale\n4️⃣ Situation familiale"),
        "Quel champ souhaitez-vous modifier ?\n\n*1* Email\n*2* Téléphone\n*3* Domicile\n*4* Boîte postale\n*5* Situation matrimoniale\n*6* Conjoint(e)\n*7* Nom de la mère\n*8* Fonction\n*9* Catégorie\n*10* Société / employeur\n*11* Personne à prévenir\n*12* Consentement au traitement de mes données"),
    "update_ask_new_value": (
        "Saisissez la *nouvelle valeur* pour ce champ.",
        "Saisissez la *nouvelle valeur* pour *{field_label}* {field_hint}"),
}


async def main(activate: bool) -> None:
    engine = create_async_engine(settings.database_url)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as db:
        wf = (await db.execute(
            select(Workflow).options(selectinload(Workflow.steps)).where(Workflow.name == WF_NAME)
        )).scalar_one_or_none()
        if wf is None:
            print(f"❌ Workflow « {WF_NAME} » introuvable : lancez d'abord seeds/seed.py")
            return
        tenant = (await db.execute(select(Tenant).where(Tenant.slug == "ma2e"))).scalar_one()
        steps = {s.code: s for s in wf.steps}

        # Étapes existantes réorientées
        lk = steps["update_lookup"]
        lk.action_name, lk.label = "lookup_societaire_base", "Recherche du sociétaire"
        lk.next_step_code = "update_ask_dob"
        lk.branches = {"not_found": "update_not_found", "ambiguous": "update_ambiguous"}
        steps["update_not_found"].label = "Sociétaire introuvable"
        steps["update_choose_field"].next_step_code = "update_prepare"
        ap = steps["update_apply"]
        ap.action_name, ap.branches = "apply_societaire_update", {"invalid": "update_invalid"}
        print("✅ update_lookup / update_apply rebranchés")

        # Nouvelles étapes (positions intercalées : lookup=30 -> dob/verify entre 30 et 40)
        positions = {"update_ask_dob": 32, "update_verify": 34, "update_identity_failed": 36,
                     "update_ambiguous": 38, "update_invalid": 72, "update_prepare": 55}
        for code, (label, typ, action, nxt, branches, content) in NEW_STEPS.items():
            if code not in steps:
                db.add(WorkflowStep(
                    workflow_id=wf.id, code=code, label=label, type=typ, template_code=None,
                    action_name=action, next_step_code=nxt, branches=branches, position=positions[code],
                ))
                print(f"✅ étape {code} ajoutée")
            if content:
                tcode = wts.derive_code(code)
                if await wts.get_content(db, tenant.id, tcode) is None:
                    await wts.upsert(db, tenant.id, tcode, content)

        for code, (old, new) in CHANGED.items():
            tcode = wts.derive_code(code)
            cur = await wts.get_content(db, tenant.id, tcode)
            olds = old if isinstance(old, tuple) else (old,)
            if cur is None or cur in olds or cur == new:
                await wts.upsert(db, tenant.id, tcode, new)
                print(f"✅ message {code} mis à jour")
            else:
                print(f"⏭  message {code} personnalisé dans le back-office : laissé intact")

        if activate:
            wf.active = True
            print("✅ workflow activé")
        await db.commit()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main("--activate" in sys.argv))
