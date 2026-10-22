"""Application settings loaded from environment variables."""
from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Cấu hình ứng dụng đọc từ .env / environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Ứng dụng
    APP_NAME: str = "Document Intelligence Vietnamese"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str = "dev-secret-key"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    SESSION_COOKIE_NAME: str = "di_session"
    SESSION_COOKIE_SECURE: bool = False

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    # Database
    DATABASE_URL: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/documents"
    )

    # Lưu trữ
    STORAGE_BACKEND: str = "local"
    STORAGE_PATH: str = "./storage/uploads"
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_EXTENSIONS: List[str] = ["pdf", "jpg", "jpeg", "png"]

    # AI Service
    AI_SERVICE_URL: str = "http://localhost:8001"
    OCR_ENGINE: str = "tesseract"
    OCR_LANG: str = "vie"
    OCR_FALLBACK_ENABLED: bool = False
    AI_SERVICE_TIMEOUT_SECONDS: float = 120.0

    DATA_RETENTION_DAYS: int = 30
    CLASSIFICATION_REVIEW_THRESHOLD: float = 70.0

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    @field_validator("DEBUG", mode="before")
    @classmethod
    def _parse_debug(cls, value: object) -> object:
        # Một số môi trường đặt DEBUG=release/debug thay vì boolean.
        if isinstance(value, str) and value.lower() in {"release", "production"}:
            return False
        if isinstance(value, str) and value.lower() == "debug":
            return True
        return value

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_cors(cls, value: object) -> object:
        """Cho phép truyền dạng chuỗi JSON hoặc list."""
        if isinstance(value, str):
            import json

            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("ALLOWED_EXTENSIONS", mode="before")
    @classmethod
    def _parse_extensions(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip().lower() for item in value.split(",") if item.strip()]
        return value

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Trả về settings đã cache (chỉ đọc 1 lần)."""
    return Settings()
