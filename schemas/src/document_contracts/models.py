"""Phase 1 wire contracts, not OCR, extraction, or review services."""

from datetime import date
from typing import Annotated, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, AfterValidator, model_validator

SCHEMA_VERSION = "1.0.0"
MAX_SAFE_INTEGER = 9_007_199_254_740_991
FieldName = Literal[
    "invoice_number", "invoice_date", "seller_name", "total_amount", "currency"
]


def calendar_date(value: str) -> str:
    date.fromisoformat(value)
    return value


InvoiceNumber = Annotated[str, Field(min_length=1, max_length=100, pattern=r"\S")]
SellerName = Annotated[str, Field(min_length=1, max_length=200, pattern=r"\S")]
ISODate = Annotated[
    str, Field(pattern=r"^\d{4}-\d{2}-\d{2}$", json_schema_extra={"format": "date"}),
    AfterValidator(calendar_date),
]
Amount = Annotated[int, Field(ge=0, le=MAX_SAFE_INTEGER)]
Confidence = Annotated[float, Field(ge=0, le=1)]
Version = Annotated[str, Field(min_length=1, max_length=120)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class InvoiceValues(Contract):
    """All keys required; null explicitly represents a missing value."""

    invoice_number: InvoiceNumber | None
    invoice_date: ISODate | None
    seller_name: SellerName | None
    total_amount: Amount | None
    currency: Literal["VND"] | None


class FinalInvoiceValues(Contract):
    invoice_number: InvoiceNumber
    invoice_date: ISODate
    seller_name: SellerName
    total_amount: Amount
    currency: Literal["VND"]


class BoundingBox(Contract):
    x0: Annotated[int, Field(ge=0)]
    y0: Annotated[int, Field(ge=0)]
    x1: Annotated[int, Field(gt=0)]
    y1: Annotated[int, Field(gt=0)]

    @model_validator(mode="after")
    def positive_area(self):
        if self.x1 <= self.x0 or self.y1 <= self.y0:
            raise ValueError("Bounding box must have positive area")
        return self


class Evidence(Contract):
    text: Annotated[str, Field(min_length=1)]
    page: Literal[1]
    box: BoundingBox


T = TypeVar("T")


class ExtractedField(Contract, Generic[T]):
    value: T | None
    confidence: Confidence | None
    evidence: list[Evidence]
    warnings: list[str]

    @model_validator(mode="after")
    def missing_has_no_score(self):
        if self.value is None and self.confidence is not None:
            raise ValueError("Missing value cannot have an extraction confidence")
        return self


class ExtractedFields(Contract):
    invoice_number: ExtractedField[InvoiceNumber]
    invoice_date: ExtractedField[ISODate]
    seller_name: ExtractedField[SellerName]
    total_amount: ExtractedField[Amount]
    currency: ExtractedField[Literal["VND"]]


class ExtractionResponse(Contract):
    schema_version: Literal["1.0.0"]
    document_id: Annotated[str, Field(min_length=1, max_length=100)]
    mode: Literal["mock", "real"]
    pipeline_version: Version
    ocr_version: Version
    config_version: Version
    fields: ExtractedFields
    warnings: list[str]


class ReviewedValues(Contract):
    """Raw browser input; services later normalize these strings."""

    invoice_number: Annotated[str, Field(max_length=1000)] | None
    invoice_date: Annotated[str, Field(max_length=1000)] | None
    seller_name: Annotated[str, Field(max_length=1000)] | None
    total_amount: Annotated[str, Field(max_length=1000)] | None
    currency: Annotated[str, Field(max_length=1000)] | None


class ValidationRequest(Contract):
    schema_version: Literal["1.0.0"]
    values: ReviewedValues


class FieldError(Contract):
    field: FieldName
    code: Literal["required", "invalid_format", "invalid_date", "out_of_range", "unsupported_currency"]
    message: Annotated[str, Field(min_length=1)]


class ValidationResponse(Contract):
    schema_version: Literal["1.0.0"]
    valid: bool
    normalized_values: InvoiceValues
    errors: list[FieldError]

    @model_validator(mode="after")
    def consistent_result(self):
        values = self.normalized_values.model_dump()
        missing = {key for key, value in values.items() if value is None}
        error_fields = {error.field for error in self.errors}
        if self.valid:
            if self.errors or missing:
                raise ValueError("Valid response must contain all values and no errors")
        elif not self.errors or missing != error_fields:
            raise ValueError("Invalid response must mark each invalid value null with a field error")
        return self


class APIErrorDetail(Contract):
    code: Literal[
        "file_too_large", "unsupported_media_type", "invalid_document",
        "multiple_pages", "image_too_large", "invalid_request",
        "ocr_unavailable", "processing_timeout", "internal_error",
    ]
    message: Annotated[str, Field(min_length=1)]
    field: FieldName | None


class APIErrorResponse(Contract):
    error: APIErrorDetail


class HealthResponse(Contract):
    status: Literal["ok"]
    mode: Literal["mock", "real"]
    ocr_ready: bool


class OCRToken(Contract):
    text: Annotated[str, Field(min_length=1)]
    confidence: Confidence | None
    box: BoundingBox


class OCRPage(Contract):
    page: Literal[1]
    width: Annotated[int, Field(gt=0)]
    height: Annotated[int, Field(gt=0)]
    # Row-major 3x3 transform from processed pixel coordinates to original image.
    to_original: Annotated[list[float], Field(min_length=9, max_length=9)]
    tokens: list[OCRToken]

    @model_validator(mode="after")
    def boxes_within_page(self):
        for token in self.tokens:
            if token.box.x1 > self.width or token.box.y1 > self.height:
                raise ValueError("Token bounding box exceeds page dimensions")
        return self


class OCRResult(Contract):
    schema_version: Literal["1.0.0"]
    mode: Literal["mock", "real"]
    ocr_version: Version
    language: Literal["vie+eng"]
    page: OCRPage


class ReviewedExport(Contract):
    schema_version: Literal["1.0.0"]
    original_extraction: ExtractionResponse
    values: FinalInvoiceValues
    edited_fields: list[FieldName]

    @model_validator(mode="after")
    def edits_match_values(self):
        original = self.original_extraction.fields
        changed = {
            key for key, value in self.values.model_dump().items()
            if getattr(original, key).value != value
        }
        if len(set(self.edited_fields)) != len(self.edited_fields) or set(self.edited_fields) != changed:
            raise ValueError("edited_fields must exactly match changed normalized values")
        return self


CONTRACT_MODELS = {
    "invoice-values": InvoiceValues,
    "final-invoice-values": FinalInvoiceValues,
    "extraction-response": ExtractionResponse,
    "validation-request": ValidationRequest,
    "validation-response": ValidationResponse,
    "api-error": APIErrorResponse,
    "health-response": HealthResponse,
    "ocr-result": OCRResult,
    "reviewed-export": ReviewedExport,
}
