from docintel.domain.models import ReviewedField


def effective_value(machine_value: str | None, reviewed: ReviewedField) -> str | None:
    """Quy tắc contract; chưa phải dịch vụ lưu/xác nhận revision."""
    return reviewed.reviewed_value if reviewed.is_reviewed else machine_value
