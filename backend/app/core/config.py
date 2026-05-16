from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), extra="ignore")

    database_url: str
    database_url_sync: str
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


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
