import os
import secrets
import logging
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    PROJECT_NAME: str = "CampusMate AI"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://campusmate_user:campusmate_secure_pass_2026@localhost:5432/campusmate"
    )

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # MinIO / Object Storage
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ROOT_USER", "campusmate_minio")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_ROOT_PASSWORD", "minio_secure_pass_2026")
    MINIO_BUCKET_NAME: str = os.getenv("MINIO_BUCKET_NAME", "documents")
    MINIO_USE_SSL: bool = os.getenv("MINIO_USE_SSL", "false").lower() == "true"

    # Security & JWT
    JWT_SECRET: str = os.getenv("JWT_SECRET") or secrets.token_hex(32)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # LLM & AI Engine
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")

    # Business thresholds
    CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.65"))
    RETRIEVAL_SIMILARITY_THRESHOLD: float = float(os.getenv("RETRIEVAL_SIMILARITY_THRESHOLD", "0.35"))

    # Vector dimension for BGE-M3
    VECTOR_DIM: int = 1024

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()

if not os.getenv("JWT_SECRET"):
    logger.warning("JWT_SECRET was not provided via environment. Generated ephemeral 32-byte secret for this instance.")

