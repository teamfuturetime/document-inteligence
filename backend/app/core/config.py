from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Vietnamese Document Intelligence"
    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "sqlite:///./documents.db"
    storage_dir: str = "./uploads"
    max_upload_mb: int = 15
    cors_origins: str = "http://localhost:5173"
    ocr_engine: str = "mock"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
