from dataclasses import dataclass
import math
import os
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    mode: str
    tessdata_dir: Path
    processing_timeout: float = 30

    def __post_init__(self):
        if self.mode not in {"real", "mock"}:
            raise ValueError("VDI_MODE must be real or mock")
        if not math.isfinite(self.processing_timeout) or self.processing_timeout <= 0:
            raise ValueError("processing_timeout must be finite and positive")

    @classmethod
    def from_environment(cls):
        return cls(os.environ.get("VDI_MODE", "real"),
                   Path(os.environ.get("VDI_TESSDATA_DIR", "data/models/tessdata")).resolve())
