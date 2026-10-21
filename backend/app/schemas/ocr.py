"""OCR observations, separate from invoice candidates and field confidence."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.extraction import BoundingBox, ProviderIdentity


class OCRWord(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    text: str = Field(min_length=1)
    page: Literal[1]
    bbox: BoundingBox
    native_confidence: float | None = Field(ge=0, le=100, allow_inf_nan=False)


class OCRMetadata(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    provider: ProviderIdentity
    engine_version: str
    model_sha256: dict[str, str]
    configuration: dict[str, str | int | float]
    config_sha256: str
    pillow_version: str
    native_confidence_scale: Literal["tesseract_word_0_100"] = "tesseract_word_0_100"


class OCRResult(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    document_id: str
    input_sha256: str
    processed_image_sha256: str
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    coordinate_space: Literal["exif_transposed_rgb_white"] = "exif_transposed_rgb_white"
    raw_text: str
    raw_tsv: str
    words: list[OCRWord]
    metadata: OCRMetadata
    warnings: list[str]

    @model_validator(mode="after")
    def boxes_fit_image(self) -> "OCRResult":
        if any(word.bbox.x1 > self.width or word.bbox.y1 > self.height for word in self.words):
            raise ValueError("OCR boxes must fit the displayed source image")
        return self
