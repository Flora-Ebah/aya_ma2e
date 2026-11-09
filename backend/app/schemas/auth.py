from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    # Jeton CSRF à réémettre en header X-CSRF-Token sur toute mutation.
    # Le frontend le lit depuis le cookie `ma2e_csrf` (non-httpOnly).
    csrf_token: str = ""
    user: dict


class MfaChallengeResponse(BaseModel):
    """Réponse au login quand MFA est exigé : pas encore de JWT, juste un challenge.

    Le frontend doit POST /api/auth/mfa/verify avec { challenge_token, code }.
    """
    mfa_required: bool = True
    challenge_token: str
    expires_in: int  # secondes


class MfaVerifyRequest(BaseModel):
    challenge_token: str
    code: str


class MfaEnableRequest(BaseModel):
    code: str


class MfaDisableRequest(BaseModel):
    code: str
