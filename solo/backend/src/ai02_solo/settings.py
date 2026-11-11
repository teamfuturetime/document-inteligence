from dataclasses import dataclass
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class Settings:
    ocr_provider: str = "tesseract"
    tessdata_dir: str = str(ROOT / ".models/tessdata")
    ocrspace_engine: int = 2
    ocrspace_key_file: str = str(ROOT / ".secrets/ocrspace.key")
    vlm_provider: str = "ollama"
    vlm_url: str = "http://127.0.0.1:11434"
    vlm_model: str = ""
    vlm_revision: str = ""
    deadline: int = 120

    @classmethod
    def from_env(cls):
        ocr_provider = os.getenv("SOLO_OCR_PROVIDER", "tesseract")
        if ocr_provider not in {"tesseract", "ocrspace"}:
            raise ValueError("SOLO_OCR_PROVIDER must be tesseract or ocrspace")
        engine = int(os.getenv("SOLO_OCRSPACE_ENGINE", "2"))
        if engine not in {2, 3}:
            raise ValueError("SOLO_OCRSPACE_ENGINE must be 2 or 3")
        provider = os.getenv("SOLO_VLM_PROVIDER", "ollama")
        if provider not in {"ollama", "remote"}:
            raise ValueError("SOLO_VLM_PROVIDER must be ollama or remote")
        return cls(ocr_provider=ocr_provider, ocrspace_engine=engine,
                   ocrspace_key_file=os.getenv("SOLO_OCRSPACE_KEY_FILE", cls.ocrspace_key_file),
                   tessdata_dir=os.getenv("SOLO_TESSDATA_DIR", cls.tessdata_dir),
                   vlm_provider=provider,
                   vlm_url=os.getenv("SOLO_VLM_URL", cls.vlm_url).rstrip("/"),
                   vlm_model=os.getenv("SOLO_VLM_MODEL", ""),
                   vlm_revision=os.getenv("SOLO_VLM_REVISION", ""),
                   deadline=max(10, min(300, int(os.getenv("SOLO_DEADLINE", "120")))))
