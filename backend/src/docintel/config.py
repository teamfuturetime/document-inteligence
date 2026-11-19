import shutil
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DOCINTEL_", env_file=ROOT / ".env", extra="ignore"
    )
    provider_mode: Literal["unconfigured", "fixture", "tesseract"] = "unconfigured"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    max_upload_bytes: int = Field(default=5_242_880, gt=0, le=20_971_520)
    upload_receive_timeout_seconds: float = Field(default=30.0, gt=0, le=120)
    max_concurrent_uploads: int = Field(default=2, ge=1, le=8)
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
    auth_mode: Literal["local", "session"] = "local"
    session_cookie_secure: bool = True
    session_ttl_seconds: int = Field(default=28_800, ge=60, le=86_400)
    max_login_attempts: int = Field(default=20, ge=1, le=100)
    login_window_seconds: int = Field(default=60, ge=10, le=3600)

    notification_mode: Literal["disabled", "log"] = "log"
    notification_timeout_seconds: float = Field(default=0.05, gt=0, le=1)

    @model_validator(mode="after")
    def validate_session_origins(self):
        if self.auth_mode == "session":
            if not self.cors_origins or len(self.cors_origins) > 10:
                raise ValueError("Session mode requires a bounded exact origin allowlist")
            for origin in self.cors_origins:
                parsed = urlsplit(origin)
                if (
                    parsed.scheme not in {"http", "https"}
                    or not parsed.hostname
                    or parsed.username
                    or parsed.password
                    or parsed.path
                    or parsed.query
                    or parsed.fragment
                    or "*" in origin
                ):
                    raise ValueError("Session origins must be exact HTTP(S) origins")
                _ = parsed.port
                if not self.session_cookie_secure and parsed.hostname not in {
                    "localhost",
                    "127.0.0.1",
                    "::1",
                }:
                    raise ValueError(
                        "Insecure session cookies are limited to explicit loopback profiles"
                    )
        return self
