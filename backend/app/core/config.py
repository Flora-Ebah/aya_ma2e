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
    jwt_expire_minutes: int = 1440

    groq_api_key: str
    groq_model: str = "llama-3.3-70b-versatile"

    mindee_api_key: str = ""
    mindee_model_id: str = ""

    whatsapp_verify_token: str = "verify_me"

    # Azure OpenAI Embeddings (text-embedding-3-small, 1536 dims)
    azure_openai_embedding: str = ""
    azure_openai_api_key_embedding: str = ""

    app_env: str = "development"
    app_base_url: str = "http://localhost:8000"
    public_webhook_url: str = ""

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
