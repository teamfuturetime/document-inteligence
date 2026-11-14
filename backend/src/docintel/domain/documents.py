"""Canonical product contracts; foundation fixtures retain their independent v1 schema."""

import re
from datetime import date, datetime
from typing import Annotated, Literal

from document_pipeline.normalization import normalize
from pydantic import Field, field_validator, model_validator

from docintel.domain.models import Confidence, Contract, FinalApplicationData, Provenance

PRODUCT_SCHEMA_VERSION = "1.0.0"
DocumentType = Literal["hoa_don", "don_de_nghi"]
Value = Annotated[str, Field(max_length=16000)] | int | None
ProductFieldId = Literal[
    "invoice_number",
    "invoice_date",
    "seller_name",
    "total_amount",
    "currency",
    "full_name",
    "student_id",
    "date_of_birth",
    "class_name",
    "faculty",
    "request_content",
    "request_date",
]


class FieldDefinition(Contract):
    field_id: ProductFieldId
    label: str
    value_type: Literal["text", "date", "integer", "currency"]
    required: bool = True


DEFINITIONS: dict[str, list[FieldDefinition]] = {
    "hoa_don": [
        FieldDefinition(field_id=key, label=label, value_type=kind)
        for key, label, kind in (
            ("invoice_number", "Số hóa đơn", "text"),
            ("invoice_date", "Ngày hóa đơn", "date"),
            ("seller_name", "Đơn vị bán hàng", "text"),
            ("total_amount", "Tổng thanh toán", "integer"),
            ("currency", "Tiền tệ", "currency"),
        )
    ],
    "don_de_nghi": [
        FieldDefinition(field_id=key, label=label, value_type=kind)
        for key, label, kind in (
            ("full_name", "Họ và tên", "text"),
            ("student_id", "Mã sinh viên", "text"),
            ("date_of_birth", "Ngày sinh", "date"),
            ("class_name", "Lớp", "text"),
            ("faculty", "Khoa", "text"),
            ("request_content", "Nội dung đề nghị", "text"),
            ("request_date", "Ngày làm đơn", "date"),
        )
    ],
}


class ProductSchema(Contract):
    document_type: DocumentType
    schema_version: str = PRODUCT_SCHEMA_VERSION
    fields: list[FieldDefinition]


class ProductIssue(Contract):
    field_path: ProductFieldId
    code: str
    message: str
    severity: Literal["error", "warning"] = "error"


class ProductSpan(Contract):
    span_id: str
    page_index: Literal[0] = 0
    text: str
    box: tuple[float, float, float, float]
    ocr_score: float | None


class ProductPrediction(Contract):
    field_id: ProductFieldId
    raw_value: str | None
    normalized_value: Value
    observation: Literal["found", "not_found", "unknown"]
    evidence_span_ids: list[str]
    confidence: Confidence


class ProductRun(Contract):
    run_id: str
    status: Literal["queued", "running", "succeeded", "failed", "unavailable"]
    created_at: datetime
    finished_at: datetime | None = None
    error_code: str | None = None
    fields: list[ProductPrediction] = Field(default_factory=list)
    spans: list[ProductSpan] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class ProductReviewedField(Contract):
    is_reviewed: bool
    reviewed_value: Value

    @model_validator(mode="after")
    def unset_value(self):
        if not self.is_reviewed and self.reviewed_value is not None:
            raise ValueError("Unreviewed fields cannot contain a reviewed value")
        return self


class ProductRevision(Contract):
    revision: Annotated[int, Field(ge=1)]
    review_status: Literal["draft", "confirmed"]
    fields: dict[ProductFieldId, ProductReviewedField]
    effective_data: dict[ProductFieldId, Value]
    validation_issues: list[ProductIssue]
    saved_at: datetime


class ReviewRequest(Contract):
    run_id: str
    expected_revision: Annotated[int, Field(ge=1)]
    expected_status: Literal["draft", "confirmed"] | None = None
    fields: dict[ProductFieldId, ProductReviewedField]


class RevisionRequest(Contract):
    run_id: str
    expected_revision: Annotated[int, Field(ge=1)]


class ReprocessRequest(Contract):
    expected_run_id: str


class FinalInvoiceData(Contract):
    invoice_number: Annotated[str, Field(min_length=1)]
    invoice_date: str
    seller_name: Annotated[str, Field(min_length=1)]
    total_amount: Annotated[int, Field(ge=0, le=9_007_199_254_740_991)]
    currency: Literal["VND"]

    @field_validator("invoice_number", "seller_name")
    @classmethod
    def normalized_nonblank(cls, value: str):
        from document_pipeline.normalization import text_value

        if not value.strip() or text_value(value) != value:
            raise ValueError("Final strings must be nonblank normalized NFC text")
        return value

    @field_validator("invoice_date")
    @classmethod
    def valid_date(cls, value: str):
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError("ISO date required")
        date.fromisoformat(value)
        return value


class ProductExportArtifact(Contract):
    document_type: DocumentType
    schema_version: Literal["1.0.0"] = PRODUCT_SCHEMA_VERSION
    document_id: str
    run_id: str
    revision: Annotated[int, Field(ge=1)]
    data: FinalInvoiceData | FinalApplicationData
    review_status: Literal["confirmed"] = "confirmed"
    provenance: Provenance
    exported_at: datetime

    @model_validator(mode="after")
    def schema_matches(self):
        if (self.document_type == "hoa_don") != isinstance(self.data, FinalInvoiceData):
            raise ValueError("Document type does not match export data")
        return self


class DocumentSummary(Contract):
    document_id: str
    document_type: DocumentType
    filename: str
    data_origin: Literal["synthetic", "sample"]
    input_sha256: str
    image_width: int
    image_height: int
    created_at: datetime
    latest_run_id: str
    status: str
    review_status: str | None = None


class DocumentList(Contract):
    items: list[DocumentSummary]
    total: int
    limit: int
    offset: int


class DocumentDetail(DocumentSummary):
    image_url: str
    definitions: list[FieldDefinition]
    run: ProductRun
    review: ProductRevision | None
    is_latest_run: bool


class HistoryEvent(Contract):
    run_id: str
    revision: int | None
    action: str
    occurred_at: datetime
    changes: dict


class DocumentHistory(Contract):
    runs: list[ProductRun]
    events: list[HistoryEvent]


class ProductInsights(Contract):
    documents: int
    completed_runs: int
    failed_runs: int
    confirmed_documents: int
    reviewed_fields: int
    corrected_fields: int
    notice: str = "Thống kê vận hành và review; không phải độ chính xác của mô hình."


def effective_values(
    document_type: str,
    predictions: list[ProductPrediction],
    reviewed: dict[str, ProductReviewedField],
) -> dict:
    machine = {field.field_id: field.normalized_value for field in predictions}
    result = {}
    for definition in DEFINITIONS[document_type]:
        key = definition.field_id
        review = reviewed.get(key)
        # Explicit null is an intentional deletion; do not use `or machine_value`.
        value = review.reviewed_value if review and review.is_reviewed else machine.get(key)
        result[key] = normalize(key, value) if isinstance(value, str) and value.strip() else value
        if isinstance(result[key], str) and not result[key].strip():
            result[key] = None
    return result


def validate_values(document_type: str, data: dict) -> list[ProductIssue]:
    issues = []

    def add(key, code, message):
        issues.append(ProductIssue(field_path=key, code=code, message=message))

    for definition in DEFINITIONS[document_type]:
        key, value = definition.field_id, data.get(definition.field_id)
        if value is None or isinstance(value, str) and not value.strip():
            add(key, "MISSING_REQUIRED", "Trường bắt buộc còn trống; vẫn có thể lưu nháp.")
            continue
        if definition.value_type == "integer":
            if type(value) is not int or not 0 <= value <= 9_007_199_254_740_991:
                add(key, "INVALID_AMOUNT", "Cần số nguyên VND không âm trong miền JSON an toàn.")
            continue
        if not isinstance(value, str):
            add(key, "INVALID_TYPE", "Trường này phải là chuỗi ký tự.")
            continue
        if definition.value_type == "date":
            try:
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                    raise ValueError("format")
                date.fromisoformat(value)
            except ValueError:
                add(key, "INVALID_DATE", "Ngày phải tồn tại, định dạng YYYY-MM-DD.")
        if key == "currency" and value != "VND":
            add(key, "UNSUPPORTED_CURRENCY", "Phiên bản này hỗ trợ VND.")
        if key == "student_id" and not re.fullmatch(r"[0-9]+", value):
            add(key, "INVALID_IDENTIFIER", "Mã sinh viên là chuỗi chữ số, giữ số 0 đầu.")
    if (
        document_type == "don_de_nghi"
        and not any(issue.field_path in ("date_of_birth", "request_date") for issue in issues)
        and data["date_of_birth"] > data["request_date"]
    ):
        add("request_date", "DATE_ORDER", "Ngày làm đơn không được trước ngày sinh.")
    return issues
