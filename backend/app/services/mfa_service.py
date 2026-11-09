"""Service MFA TOTP (RFC 6238) pour les comptes back-office.

Flow d'activation :
1. `generate_setup(user)` → secret stocké provisoirement (mfa_secret) + QR code
2. L'utilisateur scanne le QR avec Google Authenticator / Authy
3. `enable_mfa(user, code)` → vérifie le premier code et active mfa_enabled

Flow de login :
1. Login OK avec email/password → si user.mfa_enabled, retourne un challenge
2. Le frontend POST /api/auth/mfa/verify avec { challenge_token, code }
3. Sur succès, le JWT final est délivré

Le secret TOTP est sensible : ne JAMAIS le retourner en clair après l'activation.
"""
from __future__ import annotations

import base64
import io
import logging
import secrets
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

import pyotp
import qrcode
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditAction, User
from app.services import audit_service

logger = logging.getLogger(__name__)

ISSUER = "MA2E"
# Tolérance : ±1 fenêtre de 30s (gère léger décalage horloge client/serveur)
VALID_WINDOW = 1


# ====================================================================== #
# Setup / activation
# ====================================================================== #
def _make_secret() -> str:
    """Génère un secret base32 de 160 bits (recommandation RFC 4226)."""
    return pyotp.random_base32(length=32)


def build_otpauth_url(email: str, secret: str) -> str:
    """URL `otpauth://` scannée par Google Authenticator."""
    return pyotp.totp.TOTP(secret).provisioning_uri(
        name=email, issuer_name=ISSUER,
    )


def build_qr_data_uri(otpauth_url: str) -> str:
    """QR code en data URI (PNG base64) — embeddable dans une <img>."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(otpauth_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


async def generate_setup(
    db: AsyncSession,
    user: User,
) -> dict[str, str]:
    """Génère un nouveau secret pour ce user et retourne les éléments d'enrôlement.

    Note : le secret est stocké en BD mais `mfa_enabled` reste False jusqu'à
    la vérification du premier code.
    """
    if user.mfa_enabled:
        raise ValueError("MFA déjà activé. Désactivez-le avant de regénérer.")

    secret = _make_secret()
    user.mfa_secret = secret
    user.mfa_enrolled_at = None
    await db.flush()

    otpauth = build_otpauth_url(user.email, secret)
    return {
        "secret": secret,
        "otpauth_url": otpauth,
        "qr_code_data_uri": build_qr_data_uri(otpauth),
        "issuer": ISSUER,
    }


def verify_code(secret: str, code: str) -> bool:
    """Vérifie un code TOTP 6 chiffres avec tolérance ±1 fenêtre."""
    if not secret or not code:
        return False
    cleaned = code.strip().replace(" ", "")
    if not cleaned.isdigit() or len(cleaned) != 6:
        return False
    return pyotp.TOTP(secret).verify(cleaned, valid_window=VALID_WINDOW)


async def enable_mfa(
    db: AsyncSession,
    user: User,
    code: str,
) -> User:
    """Vérifie le premier code TOTP saisi et active MFA."""
    if user.mfa_enabled:
        raise ValueError("MFA déjà activé.")
    if not user.mfa_secret:
        raise ValueError("Aucun secret enregistré. Lancez d'abord /mfa/setup.")

    if not verify_code(user.mfa_secret, code):
        raise ValueError("Code TOTP invalide.")

    user.mfa_enabled = True
    user.mfa_enrolled_at = datetime.now(timezone.utc)
    await db.flush()

    await audit_service.log(
        db,
        tenant_id=user.tenant_id or user.id,
        action=AuditAction.user_mfa_enabled,
        resource_type="user",
        resource_id=str(user.id),
        actor_type="user",
        actor_id=str(user.id),
        details={"email": user.email},
    )
    return user


async def disable_mfa(
    db: AsyncSession,
    user: User,
    code: str,
    *,
    actor_id: Optional[UUID] = None,
    forced: bool = False,
) -> User:
    """Désactive MFA. Si `forced=True` (admin), pas besoin de code.
    Sinon le user doit fournir un code TOTP valide."""
    if not user.mfa_enabled:
        raise ValueError("MFA n'est pas activé.")

    if not forced and not verify_code(user.mfa_secret or "", code):
        raise ValueError("Code TOTP invalide.")

    user.mfa_enabled = False
    user.mfa_secret = None
    user.mfa_enrolled_at = None
    await db.flush()

    await audit_service.log(
        db,
        tenant_id=user.tenant_id or user.id,
        action=AuditAction.user_mfa_disabled,
        resource_type="user",
        resource_id=str(user.id),
        actor_type="user",
        actor_id=str(actor_id or user.id),
        details={"email": user.email, "forced_by_admin": forced},
    )
    return user


# ====================================================================== #
# Challenge / login
# ====================================================================== #
# Token de challenge éphémère (5 min) stocké en cache Redis.
# Le frontend reçoit ce token en réponse au login, puis le renvoie avec le code.
from app.core.cache import cache  # noqa: E402

CHALLENGE_TTL_SECONDS = 300


def _challenge_key(token: str) -> str:
    return f"mfa_challenge:{token}"


async def create_login_challenge(user: User) -> str:
    """Crée un token de challenge MFA valable 5 min."""
    token = secrets.token_urlsafe(32)
    await cache.set_json(
        _challenge_key(token),
        {"user_id": str(user.id)},
        ttl=CHALLENGE_TTL_SECONDS,
    )
    return token


async def consume_challenge(token: str, code: str, db: AsyncSession) -> Optional[User]:
    """Récupère le user du challenge et vérifie le code TOTP.
    Retourne le user en cas de succès, None sinon. Le challenge est consommé
    quelle que soit l'issue (anti-rejeu)."""
    raw = await cache.get_json(_challenge_key(token))
    if raw is None:
        return None
    await cache.invalidate(_challenge_key(token))

    user_id_str = raw.get("user_id")
    if not user_id_str:
        return None

    from app.services import user_service
    try:
        user_id = UUID(user_id_str)
    except (TypeError, ValueError):
        return None
    user = await user_service.get_user(db, user_id)
    if user is None or not user.mfa_enabled or not user.mfa_secret:
        return None
    if not verify_code(user.mfa_secret, code):
        return None

    await audit_service.log(
        db,
        tenant_id=user.tenant_id or user.id,
        action=AuditAction.user_mfa_verified,
        resource_type="user",
        resource_id=str(user.id),
        actor_type="user",
        actor_id=str(user.id),
        details={"email": user.email},
    )
    return user
