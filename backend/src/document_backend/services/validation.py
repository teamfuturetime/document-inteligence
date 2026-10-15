"""Validate user edits without altering OCR provenance or inventing values."""

from datetime import date
import re
import unicodedata

from document_contracts.models import ValidationRequest, ValidationResponse
from document_pipeline.extraction import SourceValueError, normalize_value

MESSAGES = {
    "required": "Cần nhập giá trị.",
    "invalid_format": "Giá trị không đúng định dạng.",
    "invalid_date": "Ngày không tồn tại trong lịch.",
    "out_of_range": "Giá trị vượt phạm vi cho phép.",
    "unsupported_currency": "MVP chỉ hỗ trợ VND.",
}


def validate_review(request: ValidationRequest) -> ValidationResponse:
    values = {}
    errors = []
    for field, raw in request.values:
        value = unicodedata.normalize("NFC", " ".join((raw or "").split()))
        code = None
        normalized = None
        if not value:
            code = "required"
        elif field == "invoice_date":
            if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
                code = "invalid_format"
            else:
                try:
                    normalized = date.fromisoformat(value).isoformat()
                except ValueError:
                    code = "invalid_date"
        else:
            try:
                normalized = normalize_value(field, value)
            except SourceValueError:
                if field == "currency":
                    code = "unsupported_currency"
                elif (field == "invoice_number" and len(value) > 100
                      or field == "seller_name" and len(value) > 200
                      or field == "total_amount" and re.fullmatch(r"-?[0-9., ]+", value)
                      and (value.startswith("-") or len(re.sub(r"[., ]", "", value).lstrip("0")) > 16)):
                    code = "out_of_range"
                elif field == "total_amount" and value.isascii() and value.isdigit():
                    code = "out_of_range"
                else:
                    code = "invalid_format"
        values[field] = normalized
        if code:
            errors.append({"field": field, "code": code, "message": MESSAGES[code]})
    return ValidationResponse(schema_version="1.0.0", valid=not errors,
                              normalized_values=values, errors=errors)
