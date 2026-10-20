"""Small provider/pipeline contracts around sales_invoice 1.0.0 values.

Provider raw candidates are deliberately separate from canonical validation and
from the future reviewed/exported document. No OCR confidence is represented here.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.invoice import InvoiceValues
from app.schemas.validation import FieldName, ValidationResult


class DocumentInput(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    document_id: str = Field(min_length=1)
    media_type: Literal["image/png", "image/jpeg"]
    content: bytes = Field(min_length=1, repr=False)


class ProviderIdentity(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    name: str = Field(min_length=1, pattern=r"\S")
    implementation_version: str = Field(min_length=1, pattern=r"\S")
    config_version: str = Field(min_length=1, pattern=r"\S")
    mode: Literal["fake", "real"]


class BoundingBox(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    x0: int = Field(ge=0)
    y0: int = Field(ge=0)
    x1: int = Field(gt=0)
    y1: int = Field(gt=0)

    @model_validator(mode="after")
    def positive_area(self) -> "BoundingBox":
        if self.x1 <= self.x0 or self.y1 <= self.y0:
            raise ValueError("Evidence box must have positive area")
        return self


class Evidence(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    page: Literal[1]
    bbox: BoundingBox | None


class FieldConfidence(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    score: float = Field(ge=0, le=1, allow_inf_nan=False)
    source: Literal["ocr_aggregation", "calibrated_extraction"]
    method_version: str = Field(min_length=1)
    calibration_version: str | None
    evidence_ids: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def calibrated_source_has_version(self) -> "FieldConfidence":
        if self.source == "calibrated_extraction" and not self.calibration_version:
            raise ValueError("Calibrated extraction requires a calibration version")
        return self


class FieldMetadata(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    confidence: FieldConfidence | None
    evidence: list[Evidence]


class ProviderOutput(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    raw_values: dict[FieldName, str | int | None]
    source_locale: Literal["vi-VN"] | None
    uncertain_fields: list[FieldName]
    field_metadata: dict[FieldName, FieldMetadata]
    ocr_text: str | None
    warnings: list[str]

    @model_validator(mode="after")
    def consistent_fields(self) -> "ProviderOutput":
        fields = set(InvoiceValues.model_fields)
        if set(self.raw_values) != fields or set(self.field_metadata) != fields:
            raise ValueError("Raw values and metadata must contain exactly the five invoice keys")
        if len(self.uncertain_fields) != len(set(self.uncertain_fields)):
            raise ValueError("Uncertain fields must be unique")
        for field, value in self.raw_values.items():
            if field != "total_amount" and value is not None and not isinstance(value, str):
                raise ValueError("Only raw total_amount may be an integer")
            metadata = self.field_metadata[field]
            ids = [item.id for item in metadata.evidence]
            if len(ids) != len(set(ids)):
                raise ValueError("Evidence IDs must be unique within each field")
            if metadata.confidence is not None:
                if value is None or field in self.uncertain_fields:
                    raise ValueError("Unavailable/uncertain fields cannot have confidence")
                if not set(metadata.confidence.evidence_ids).issubset(ids):
                    raise ValueError("Confidence must reference evidence of the same field")
        return self


class RunMetadata(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    run_id: str
    content_sha256: str
    provider: ProviderIdentity
    pipeline_version: str
    normalization_version: str
    code_revision: str | None


class PipelineSuccess(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    status: Literal["succeeded"] = "succeeded"
    document_id: str
    document_type: Literal["sales_invoice"] = "sales_invoice"
    schema_version: Literal["1.0.0"] = "1.0.0"
    run_metadata: RunMetadata
    provider_output: ProviderOutput
    validation: ValidationResult


class PipelineError(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    code: Literal[
        "invalid_input", "invalid_provider_output", "provider_unavailable",
        "provider_timeout", "provider_failed", "invalid_document",
    ]
    message: str


class PipelineFailure(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    status: Literal["failed"] = "failed"
    document_id: str | None
    document_type: Literal["sales_invoice"] = "sales_invoice"
    schema_version: Literal["1.0.0"] = "1.0.0"
    run_metadata: RunMetadata | None
    error: PipelineError
