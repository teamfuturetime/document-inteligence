import unicodedata
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

FieldId = Literal[
    "full_name",
    "student_id",
    "date_of_birth",
    "class_name",
    "faculty",
    "request_content",
    "request_date",
]
FIELD_IDS: tuple[FieldId, ...] = (
    "full_name",
    "student_id",
    "date_of_birth",
    "class_name",
    "faculty",
    "request_content",
    "request_date",
)
SCHEMA_VERSION = "1.0.0"
Score = Annotated[float, Field(ge=0, le=1)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Provenance(Contract):
    data_origin: Literal["synthetic", "sample"]
    prediction_source: Literal["fixture", "model", "unavailable"]


class Document(Contract):
    document_id: str
    document_type: Literal["don_de_nghi"] = "don_de_nghi"
    input_sha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    page_count: Annotated[int, Field(ge=1)] = 1
    provenance: Provenance


class Point(Contract):
    x: Annotated[float, Field(ge=0)]
    y: Annotated[float, Field(ge=0)]


class OCRSpan(Contract):
    span_id: str
    page_index: Annotated[int, Field(ge=0)]
    text: str
    polygon: Annotated[list[Point], Field(min_length=4, max_length=4)] | None = None
    image_width: Annotated[int, Field(gt=0)]
    image_height: Annotated[int, Field(gt=0)]
    coordinate_system: Literal["original_pixels_top_left"] = "original_pixels_top_left"
    transform: Literal["identity"] = "identity"
    ocr_score: Score | None = None

    @model_validator(mode="after")
    def bounds(self):
        if self.polygon and any(
            p.x > self.image_width or p.y > self.image_height for p in self.polygon
        ):
            raise ValueError("Tọa độ ngoài kích thước ảnh nguồn")
        return self


class Confidence(Contract):
    method: Literal["unknown", "simulated", "heuristic", "calibrated"] = "unknown"
    policy_version: str = "confidence-draft-1"
    score: Score | None = None
    ocr_score: Score | None = None
    mapping_signals: dict[str, str | int | float | bool] = Field(default_factory=dict)
    reason_codes: list[str] = Field(default_factory=lambda: ["NOT_MEASURED"])

    @model_validator(mode="after")
    def unknown_score(self):
        if self.method == "unknown" and (self.score is not None or self.ocr_score is not None):
            raise ValueError("Confidence unknown không có điểm")
        return self


class FieldPrediction(Contract):
    field_id: FieldId
    raw_value: str | None
    normalized_value: str | None
    observation: Literal["found", "not_found", "unreadable", "unknown"]
    evidence_status: Literal["available", "unavailable", "unknown"]
    evidence_span_ids: list[str] = Field(default_factory=list)
    confidence: Confidence = Field(default_factory=Confidence)

    @model_validator(mode="after")
    def observation_value(self):
        if self.observation == "found" and self.raw_value is None:
            raise ValueError("found cần raw_value")
        if self.observation != "found" and (
            self.raw_value is not None or self.normalized_value is not None
        ):
            raise ValueError("Trạng thái từ chối cần giá trị null")
        if self.evidence_status != "available" and self.evidence_span_ids:
            raise ValueError("Không được tạo evidence khi không có nguồn")
        return self


class OCRResult(Contract):
    status: Literal["succeeded", "unavailable", "failed"]
    prediction_source: Literal["fixture", "model", "unavailable"]
    spans: list[OCRSpan]
    engine_package: str | None
    model_artifact: str | None
    error_code: str | None = None


class ExtractionRun(Contract):
    run_id: str
    document_id: str
    schema_version: str
    provenance: Provenance
    fields: list[FieldPrediction]
    spans: list[OCRSpan]
    status: Literal["succeeded", "failed", "unavailable"]

    @model_validator(mode="after")
    def evidence_references(self):
        span_ids = {span.span_id for span in self.spans}
        field_ids = [field.field_id for field in self.fields]
        if len(field_ids) != len(set(field_ids)):
            raise ValueError("Trường dự đoán trùng ID")
        if len(span_ids) != len(self.spans):
            raise ValueError("OCR spans trùng ID")
        if any(set(field.evidence_span_ids) - span_ids for field in self.fields):
            raise ValueError("Evidence tham chiếu span không có trong run")
        return self


class DraftApplicationData(Contract):
    full_name: str | None = None
    student_id: str | None = None
    date_of_birth: str | None = None
    class_name: str | None = None
    faculty: str | None = None
    request_content: str | None = None
    request_date: str | None = None


class ValidationIssue(Contract):
    code: str
    field_path: FieldId
    severity: Literal["error", "warning"]
    message: str


class FinalApplicationData(Contract):
    full_name: Annotated[str, Field(min_length=1)]
    student_id: Annotated[str, Field(pattern=r"^[0-9]+$")]
    date_of_birth: Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}$")]
    class_name: Annotated[str, Field(min_length=1)]
    faculty: Annotated[str, Field(min_length=1)]
    request_content: Annotated[str, Field(min_length=1)]
    request_date: Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}$")]

    @field_validator("*")
    @classmethod
    def normalized_text(cls, value: str) -> str:
        if value != " ".join(unicodedata.normalize("NFC", value).split()):
            raise ValueError("Bản cuối cần dữ liệu đã chuẩn hóa NFC và khoảng trắng")
        return value

    @field_validator("date_of_birth", "request_date")
    @classmethod
    def calendar_date(cls, value: str) -> str:
        date.fromisoformat(value)
        return value

    @field_validator("full_name", "class_name", "faculty", "request_content")
    @classmethod
    def non_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Không được chỉ có khoảng trắng")
        return value

    @model_validator(mode="after")
    def date_order(self):
        if self.date_of_birth > self.request_date:
            raise ValueError("Ngày sinh không sau ngày làm đơn")
        return self


class ReviewedField(Contract):
    is_reviewed: bool
    reviewed_value: str | None

    @model_validator(mode="after")
    def unreviewed(self):
        if not self.is_reviewed and self.reviewed_value is not None:
            raise ValueError("Chưa review không có reviewed_value")
        return self


class ReviewRevision(Contract):
    document_id: str
    run_id: str
    revision: Annotated[int, Field(ge=1)]
    review_status: Literal["draft", "confirmed"]
    fields: dict[FieldId, ReviewedField]
    validation_issues: list[ValidationIssue]
    saved_at: datetime


class ReviewEvent(Contract):
    document_id: str
    run_id: str
    revision: Annotated[int, Field(ge=1)]
    field_id: FieldId | None
    action: Literal["edit", "clear", "confirm"]
    old_value: str | None
    new_value: str | None
    occurred_at: datetime
    reviewer_id: str | None = None


class ExportArtifact(Contract):
    document_type: Literal["don_de_nghi"] = "don_de_nghi"
    schema_version: Literal["1.0.0"] = SCHEMA_VERSION
    document_id: str
    run_id: str
    revision: Annotated[int, Field(ge=1)]
    data: FinalApplicationData
    review_status: Literal["confirmed"]
    provenance: Provenance


class GoldField(Contract):
    status: Literal["present", "absent", "unreadable"]
    value: str | None

    @model_validator(mode="after")
    def visible_value(self):
        if (self.status == "present") != (self.value is not None):
            raise ValueError("Chỉ gold present có giá trị đọc được")
        return self


class GoldAnnotation(Contract):
    sample_id: str
    fields: dict[FieldId, GoldField]


class FixtureSample(Contract):
    sample_id: Annotated[str, Field(pattern=r"^[a-z0-9_]+$")]
    parent_document_id: str
    template_id: str
    document_type: Literal["don_de_nghi"]
    input_path: str
    input_sha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    annotation_path: str
    annotation_sha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    split: Literal["contract_fixture", "development", "validation", "test"]
    quality_tags: list[str]
    provenance: dict[str, str]
    dataset_version: str


class FixtureManifest(Contract):
    purpose: Literal["contract_fixture"]
    dataset_version: str
    samples: list[FixtureSample]


class FixtureView(Contract):
    sample_id: str
    label: str
    image_url: str
    run: ExtractionRun
    draft: DraftApplicationData
    validation_issues: list[ValidationIssue]
