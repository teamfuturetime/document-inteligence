from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DOCINTEL_", env_file=ROOT / ".env", extra="ignore"
    )
    provider_mode: Literal["unconfigured", "fixture"] = "unconfigured"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    max_upload_bytes: int = Field(default=5_242_880, gt=0)
    max_image_pixels: int = Field(default=16_000_000, gt=0)
    max_pages: int = Field(default=1, gt=0)
    provider_timeout_seconds: int = Field(default=30, gt=0)
