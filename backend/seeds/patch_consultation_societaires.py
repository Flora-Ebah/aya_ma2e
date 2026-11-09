"""Migration : branche le parcours « Consultation de dossier » sur la base importée.

Pour une base DÉJÀ seedée (le seed ne met pas à jour un workflow existant).
Idempotent. Usage :  python seeds/patch_consultation_societaires.py [--activate]

- consult_lookup : action `lookup_societaire_base` + branche `ambiguous`
- ajoute l'étape `consult_ambiguous`
- met à jour les 4 messages concernés, SAUF si l'utilisateur les a modifiés
  dans le back-office (contenu différent du défaut d'origine) : ils sont alors
  laissés intacts et signalés.
- `--activate` : active aussi le workflow (il est inactif par défaut au seed).
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

WF_NAME = "Consultation de dossier"

# step_code -> (ancien défaut du seed, nouveau contenu)
TEMPLATES = {
    "consult_ask_matricule": (
        "Saisissez votre *matricule employeur* (6 à 10 caractères alphanumériques).",
        "Saisissez votre *matricule*, votre *ID client* ou votre *numéro de pièce d'identité (CNI)*.",
    ),
    "consult_not_found": (
        "❌ Aucun dossier trouvé pour ce matricule.\n\nSi vous n'êtes pas encore inscrit, tapez *INSCRIPTION* pour démarrer.",
        "❌ Aucun sociétaire trouvé avec cet identifiant.\n\nVérifiez votre saisie, ou contactez MA2E. Si vous n'êtes pas encore inscrit, tapez *INSCRIPTION* pour démarrer.",
    ),
    "consult_show_status": (
        "📋 *Votre dossier MA2E*\n\n• N° dossier : {dossier_number}\n• Statut : *{status_label}*\n• Soumis le : {submitted_date}\n• Dernière mise à jour : {updated_date}",
        "📋 *Votre adhésion MA2E*\n\n• Sociétaire : {soc_display_name}\n• Statut : *{soc_statut}*\n• Employeur : {soc_employeur}\n• Adhérent depuis le : {soc_date_adhesion}",
    ),
    "consult_ambiguous": (
        None,
        "⚠️ Cet identifiant correspond à plusieurs dossiers. Merci de réessayer avec votre *ID client* ou votre *numéro de pièce d'identité*.",
    ),
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

        lookup = steps["consult_lookup"]
        lookup.action_name = "lookup_societaire_base"
        lookup.label = "Recherche du sociétaire"
        lookup.branches = {"not_found": "consult_not_found", "ambiguous": "consult_ambiguous"}
        print("✅ consult_lookup → lookup_societaire_base (+ branche ambiguous)")

        if "consult_ambiguous" not in steps:
            db.add(WorkflowStep(
                workflow_id=wf.id, code="consult_ambiguous", label="Identifiant ambigu",
                type=WorkflowStepType.message, template_code=None, action_name=None,
                next_step_code=None, branches={}, position=(steps["consult_not_found"].position + 5),
            ))
            print("✅ étape consult_ambiguous ajoutée")
        steps["consult_not_found"].label = "Aucun sociétaire trouvé"

        for step_code, (old, new) in TEMPLATES.items():
            code = wts.derive_code(step_code)
            current = await wts.get_content(db, tenant.id, code)
            if current is None or current == old or current == new:
                await wts.upsert(db, tenant.id, code, new)
                print(f"✅ message {step_code} mis à jour")
            else:
                print(f"⏭  message {step_code} personnalisé dans le back-office : laissé intact")

        if activate:
            wf.active = True
            print("✅ workflow activé")
        await db.commit()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main("--activate" in sys.argv))
