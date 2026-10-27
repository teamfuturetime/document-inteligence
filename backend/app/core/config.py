from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="Vietnamese Document Intelligence", min_length=1)
    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = Field(default="sqlite:///./documents.db", min_length=1)
    storage_dir: str = Field(default="./uploads", min_length=1)
    max_upload_mb: int = Field(default=15, gt=0)
    cors_origins: str = "http://localhost:5173"
    ocr_engine: str = "mock"
    api_key: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
