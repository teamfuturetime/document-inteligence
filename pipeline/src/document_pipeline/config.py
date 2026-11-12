import hashlib
import json

from pydantic import Field, field_validator

from document_pipeline.models import Model


class PipelineConfig(Model):
    version: str = "inference-config-1.1.0"
    max_upload_bytes: int = Field(default=5_242_880, gt=0, le=20_971_520)
    max_image_pixels: int = Field(default=16_000_000, gt=0, le=40_000_000)
    timeout_seconds: float = Field(default=30.0, gt=0, le=120, allow_inf_nan=False)
    psm: int = 6
    rotation: int = 0
    scale: float = Field(default=1.0, ge=0.5, le=2.0, allow_inf_nan=False)
    autocontrast: bool = False
    minimum_field_ocr_score: float = Field(default=0.5, ge=0, le=1, allow_inf_nan=False)

    @field_validator("psm")
    @classmethod
    def recognition_mode(cls, value: int) -> int:
        if value not in (3, 4, 6, 11):
            raise ValueError("psm must be 3, 4, 6 or 11; no implicit OSD model")
        return value

    @field_validator("rotation")
    @classmethod
    def quarter_turn(cls, value: int) -> int:
        if value not in (0, 90, 180, 270):
            raise ValueError("rotation must be 0, 90, 180 or 270 clockwise")
        return value

    @property
    def sha256(self) -> str:
        content = json.dumps(self.model_dump(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(content.encode()).hexdigest()
