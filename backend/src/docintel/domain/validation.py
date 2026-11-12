import re
from datetime import date

from docintel.domain.models import DraftApplicationData, FieldId, ValidationIssue

VALIDATION_VERSION = "application-rules-1.0.0"


def validate_draft(draft: DraftApplicationData) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    def add(code: str, field: FieldId, message: str):
        issues.append(
            ValidationIssue(code=code, field_path=field, severity="error", message=message)
        )

    for field, value in draft.model_dump().items():
        if value is None or not value.strip():
            add("MISSING_REQUIRED", field, "Trường bắt buộc còn trống; bản nháp vẫn được phép lưu.")
    if draft.student_id and not re.fullmatch(r"[0-9]+", draft.student_id):
        add("STUDENT_ID_FORMAT", "student_id", "Mã sinh viên phải là chuỗi chữ số, giữ số 0 đầu.")
    parsed: dict[str, date] = {}
    for field in ("date_of_birth", "request_date"):
        value = getattr(draft, field)
        if value and value.strip():
            try:
                if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
                    raise ValueError("format")
                parsed[field] = date.fromisoformat(value)
            except ValueError:
                add("INVALID_DATE", field, "Ngày phải tồn tại và có định dạng YYYY-MM-DD.")
    if len(parsed) == 2 and parsed["date_of_birth"] > parsed["request_date"]:
        add("DATE_ORDER", "request_date", "Ngày làm đơn không được trước ngày sinh.")
    return issues
