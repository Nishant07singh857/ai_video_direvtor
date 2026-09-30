from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    APP_NAME: str = "AI Video Director"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    PUBLIC_API_URL: str = "http://127.0.0.1:8000"

    # Database - PostgreSQL as primary (per spec)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/ai_video_director"
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres@127.0.0.1:5432/ai_video_director"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS
    BACKEND_CORS_ORIGINS: str | list[str] = "http://localhost:3000"

    # Media Storage
    MEDIA_STORAGE_ROOT: str = "./media"

    # FFmpeg/FFprobe paths
    FFMPEG_PATH: Optional[str] = None
    FFPROBE_PATH: Optional[str] = None

    # Upload limits
    MAX_UPLOAD_SIZE: int = 5 * 1024 * 1024 * 1024  # 5 GB

    # Storage (for Phase 2+)
    STORAGE_PROVIDER: str = "local"
    S3_ENDPOINT: Optional[str] = None
    S3_ACCESS_KEY: Optional[str] = None
    S3_SECRET_KEY: Optional[str] = None
    S3_BUCKET: Optional[str] = None

    # AI provider.  Credentials and model identifiers belong in the runtime
    # environment, never in source code or a committed project file.
    LLM_API_URL: Optional[str] = None
    LLM_API_KEY: Optional[str] = None
    LLM_MODEL: str = ""
    LLM_TIMEOUT_SECONDS: float = 60.0
    LLM_ENABLED: bool = False
    ALLOW_MOCK_AI: bool = False

    # Queue/render behaviour.
    RENDER_SYNC_FALLBACK: bool = True
    CELERY_ENABLED: bool = False
    CELERY_TASK_ALWAYS_EAGER: bool = False

    @property
    def cors_origins(self) -> list[str]:
        if isinstance(self.BACKEND_CORS_ORIGINS, list):
            return [origin.strip() for origin in self.BACKEND_CORS_ORIGINS if origin.strip()]
        return [origin.strip() for origin in self.BACKEND_CORS_ORIGINS.split(",") if origin.strip()]

    def model_post_init(self, __context: object) -> None:
        environment = self.ENVIRONMENT.strip().lower()
        if not self.SECRET_KEY:
            if environment in {"development", "test", "testing"}:
                self.SECRET_KEY = "dev-only-secret-replace-before-production"
            else:
                raise ValueError("SECRET_KEY must be set for non-development environments")
        if environment in {"production", "prod"}:
            if len(self.SECRET_KEY) < 32 or self.SECRET_KEY.startswith("dev-only-"):
                raise ValueError("SECRET_KEY must be a random value of at least 32 characters in production")
            if self.DEBUG:
                raise ValueError("DEBUG must be false in production")
            if "*" in self.cors_origins:
                raise ValueError("Wildcard CORS is not allowed in production")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
