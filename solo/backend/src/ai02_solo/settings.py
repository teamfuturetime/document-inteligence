from dataclasses import dataclass
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class Settings:
    tessdata_dir: str = str(ROOT / ".models/tessdata")
    vlm_provider: str = "ollama"
    vlm_url: str = "http://127.0.0.1:11434"
    vlm_model: str = ""
    vlm_revision: str = ""
    deadline: int = 120

    @classmethod
    def from_env(cls):
        provider = os.getenv("SOLO_VLM_PROVIDER", "ollama")
        if provider not in {"ollama", "remote"}:
            raise ValueError("SOLO_VLM_PROVIDER must be ollama or remote")
        return cls(tessdata_dir=os.getenv("SOLO_TESSDATA_DIR", cls.tessdata_dir),
                   vlm_provider=provider,
                   vlm_url=os.getenv("SOLO_VLM_URL", cls.vlm_url).rstrip("/"),
                   vlm_model=os.getenv("SOLO_VLM_MODEL", ""),
                   vlm_revision=os.getenv("SOLO_VLM_REVISION", ""),
                   deadline=max(10, min(300, int(os.getenv("SOLO_DEADLINE", "120")))))
