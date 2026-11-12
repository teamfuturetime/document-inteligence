import shutil
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DOCINTEL_", env_file=ROOT / ".env", extra="ignore"
    )
    provider_mode: Literal["unconfigured", "fixture", "tesseract"] = "unconfigured"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    max_upload_bytes: int = Field(default=5_242_880, gt=0, le=20_971_520)
    max_image_pixels: int = Field(default=16_000_000, gt=0, le=40_000_000)
    max_pages: int = Field(default=1, ge=1, le=1)
    provider_timeout_seconds: int = Field(default=30, gt=0, le=120)
    runtime_dir: Path = ROOT / "runtime/app"
    tesseract_executable: str = Field(
        default_factory=lambda: (
            shutil.which("tesseract")
            or (
                "C:/Program Files/Tesseract-OCR/tesseract.exe"
                if Path("C:/Program Files/Tesseract-OCR/tesseract.exe").is_file()
                else "tesseract"
            )
        )
    )
    tessdata_dir: Path = ROOT / "runtime/models/tessdata_fast"
    max_pending_runs: int = Field(default=5, ge=1, le=20)
    notification_mode: Literal["disabled", "log"] = "log"
    notification_timeout_seconds: float = Field(default=0.05, gt=0, le=1)
