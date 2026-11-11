"""Single source of schema, normalization and review validation."""

from datetime import date
from functools import lru_cache
import re
import unicodedata
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator

SCHEMA_VERSION = "solo-1.0"
SAFE_INT = 9_007_199_254_740_991
Kind = Literal["invoice", "application"]
Mode = Literal["rules", "vlm", "hybrid"]
Value = str | int | None


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class Invoice(Strict):
    invoice_number: Annotated[str, Field(min_length=1, max_length=100)]
    invoice_date: str
    seller_name: Annotated[str, Field(min_length=1, max_length=200)]
    total_amount: Annotated[int, Field(ge=0, le=SAFE_INT)]
    currency: Literal["VND"]

    @field_validator("invoice_date")
    @classmethod
    def valid_date(cls, value):
        return date.fromisoformat(value).isoformat()


class Application(Strict):
    applicant_name: Annotated[str, Field(min_length=1, max_length=200)]
    student_id: Annotated[str, Field(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9-]+$")]
    recipient: Annotated[str, Field(min_length=1, max_length=200)]
    request: Annotated[str, Field(min_length=1, max_length=1000)]
    submission_date: str

    @field_validator("submission_date")
    @classmethod
    def valid_date(cls, value):
        return date.fromisoformat(value).isoformat()


# Insertion order is display order. These aliases are versioned extraction config.
LABELS = {
    "invoice": {
        "invoice_number": ["Số hóa đơn", "Mã hóa đơn", "Số HĐ"],
        "invoice_date": ["Ngày hóa đơn", "Ngày lập", "Ngày"],
        "seller_name": ["Tên đơn vị bán", "Đơn vị bán hàng", "Người bán", "Bên bán"],
        "total_amount": ["Tổng tiền thanh toán", "Tổng thanh toán", "Tổng cộng", "Tổng tiền"],
        "currency": ["Đơn vị tiền tệ", "Tiền tệ"],
    },
    "application": {
        "applicant_name": ["Họ và tên", "Họ tên", "Người đề nghị"],
        "student_id": ["Mã số sinh viên", "Mã sinh viên", "MSSV"],
        "recipient": ["Kính gửi", "Nơi nhận"],
        "request": ["Nội dung đề nghị", "Đề nghị", "Nội dung"],
        "submission_date": ["Ngày làm đơn", "Ngày lập đơn", "Ngày"],
    },
}
MODELS = {"invoice": Invoice, "application": Application}
TITLES = {"invoice": "Hóa đơn bán hàng", "application": "Đơn đề nghị sinh viên"}


def clean(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).split())


def folded(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", clean(text).lower().replace("đ", "d"))
                   if unicodedata.category(c) != "Mn")


def normalize(key: str, value: Value) -> str | int:
    if value is None or isinstance(value, bool):
        raise ValueError("Cần bổ sung giá trị.")
    text = clean(str(value))
    if not text:
        raise ValueError("Cần bổ sung giá trị.")
    if key.endswith("_date"):
        if re.fullmatch(r"\d{2}/\d{2}/\d{4}", text):
            day, month, year = map(int, text.split("/"))
            return date(year, month, day).isoformat()
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
            raise ValueError("Dùng YYYY-MM-DD hoặc DD/MM/YYYY.")
        return date.fromisoformat(text).isoformat()
    if key == "total_amount":
        text = re.sub(r"\s*(VND|VNĐ|đ)\s*$", "", text, flags=re.I).strip()
        if not re.fullmatch(r"\d+|\d{1,3}(?:\.\d{3})+|\d{1,3}(?:,\d{3})+", text):
            raise ValueError("Nhập số nguyên VND, không có phần thập phân.")
        amount = int(text.replace(".", "").replace(",", ""))
        if not 0 <= amount <= SAFE_INT:
            raise ValueError("Số tiền ngoài phạm vi hỗ trợ.")
        return amount
    if key == "currency":
        if text.upper() not in {"VND", "VNĐ", "Đ"}:
            raise ValueError("Schema hóa đơn này chỉ hỗ trợ VND.")
        return "VND"
    return text


@lru_cache(maxsize=10)
def adapter(kind, key):
    annotation = MODELS[kind].model_fields[key].rebuild_annotation()
    return TypeAdapter(annotation, config=ConfigDict(strict=True))


def validated_value(kind, key, value):
    return adapter(kind, key).validate_python(normalize(key, value))


def validate_values(kind: Kind, values: dict[str, Value]) -> dict:
    expected = LABELS[kind]
    if set(values) != set(expected):
        raise ValueError("Các trường phải khớp chính xác schema đã chọn.")
    normalized, errors = {}, {}
    for key, value in values.items():
        try:
            normalized[key] = validated_value(kind, key, value)
        except ValueError:
            normalized[key] = None
            errors[key] = "Cần giá trị hợp lệ: ngày đúng lịch, tiền nguyên VND, chuỗi đúng giới hạn."
    if not errors:
        normalized = MODELS[kind].model_validate(normalized).model_dump()
    return {"valid": not errors, "values": normalized, "errors": errors}


class Token(Strict):
    text: str
    confidence: Annotated[float, Field(ge=0, le=1)] | None
    box: tuple[int, int, int, int]
    line: tuple[int, int, int]


class Extracted(Strict):
    value: Value
    confidence: Annotated[float, Field(ge=0, le=1)] | None
    confidence_source: Literal["ocr_min", "ocr_agreement", "unavailable"]
    source: Literal["rules", "vlm", "agreement", "conflict", "missing"]
    evidence: list[str]
    warnings: list[str]


class Extraction(Strict):
    schema_version: Literal["solo-1.0"] = SCHEMA_VERSION
    document_type: Kind
    document_sha256: str
    mode: Mode
    fields: dict[str, Extracted]
    ocr_text: str
    provenance: dict
    warnings: list[str]


class Review(Strict):
    document_type: Kind
    values: dict[str, Value]


class ExportRequest(Strict):
    original: Extraction
    values: dict[str, Value]


def reviewed_export(request: ExportRequest) -> dict:
    kind = request.original.document_type
    if set(request.original.fields) != set(LABELS[kind]):
        raise ValueError("Extraction không khớp schema.")
    result = validate_values(kind, request.values)
    if not result["valid"]:
        raise ValueError("Cần sửa tất cả lỗi trước khi xuất JSON.")
    return {"schema_version": SCHEMA_VERSION, "document_type": kind,
            "original_extraction": request.original.model_dump(mode="json"),
            "values": result["values"],
            "edited_fields": [key for key, value in result["values"].items()
                              if value != request.original.fields[key].value]}
