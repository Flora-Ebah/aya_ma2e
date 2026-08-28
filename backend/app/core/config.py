from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), extra="ignore")

    database_url: str
    database_url_sync: str = ""
    redis_url: str = "redis://localhost:6379/0"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False

    jwt_secret: str
    jwt_algorithm: str = "HS256"
    # 60 minutes par défaut (Phase 2 sécurité : réduction depuis 8h). Justification :
    # l'IdleGuard côté frontend déconnecte déjà après 20 min d'inactivité, et une
    # session courte réduit la fenêtre d'exploitation en cas de vol de cookie.
    # Peut être remonté ponctuellement via l'env JWT_EXPIRE_MINUTES (ex. 480 pour
    # rétablir l'ancien comportement 8h ouvrées si besoin métier).
    jwt_expire_minutes: int = 60

    # === Provider IA legacy (gardé pour compat / fallback éventuel) ===
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    mindee_api_key: str = ""
    mindee_model_id: str = ""

    whatsapp_verify_token: str = "verify_me"
    # App Secret Meta (Facebook Developers → App → Settings → Basic).
    # Utilisé pour vérifier X-Hub-Signature-256 sur les webhooks entrants (F-04).
    # Si vide ET app_env != production : les signatures ne sont pas vérifiées
    # (dev-friendly). En prod, l'absence de secret refuse TOUS les webhooks.
    whatsapp_app_secret: str = ""

    # ====================================================================== #
    # Azure OpenAI — Chat (gpt-5.4-mini ou autre déploiement)
    # Endpoint sur le format `https://<resource>.cognitiveservices.azure.com/`
    # Utilise la Responses API → api-version 2025-04-01-preview
    # ====================================================================== #
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment: str = "gpt-5.4-mini"
    azure_openai_api_version: str = "2025-04-01-preview"

    # ====================================================================== #
    # Azure OpenAI Embeddings (text-embedding-3-small, 1536 dims)
    # Resource séparée (chat-genai)
    # ====================================================================== #
    azure_openai_embedding: str = ""
    azure_openai_api_key_embedding: str = ""

    # ====================================================================== #
    # Azure AI Vision — OCR (Read API)
    # Endpoint format `https://<resource>.cognitiveservices.azure.com/`
    # Utilisé par `services/ocr_azure_vision.py`
    # ====================================================================== #
    azure_ai_vision_endpoint: str = ""
    azure_ai_vision_api_key: str = ""

    # ====================================================================== #
    # OCR.space — fournisseur gratuit utilisé pour les recettes.
    # Free tier : 25 000 req/mois, 500 req/jour/IP, 1 MB max par fichier.
    # https://ocr.space/ocrapi → bouton "Free API key" pour s'inscrire.
    # Toggle entre OCR.space ↔ Azure Vision via setting `services.ocr_provider`.
    # ====================================================================== #
    ocr_space_api_key: str = ""
    ocr_space_endpoint: str = "https://api.ocr.space/parse/image"

    # SMTP (MailHog en dev, vrai SMTP en prod)
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = False
    smtp_from_email: str = "no-reply@ma2e.ci"
    smtp_from_name: str = "MA2E Notifications"
    smtp_test_mode: bool = False  # si True, on n'envoie pas vraiment (utile pour tests unitaires)

    app_env: str = "development"
    app_base_url: str = "http://localhost:8000"
    public_webhook_url: str = ""

    # ── Sécurité — authentification par cookie httpOnly (Phase 2) ──
    # Nom du cookie de session JWT (httpOnly, non-lisible par JS).
    auth_cookie_name: str = "ma2e_token"
    # Nom du cookie CSRF associé (lisible par JS, envoyé en header X-CSRF-Token).
    auth_csrf_cookie_name: str = "ma2e_csrf"
    # Nom du cookie refresh token (httpOnly, path=/api/auth pour scope réduit).
    auth_refresh_cookie_name: str = "ma2e_refresh"
    # Secure=True en prod HTTPS. Passer à False en dev HTTP.
    auth_cookie_secure: bool = True
    # SameSite : "strict" (max sécu, back-office same-origin) ou "lax" (nécessaire cross-origin dev).
    auth_cookie_samesite: str = "lax"
    # Domaine explicite du cookie (vide = domaine de la requête).
    auth_cookie_domain: str = ""
    # Durée du refresh token en jours (rotation à chaque usage).
    refresh_expire_days: int = 7

    # ── CORS ──
    # Liste séparée par virgules des origines autorisées.
    # Défaut : autorise les origines habituelles dev + prod pilote MA2E.
    cors_origins: str = (
        "http://localhost:3000,"
        "http://localhost:3001,"
        "https://ma2e.swedencentral.cloudapp.azure.com"
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @model_validator(mode="after")
    def _normalise_db_urls(self) -> "Settings":
        # Railway (and most PaaS) emit postgresql:// — asyncpg needs +asyncpg scheme
        for old in ("postgres://", "postgresql://"):
            if self.database_url.startswith(old):
                self.database_url = self.database_url.replace(old, "postgresql+asyncpg://", 1)
                break
        # Auto-derive the sync URL (used by Alembic) when not explicitly set
        if not self.database_url_sync:
            self.database_url_sync = self.database_url.replace(
                "postgresql+asyncpg://", "postgresql://"
            )
        # Minio expects host:port only — strip any scheme or trailing slash
        for scheme in ("https://", "http://"):
            if self.minio_endpoint.startswith(scheme):
                self.minio_endpoint = self.minio_endpoint[len(scheme):]
                break
        self.minio_endpoint = self.minio_endpoint.rstrip("/")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
