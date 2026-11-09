import logging
import secrets
from datetime import datetime, timezone
from typing import Optional, Union

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pydantic import BaseModel, EmailStr

from app.core.config import settings
from app.core.database import get_db
from app.core.redis import redis_client
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    verify_password,
)
from app.models import AuthMethod, User
from app.schemas.auth import (
    LoginRequest,
    MfaChallengeResponse,
    MfaVerifyRequest,
    TokenResponse,
)
from app.services import ad_service, mfa_service, security_policy
from app.services.ad_service import ADAuthError

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ────────────────────────────────────────────────────────────────────────
# Session par cookie httpOnly + jeton CSRF (double-submit).
#
# Le JWT est stocké dans un cookie httpOnly (invisible pour JavaScript ⇒
# immunisé au vol par XSS). Un second cookie `ma2e_csrf`, lui lisible par
# JS, contient un jeton aléatoire que le frontend doit réémettre en
# header `X-CSRF-Token` sur toute mutation. Le middleware CSRF vérifie
# que les deux correspondent.
#
# `access_token` reste renvoyé dans la réponse JSON pour la compatibilité
# des clients existants pendant la transition — à retirer en Phase 3.
# ────────────────────────────────────────────────────────────────────────
def _refresh_jti_key(jti: str) -> str:
    """Clé Redis d'un `jti` de refresh (utilisée pour anti-replay et révocation)."""
    return f"refresh:jti:{jti}"


async def _register_refresh_jti(jti: str, user_id: str) -> None:
    """Marque un `jti` comme valide dans Redis avec le TTL du refresh token."""
    try:
        await redis_client.set(
            _refresh_jti_key(jti),
            user_id,
            ex=settings.refresh_expire_days * 24 * 3600,
        )
    except Exception as e:  # noqa: BLE001
        # Redis KO : on log, la révocation ne sera pas possible mais le login
        # continue de fonctionner (fail-open sur l'auth pour la disponibilité).
        log.warning("refresh: cannot register jti %s (%s)", jti, e)


async def _consume_refresh_jti(jti: str) -> Optional[str]:
    """Vérifie qu'un `jti` est encore valide et le supprime atomiquement (rotation).

    Retourne le `user_id` associé, ou None si le `jti` est inconnu / déjà consommé.
    L'utilisation d'un `GETDEL` atomique évite toute race entre 2 refresh concurrents.
    """
    try:
        return await redis_client.getdel(_refresh_jti_key(jti))
    except Exception as e:  # noqa: BLE001
        log.warning("refresh: cannot consume jti %s (%s)", jti, e)
        return None


async def _revoke_refresh_jti(jti: str) -> None:
    """Révoque explicitement un `jti` (au logout)."""
    try:
        await redis_client.delete(_refresh_jti_key(jti))
    except Exception:
        pass


def _apply_auth_cookies(response: Response, access_token: str,
                        refresh_token: Optional[str] = None) -> str:
    """Pose les 3 cookies : session (httpOnly), CSRF (visible JS), refresh (httpOnly).

    Retourne la valeur du jeton CSRF (également renvoyée en JSON pour bootstrap).
    """
    csrf = secrets.token_urlsafe(32)
    access_max_age = settings.jwt_expire_minutes * 60
    common_session = dict(
        max_age=access_max_age,
        path="/",
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
    )
    if settings.auth_cookie_domain:
        common_session["domain"] = settings.auth_cookie_domain

    # 1) Cookie access token — httpOnly, envoyé sur tout le site.
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=access_token,
        httponly=True,
        **common_session,
    )
    # 2) Cookie CSRF — visible par JS, à réémettre en header X-CSRF-Token.
    response.set_cookie(
        key=settings.auth_csrf_cookie_name,
        value=csrf,
        httponly=False,
        **common_session,
    )
    # 3) Cookie refresh token — httpOnly, scope réduit au router /api/auth
    #    pour minimiser l'exposition (transporté uniquement lors des appels
    #    /api/auth/refresh et /api/auth/logout).
    if refresh_token:
        refresh_max_age = settings.refresh_expire_days * 24 * 3600
        common_refresh = dict(
            max_age=refresh_max_age,
            path="/api/auth",
            secure=settings.auth_cookie_secure,
            samesite=settings.auth_cookie_samesite,
        )
        if settings.auth_cookie_domain:
            common_refresh["domain"] = settings.auth_cookie_domain
        response.set_cookie(
            key=settings.auth_refresh_cookie_name,
            value=refresh_token,
            httponly=True,
            **common_refresh,
        )
    return csrf


def _clear_auth_cookies(response: Response) -> None:
    """Supprime les 3 cookies (session + CSRF + refresh)."""
    session_kwargs = dict(path="/")
    refresh_kwargs = dict(path="/api/auth")
    if settings.auth_cookie_domain:
        session_kwargs["domain"] = settings.auth_cookie_domain
        refresh_kwargs["domain"] = settings.auth_cookie_domain
    response.delete_cookie(settings.auth_cookie_name, **session_kwargs)
    response.delete_cookie(settings.auth_csrf_cookie_name, **session_kwargs)
    response.delete_cookie(settings.auth_refresh_cookie_name, **refresh_kwargs)


async def _issue_token_response(user: User, response: Response) -> TokenResponse:
    """Génère access + refresh, pose les cookies, renvoie la structure JSON métier."""
    access = create_access_token(
        subject=str(user.id),
        tenant_id=str(user.tenant_id) if user.tenant_id else None,
        role=user.role.value,
    )
    refresh, jti = create_refresh_token(
        subject=str(user.id),
        tenant_id=str(user.tenant_id) if user.tenant_id else None,
        role=user.role.value,
    )
    await _register_refresh_jti(jti, str(user.id))
    csrf = _apply_auth_cookies(response, access, refresh_token=refresh)
    return TokenResponse(
        access_token=access,
        csrf_token=csrf,
        user={
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "role": user.role.value,
            "tenant_id": str(user.tenant_id) if user.tenant_id else None,
        },
    )


@router.post("/login", response_model=Union[TokenResponse, MfaChallengeResponse])
async def login(payload: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    # Vérifie d'abord le verrouillage avant même de toucher à la BD
    locked, until = await security_policy.is_locked(payload.email)
    if locked:
        retry_after = int((until - datetime.now(timezone.utc)).total_seconds())
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Compte temporairement verrouillé suite à des tentatives répétées. "
                f"Réessayez dans {max(1, retry_after // 60)} minutes."
            ),
            headers={"Retry-After": str(retry_after)},
        )

    result = await db.execute(
        select(User).where(User.email == payload.email, User.is_active.is_(True))
    )
    user = result.scalar_one_or_none()

    # Si l'utilisateur existe et est en mode AD, refuser le login password classique
    if user is not None and user.auth_method == AuthMethod.ad:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Ce compte utilise l'authentification Active Directory ERANOVE. "
                "Cliquez sur « Se connecter avec ERANOVE »."
            ),
        )

    if not user or not user.password_hash or not verify_password(payload.password, user.password_hash):
        # Politique du tenant de l'utilisateur cible si trouvé, sinon registry defaults
        target_tenant = user.tenant_id if user else None
        policy = await security_policy.get_policy(db, target_tenant)
        attempts, lockout_until = await security_policy.record_failed_attempt(
            payload.email, policy,
        )
        if lockout_until is not None:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Trop d'échecs ({attempts}). Compte verrouillé pour "
                    f"{policy.login_lockout_minutes} minutes."
                ),
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid credentials",
        )

    # Login OK → reset compteur
    await security_policy.reset_attempts(payload.email)

    # Si MFA est activé, on n'émet PAS le JWT — challenge à fournir d'abord
    if user.mfa_enabled:
        challenge = await mfa_service.create_login_challenge(user)
        return MfaChallengeResponse(
            mfa_required=True,
            challenge_token=challenge,
            expires_in=mfa_service.CHALLENGE_TTL_SECONDS,
        )

    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    return await _issue_token_response(user, response)


@router.post("/mfa/verify", response_model=TokenResponse)
async def mfa_verify(
    payload: MfaVerifyRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Vérifie le code TOTP soumis avec un challenge_token.
    Sur succès, émet le JWT final (cookie httpOnly + CSRF)."""
    user = await mfa_service.consume_challenge(payload.challenge_token, payload.code, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Code MFA invalide ou challenge expiré.",
        )
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    return await _issue_token_response(user, response)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    ma2e_refresh: Optional[str] = Cookie(default=None, alias="ma2e_refresh"),
):
    """Termine la session : révoque le refresh token puis supprime les cookies.

    Idempotent — appelable sans être authentifié (le refresh cookie peut
    être absent). Aucune erreur remontée si le jeton est déjà expiré ou
    invalide, on nettoie simplement l'état côté navigateur.
    """
    if ma2e_refresh:
        try:
            payload = decode_refresh_token(ma2e_refresh)
            await _revoke_refresh_jti(payload["jti"])
        except ValueError:
            pass
    _clear_auth_cookies(response)
    return None


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    response: Response,
    db: AsyncSession = Depends(get_db),
    ma2e_refresh: Optional[str] = Cookie(default=None, alias="ma2e_refresh"),
):
    """Régénère un couple access + refresh à partir du refresh cookie httpOnly.

    Le refresh token est **rotaté** à chaque appel : le `jti` consommé est
    supprimé de Redis (GETDEL atomique) et un nouveau `jti` est enregistré.
    Toute réutilisation d'un ancien refresh échouera (401) — signal de vol.
    """
    if not ma2e_refresh:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="missing refresh token")

    try:
        payload = decode_refresh_token(ma2e_refresh)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail=f"invalid refresh token: {e}")

    jti = payload["jti"]
    user_id = payload["sub"]

    # Consomme atomiquement le jti (empêche la réutilisation).
    stored_user_id = await _consume_refresh_jti(jti)
    if stored_user_id is None:
        # jti déjà consommé ou inconnu → refresh volé ou expiré.
        # Par sécurité on force la déconnexion complète.
        _clear_auth_cookies(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="refresh token replay detected")
    if stored_user_id != user_id:
        _clear_auth_cookies(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="refresh token subject mismatch")

    # Recharge l'utilisateur (peut avoir été désactivé entre-temps).
    user = (await db.execute(
        select(User).where(User.id == user_id, User.is_active.is_(True))
    )).scalar_one_or_none()
    if user is None:
        _clear_auth_cookies(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="user disabled")

    # Émet une nouvelle paire access + refresh (rotation).
    return await _issue_token_response(user, response)


# ====================================================================== #
# Authentification Active Directory ERANOVE (US-02)
# ====================================================================== #
class ADLoginRequest(BaseModel):
    """Requête de login AD.

    En POC : seul `email` est requis (l'app considère l'utilisateur authentifié
    par sa session de domaine côté poste de travail ERANOVE).

    En prod (Azure AD OIDC) : `code` est l'authorization code retourné par
    Microsoft après la redirection vers `/oauth2/v2.0/authorize`. Le serveur
    l'échange contre un id_token et en extrait l'email vérifié.
    """
    email: EmailStr
    code: Optional[str] = None
    redirect_uri: Optional[str] = None


@router.post("/ad/login", response_model=Union[TokenResponse, MfaChallengeResponse])
async def ad_login(
    payload: ADLoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Authentification déléguée à l'AD ERANOVE pour les agents internes.

    Lockout email-based partagé avec le flow password classique.
    """
    locked, until = await security_policy.is_locked(payload.email)
    if locked:
        retry_after = int((until - datetime.now(timezone.utc)).total_seconds())
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Compte temporairement verrouillé. "
                f"Réessayez dans {max(1, retry_after // 60)} minutes."
            ),
        )

    # Production : échanger le `code` OIDC contre l'identité vérifiée
    if payload.code and payload.redirect_uri:
        verified = await ad_service.exchange_oidc_code(payload.code, payload.redirect_uri)
        if verified is None:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="OIDC Azure AD pas encore activé sur ce déploiement.",
            )
        verified_email = verified["email"]
    else:
        # POC : on se contente de vérifier l'email contre le référentiel des
        # comptes AD enregistrés. La vraie auth est faite côté poste ERANOVE.
        verified_email = payload.email

    try:
        user = await ad_service.verify_ad_login(db, email=verified_email)
    except ADAuthError as e:
        policy = await security_policy.get_policy(db, None)
        await security_policy.record_failed_attempt(payload.email, policy)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    # Login AD OK → reset compteur et émettre JWT (ou challenge MFA si actif)
    await security_policy.reset_attempts(payload.email)

    if user.mfa_enabled:
        challenge = await mfa_service.create_login_challenge(user)
        return MfaChallengeResponse(
            mfa_required=True,
            challenge_token=challenge,
            expires_in=mfa_service.CHALLENGE_TTL_SECONDS,
        )

    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    return await _issue_token_response(user, response)
