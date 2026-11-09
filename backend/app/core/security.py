import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings


# Claim `type` inséré dans le payload pour distinguer access ↔ refresh.
# Un token de refresh présenté comme access (ou l'inverse) sera rejeté.
TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"


def hash_password(password: str) -> str:
    pw = password.encode("utf-8")[:72]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str, tenant_id: Optional[str], role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": subject,
        "tenant_id": tenant_id,
        "role": role,
        "type": TOKEN_TYPE_ACCESS,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str, tenant_id: Optional[str], role: str) -> tuple[str, str]:
    """Émet un refresh token avec un `jti` unique.

    Retourne `(token, jti)`. Le `jti` doit être enregistré côté serveur
    (Redis) pour permettre la révocation et la détection de vol
    (réutilisation d'un ancien refresh déjà rotaté).
    """
    jti = secrets.token_urlsafe(24)
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_expire_days)
    payload = {
        "sub": subject,
        "tenant_id": tenant_id,
        "role": role,
        "type": TOKEN_TYPE_REFRESH,
        "jti": jti,
        "exp": expire,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, jti


def decode_token(token: str) -> dict:
    """Décode un access token. Rejette si `type` ne matche pas."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as e:
        raise ValueError("invalid token") from e
    # Rétrocompatibilité : les tokens émis AVANT l'ajout du claim `type`
    # sont considérés comme access (sinon on invalide toutes les sessions
    # au déploiement de cette version).
    tok_type = payload.get("type", TOKEN_TYPE_ACCESS)
    if tok_type != TOKEN_TYPE_ACCESS:
        raise ValueError(f"wrong token type: expected access, got {tok_type}")
    return payload


def decode_refresh_token(token: str) -> dict:
    """Décode un refresh token. Rejette si `type != "refresh"`."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as e:
        raise ValueError("invalid refresh token") from e
    if payload.get("type") != TOKEN_TYPE_REFRESH:
        raise ValueError("wrong token type: expected refresh")
    if not payload.get("jti"):
        raise ValueError("refresh token missing jti")
    return payload
