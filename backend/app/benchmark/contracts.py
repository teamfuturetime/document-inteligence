"""Small benchmark boundary; labels never belong to provider input."""

from dataclasses import dataclass
import hashlib
import json
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.extraction import BoundingBox, DocumentInput, ProviderIdentity
from app.schemas.invoice import InvoiceValues

Mode = Literal["image-only", "ocr-text-only", "image+ocr"]
MODES: tuple[Mode, ...] = ("image-only", "ocr-text-only", "image+ocr")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_digest(value: object) -> str:
    return digest(json.dumps(value, ensure_ascii=True, sort_keys=True, allow_nan=False).encode())


class SourceSpan(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    id: str = Field(min_length=1)
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    page: Literal[1] = 1
    bbox: BoundingBox | None = None
    ocr_native_score: float | None = Field(default=None, ge=0, le=100, allow_inf_nan=False)


class OCRContext(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    document_id: str
    input_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    text: str
    text_sha256: str
    origin: Literal["synthetic_text_fixture", "tesseract_snapshot"]
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    spans: list[SourceSpan]
    provenance: dict[str, str]

    @model_validator(mode="after")
    def source_integrity(self) -> "OCRContext":
        if self.text_sha256 != digest(self.text.encode("utf-8")):
            raise ValueError("Source text hash mismatch")
        if len({span.id for span in self.spans}) != len(self.spans):
            raise ValueError("Source IDs must be unique")
        for span in self.spans:
            if not 0 <= span.start < span.end <= len(self.text):
                raise ValueError("Source span must fit text")
            if span.bbox and (span.bbox.x1 > self.width or span.bbox.y1 > self.height):
                raise ValueError("Source box must fit the EXIF-oriented image")
            if self.origin == "synthetic_text_fixture" and (span.bbox is not None or span.ocr_native_score is not None):
                raise ValueError("Synthetic text does not have measured OCR scores or coordinates")
        return self


class BenchmarkRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    sample_id: str
    mode: Mode
    image: DocumentInput | None
    ocr: OCRContext | None
    source_locale: Literal["vi-VN"] | None

    @model_validator(mode="after")
    def mode_inputs(self) -> "BenchmarkRequest":
        expected = {"image-only": (True, False), "ocr-text-only": (False, True), "image+ocr": (True, True)}
        if (self.image is not None, self.ocr is not None) != expected[self.mode]:
            raise ValueError("Inputs must match the selected mode")
        if self.image and self.image.document_id != self.sample_id:
            raise ValueError("Image ID mismatch")
        if self.ocr and self.ocr.document_id != self.sample_id:
            raise ValueError("OCR ID mismatch")
        if self.image and self.ocr and digest(self.image.content) != self.ocr.input_sha256:
            raise ValueError("OCR must reference the same source image")
        return self

    def fingerprint(self) -> str:
        return json_digest({
            "sample_id": self.sample_id, "mode": self.mode, "source_locale": self.source_locale,
            "image": None if self.image is None else {
                "media_type": self.image.media_type, "sha256": digest(self.image.content),
            }, "ocr": None if self.ocr is None else self.ocr.model_dump(),
        })


class BenchmarkIdentity(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    provider: ProviderIdentity
    model_id: str | None
    model_revision: str | None


class BenchmarkProvider(Protocol):
    @property
    def identity(self) -> BenchmarkIdentity: ...

    def respond(self, request: BenchmarkRequest) -> str: ...


@dataclass(frozen=True)
class BenchmarkCase:
    image: DocumentInput
    ocr: OCRContext | None
    source_locale: Literal["vi-VN"] | None
    ground_truth: InvoiceValues | None  # None = unannotated; all-null values = annotated negative.


@dataclass(frozen=True)
class BenchmarkDataset:
    cases: tuple[BenchmarkCase, ...]
    version: str
    manifest_sha256: str
    labels_version: str | None
    labels_sha256: str | None
    ocr_sources_sha256: str
