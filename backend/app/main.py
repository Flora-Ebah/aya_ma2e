from contextlib import asynccontextmanager
from secrets import compare_digest as secrets_compare

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.rate_limit import check_rate_limit, find_rule
from app.core.request_context import RequestContext, set_current
from app.core import scheduler as app_scheduler
from app.core.security import decode_token

from app.api import audit as audit_api
from app.api import auth as auth_api
from app.api import collaborateurs as collaborateurs_api
from app.api import dossiers as dossiers_api
from app.api import duplicates as duplicates_api
from app.api import employeurs as employeurs_api
from app.api import health as health_api
from app.api import imports as imports_api
from app.api import roles as roles_api
from app.api import integrations as integrations_api
from app.api import knowledge as knowledge_api
from app.api import me as me_api
from app.api import message_templates as templates_api
from app.api import otp as otp_api
from app.api import security as security_api
from app.api import settings as settings_api
from app.api import stats as stats_api
from app.api import users as users_api
from app.api import workflows as workflows_api
from app.core.config import settings
from app.core.logging_config import configure_logging
from app.webhooks import web as web_webhook
from app.webhooks import whatsapp as whatsapp_webhook

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app_scheduler.start()
    try:
        yield
    finally:
        app_scheduler.shutdown()


# F-05 : la doc API interactive est retirée en production pour ne pas
# divulguer la surface d'attaque à un visiteur anonyme. Elle reste
# disponible en dev/staging pour l'équipe.
_IS_PROD = settings.app_env == "production"

app = FastAPI(
    title="MA2E - Plateforme Digitale d'Identification",
    description="Plateforme d'identification des sociétaires MA2E (Mutuelle des Agents de l'Eau et de l'Électricité), conforme ARTCI loi 2013-450.",
    version="0.2.0",
    lifespan=lifespan,
    docs_url=None if _IS_PROD else "/docs",
    redoc_url=None if _IS_PROD else "/redoc",
    openapi_url=None if _IS_PROD else "/openapi.json",
)

def _extract_client_ip(request: Request) -> str:
    """IP client compatible reverse-proxy. Utilisée par plusieurs middlewares."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _extract_user_id_from_jwt(request: Request) -> str | None:
    """Décodage léger du JWT (sans DB) pour identifier l'utilisateur. Best-effort.

    F-07 — la reco pentest exige de proscrire le passage du jeton en
    paramètre d'URL sur TOUS les endpoints, y compris les usages non-auth.
    Cette fonction est utilisée par le middleware de rate-limit pour
    bucketer par `user_id` plutôt que par IP quand l'utilisateur est
    connu. On lit uniquement le header Authorization et le cookie
    httpOnly `ma2e_token` ; le fallback `?token=` a été retiré. Si aucun
    token n'est présent, le bucket retombera automatiquement sur `ip:`
    (rate-limit avec key_strategy `user_or_ip`).
    """
    auth = request.headers.get("authorization") or ""
    token: str | None = None
    if auth.startswith("Bearer "):
        token = auth[7:]
    else:
        # F-07 — plus de fallback query string. On lit le cookie httpOnly
        # `ma2e_token` pour continuer à bucketer par user_id sur les
        # sessions cookie-only (mode nominal Phase 2).
        token = request.cookies.get(settings.auth_cookie_name)
    if not token:
        return None
    try:
        payload = decode_token(token)
        return payload.get("sub")
    except Exception:
        return None


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Remplit `request_context.current()` avec l'IP et le user-agent."""

    async def dispatch(self, request: Request, call_next):
        ip = _extract_client_ip(request)
        ua = (request.headers.get("user-agent") or "")[:512]
        set_current(RequestContext(ip_address=ip, user_agent=ua))
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """F-08 — anonymise les headers qui divulguent la pile technique.

    Écrase `Server: uvicorn` par une valeur générique, retire tout
    `X-Powered-By` éventuel, et ajoute quelques en-têtes de sécurité
    de base cohérents avec le reste de l'application.
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["server"] = "MA2E"
        if "x-powered-by" in response.headers:
            del response.headers["x-powered-by"]
        response.headers.setdefault("x-content-type-options", "nosniff")
        response.headers.setdefault("x-frame-options", "DENY")
        response.headers.setdefault("referrer-policy", "strict-origin-when-cross-origin")
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Applique les règles de rate limit définies dans `app.core.rate_limit`.

    Renvoie 429 avec un header `Retry-After` en cas de dépassement.
    Fail-open si Redis KO (log seulement) — la disponibilité prime.
    """

    async def dispatch(self, request: Request, call_next):
        rule = find_rule(request.method, request.url.path)
        if rule is None:
            return await call_next(request)

        # Construction de la clé de bucket
        ip = _extract_client_ip(request)
        if rule.key_strategy == "user_or_ip":
            user_id = _extract_user_id_from_jwt(request)
            bucket_id = f"user:{user_id}" if user_id else f"ip:{ip}"
        else:  # "ip"
            bucket_id = f"ip:{ip}"

        bucket_key = f"{rule.label}:{bucket_id}"
        allowed, count = await check_rate_limit(bucket_key, rule.limit, rule.window_seconds)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Trop de requêtes. Réessayez dans quelques instants.",
                    "limit": rule.limit,
                    "window_seconds": rule.window_seconds,
                },
                headers={"Retry-After": str(rule.window_seconds)},
            )
        return await call_next(request)


# ORDRE : RateLimit AVANT RequestContext pour bloquer les requêtes abusives
# le plus tôt possible, avant même de peupler le contexte.
class CSRFMiddleware(BaseHTTPMiddleware):
    """Vérifie le jeton CSRF (double-submit cookie) sur toute mutation.

    Le cookie `ma2e_csrf` est posé au login (non-httpOnly, lisible par JS).
    Le frontend doit le lire et le réémettre en header `X-CSRF-Token` sur
    toute requête qui modifie l'état (POST, PUT, DELETE, PATCH).

    Sont EXCLUS :
    - GET / HEAD / OPTIONS (aucune mutation, protection Same-Site du cookie
      httpOnly suffit)
    - Endpoints d'authentification (login, mfa/verify, ad/login) : l'utilisateur
      n'a pas encore de cookie CSRF avant de se connecter
    - Webhooks entrants (Meta WhatsApp, notifications externes) : les serveurs
      externes ne peuvent pas transmettre de header custom
    """

    # Chemins EXCLUS de la vérification CSRF (préfixes)
    EXEMPT_PREFIXES: tuple[str, ...] = (
        "/api/auth/login",
        "/api/auth/mfa/verify",
        "/api/auth/ad/login",
        "/api/auth/logout",      # idempotent, sûr
        "/api/auth/refresh",     # protégé par le cookie httpOnly SameSite du refresh
        "/webhooks/",
    )

    async def dispatch(self, request: Request, call_next):
        method = request.method.upper()
        if method in ("GET", "HEAD", "OPTIONS"):
            return await call_next(request)

        path = request.url.path
        if any(path.startswith(p) for p in self.EXEMPT_PREFIXES):
            return await call_next(request)

        cookie_token = request.cookies.get(settings.auth_csrf_cookie_name)
        header_token = request.headers.get("x-csrf-token")

        # Si aucun cookie CSRF n'est présent → l'utilisateur n'est pas
        # authentifié par cookie (ancien flux Bearer). On laisse passer
        # pour préserver la compatibilité durant la transition.
        if not cookie_token:
            return await call_next(request)

        # Cookie présent → header obligatoire ET identique.
        if not header_token or not secrets_compare(cookie_token, header_token):
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF token missing or invalid."},
            )
        return await call_next(request)


# ORDRE d'ajout (LIFO, donc premier ajouté = dernier exécuté) :
#   Requête entrante → CORS → CSRF → RateLimit → RequestContext → route
# Les 3 middlewares custom sont ajoutés dans l'ordre INVERSE d'exécution
# souhaité (Starlette empile en LIFO).
app.add_middleware(RequestContextMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(CSRFMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-CSRF-Token"],
    max_age=600,
)

# F-11 — les erreurs de validation Pydantic levées à l'intérieur d'une route
# (ex : parsing d'un payload en dehors du modèle FastAPI) remontaient en 500
# et exposaient une stack trace. On les convertit désormais en 400 propres,
# aussi cohérents que ceux émis par la validation FastAPI (RequestValidationError).
from pydantic import ValidationError as _PydanticValidationError

@app.exception_handler(_PydanticValidationError)
async def _handle_pydantic_validation_error(request: Request, exc: _PydanticValidationError):
    return JSONResponse(
        status_code=400,
        content={
            "detail": "Requête invalide : les données ne respectent pas le schéma attendu.",
            "errors": [
                {
                    "loc": list(err.get("loc") or []),
                    "msg": err.get("msg") or "invalid",
                    "type": err.get("type") or "value_error",
                }
                for err in exc.errors()[:20]
            ],
        },
    )


app.include_router(auth_api.router)
app.include_router(me_api.router)
app.include_router(dossiers_api.router)
app.include_router(knowledge_api.router)
app.include_router(audit_api.router)
app.include_router(settings_api.router)
app.include_router(templates_api.router)
app.include_router(users_api.router)
app.include_router(security_api.router)
app.include_router(stats_api.router)
app.include_router(integrations_api.router)
app.include_router(duplicates_api.router)
app.include_router(employeurs_api.router)
app.include_router(collaborateurs_api.router)
app.include_router(imports_api.router)
app.include_router(otp_api.router)
app.include_router(roles_api.router)
app.include_router(workflows_api.router)
app.include_router(health_api.router)
app.include_router(web_webhook.router)
app.include_router(whatsapp_webhook.router)


@app.get("/")
async def root():
    return {
        "service": "ma2e-identification-platform",
        "env": settings.app_env,
        "status": "ok",
        "version": app.version,
    }


@app.get("/health")
async def health_legacy():
    """Legacy endpoint conservé pour compat. Préférer /health/liveness."""
    return {"status": "healthy"}
