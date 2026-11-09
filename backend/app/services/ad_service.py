"""Service d'authentification Active Directory ERANOVE (US-02).

**Mode POC (par défaut)** : le service accepte une auth AD si :
- l'utilisateur existe dans `users` avec `auth_method=ad`
- et son email matche le suffixe de domaine ERANOVE configuré

**Mode production** (à câbler avant prod) : intégration Azure AD (Entra ID) via OIDC
en utilisant `msal-python`. Le bouton frontend redirige vers la page de consentement
Microsoft, qui retourne un code échangé contre un token. On vérifie le claim `email`
et on émet notre JWT MA2E.

Le pattern adapter permet de basculer du POC à la prod sans toucher au reste.
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import AuthMethod, User
from app.services import user_service

logger = logging.getLogger(__name__)


# Domaines acceptés en POC (à remplacer par la vérif Azure AD réelle en prod)
ERANOVE_DOMAINS = ("@eranove.com", "@cie.ci", "@sodeci.ci", "@ma2e.ci")


class ADAuthError(Exception):
    """Erreur d'authentification AD."""


async def verify_ad_login(
    db: AsyncSession,
    *,
    email: str,
) -> User:
    """Vérifie qu'un email peut se connecter via AD ERANOVE.

    En POC : check que le user existe avec auth_method=ad ET que l'email
    appartient à un domaine du groupe.

    En prod : le caller aura validé le token Azure AD avant d'appeler ici.

    Lève ADAuthError sur tout échec. Retourne le User correspondant.
    """
    email_norm = email.lower().strip()

    # 1. Vérification basique du domaine
    if not any(email_norm.endswith(d) for d in ERANOVE_DOMAINS):
        raise ADAuthError(
            "Email hors périmètre AD ERANOVE. "
            "L'authentification AD est réservée aux agents internes du groupe."
        )

    # 2. L'utilisateur doit exister et être en mode AD
    user = await user_service.get_by_email(db, email_norm)
    if user is None:
        raise ADAuthError(
            "Aucun compte MA2E ne correspond à cet email. "
            "Contactez votre administrateur MA2E pour créer votre compte."
        )

    if user.auth_method != AuthMethod.ad:
        raise ADAuthError(
            "Ce compte n'est pas configuré pour l'authentification AD. "
            "Utilisez le formulaire email/mot de passe."
        )

    if not user.is_active:
        raise ADAuthError("Ce compte est désactivé.")

    return user


# ====================================================================== #
# Skeleton Azure AD OIDC (à activer en prod)
# ====================================================================== #
async def exchange_oidc_code(code: str, redirect_uri: str) -> Optional[dict]:
    """Échange un `code` OIDC reçu de Azure AD contre un id_token.

    À implémenter en production avec `msal-python` :
        msal_app = msal.ConfidentialClientApplication(
            client_id=settings.azure_ad_client_id,
            authority=f"https://login.microsoftonline.com/{settings.azure_ad_tenant_id}",
            client_credential=settings.azure_ad_client_secret,
        )
        result = msal_app.acquire_token_by_authorization_code(
            code, scopes=["openid", "email", "profile"],
            redirect_uri=redirect_uri,
        )
        return {
            "email": result["id_token_claims"]["email"],
            "name": result["id_token_claims"]["name"],
        }

    Pour le POC, retourne None — l'admin doit utiliser le mode POC simplifié.
    """
    logger.info("OIDC code exchange (POC stub) — code length=%d", len(code or ""))
    return None
