from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_ENV: str = "local"
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: str = "http://localhost:5173"

    # Login & Auth
    JWT_SECRET_KEY: str = "secret-key-must-be-changed-in-production-min-32-chars"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_MINUTES: int = 30
    REFRESH_TOKEN_DAYS: int = 7

    # Neon (PostgreSQL)
    DATABASE_URL: str = ""
    DATABASE_URL_DIRECT: str = ""

    # Qdrant
    QDRANT_URL: str = ""
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION: str = "enterprise_docs"

    # Embeddings
    JINA_API_KEY: str = ""
    EMBEDDING_MODEL: str = "jina-embeddings-v3"
    EMBEDDING_DIM: int = 1024
    RERANKER_MODEL: str = "jina-reranker-v2-base-multilingual"
    SPARSE_MODEL: str = "Qdrant/bm25"

    # LLM
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_FALLBACK_MODEL: str = "llama-3.1-8b-instant"
    LLM_CONTEXT_TOKEN_BUDGET: int = 3000

    # File storage (Backblaze B2, S3-compatible)
    STORAGE_BACKEND: str = "b2"  # b2 or local
    B2_KEY_ID: str = ""
    B2_APPLICATION_KEY: str = ""
    B2_BUCKET_NAME: str = ""
    B2_ENDPOINT_URL: str = ""
    B2_REGION: str = ""
    LOCAL_STORAGE_DIR: str = "./data/uploads"

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env", "../.env"), env_file_encoding="utf-8", extra="ignore"
    )

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
