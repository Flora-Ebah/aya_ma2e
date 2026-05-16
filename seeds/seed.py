"""Seed initial pour la démo MA2E.

Crée :
- Tenant MA2E (principal) + tenants placeholder CIE/SODECI (extension groupe)
- Texte de consentement ARTCI conforme loi 2013-450 art.16 (versionné, hashé)
- Liste fermée des employeurs (SODECI, CIE, GS2E, SMB, SDE, etc.)
- 3 comptes utilisateurs (super_admin GS2E, tenant_admin MA2E, agent MA2E)

Usage (depuis le dossier racine du projet):
    python seeds/seed.py
"""
import asyncio
import hashlib
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from dotenv import load_dotenv
load_dotenv(ROOT / "backend" / ".env")

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import hash_password
from app.models import (
    ConsentGate,
    Employeur,
    Tenant,
    TenantChannel,
    TexteConsentement,
    User,
    UserRole,
)


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
        #  TENANTS PLACEHOLDER pour démontrer l'extension groupe
        # ============================================================
        for slug, name, desc in [
            ("cie", "CIE", "Compagnie Ivoirienne d'Électricité — Onboarding prévu Phase 2"),
            ("sodeci", "SODECI", "Société de Distribution d'Eau — Onboarding prévu Phase 2"),
        ]:
            existing = (await db.execute(select(Tenant).where(Tenant.slug == slug))).scalar_one_or_none()
            if not existing:
                t = Tenant(
                    slug=slug, name=name, description=desc,
                    branding={"bot_name": f"Assistant {name}", "status": "ready_for_onboarding"},
                    menu_config={}, llm_config={},
                    is_active=False,
                )
                db.add(t)
                print(f"  ✅ Tenant placeholder créé : {slug}")

        # ============================================================
        #  UTILISATEURS
        # ============================================================
        for email, pwd, name, role, tenant_id in [
            ("admin@gs2e.ci", "admin123", "Super Admin GS2E", UserRole.super_admin, None),
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
        #  CHANNELS
        # ============================================================
        # WhatsApp Cloud API (canal principal)
        await _seed_channel(
            db, ma2e.id, "whatsapp",
            os.getenv("WHATSAPP_PHONE_ID_MA2E"), "MA2E WhatsApp",
            credentials={"access_token": os.getenv("WHATSAPP_ACCESS_TOKEN_MA2E", "")},
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
