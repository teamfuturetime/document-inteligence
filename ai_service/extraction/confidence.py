"""Đánh giá độ tin cậy của kết quả trích xuất trường dữ liệu."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from ai_service.extraction.engine import ExtractedField, ExtractionResult

# Ngưỡng chất lượng
HIGH_CONFIDENCE = 85.0
LOW_CONFIDENCE = 60.0


@dataclass
class FieldQualityReport:
    """Báo cáo chất lượng một trường."""

    name: str
    confidence: float
    validity: str  # "valid" | "suspicious" | "invalid"
    reason: Optional[str] = None

    @property
    def is_ok(self) -> bool:
        return self.validity == "valid"


def _check_cccd(value: str) -> Optional[str]:
    """Kiểm tra số CCCD/CMND."""
    digits = re.sub(r"\D", "", value)
    if len(digits) not in (9, 12):
        return f"Số CCCD phải có 9 hoặc 12 chữ số (hiện tại: {len(digits)})"
    # Năm sinh suy từ CCCD 12 số: 2 ký tự đầu là mã tỉnh, 3 ký tự sau là mã giới tính + thế kỷ
    return None


def _check_birth_date(value: str) -> Optional[str]:
    """Kiểm tra ngày sinh hợp lệ (01/01/1900 - 31/12/now)."""
    match = re.match(r"^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})$", value.strip())
    if not match:
        return "Định dạng ngày không hợp lệ (dd/mm/yyyy)"
    day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
    if not (1900 <= year <= 2100):
        return f"Năm sinh ngoài khoảng hợp lệ: {year}"
    if not (1 <= month <= 12):
        return f"Tháng sinh không hợp lệ: {month}"
    if not (1 <= day <= 31):
        return f"Ngày sinh không hợp lệ: {day}"
    return None


def _check_phone(value: str) -> Optional[str]:
    """Kiểm tra số điện thoại Việt Nam."""
    digits = re.sub(r"\D", "", value)
    if not digits.startswith("0") or len(digits) not in (10, 11):
        return "SĐT VN phải bắt đầu bằng 0 và có 10-11 số"
    return None


def _check_email(value: str) -> Optional[str]:
    """Kiểm tra email cơ bản."""
    if not re.match(r"^[\w.+-]+@[\w-]+\.[\w.]+$", value.strip()):
        return "Email không hợp lệ"
    return None


def _check_gender(value: str) -> Optional[str]:
    """Kiểm tra giới tính."""
    if value.strip().lower() not in ("nam", "nữ", "nu"):
        return "Giới tính chỉ nhận Nam/Nữ"
    return None


# Danh sách validator theo tên trường
_VALIDATORS = {
    "cccd": _check_cccd,
    "birth_date": _check_birth_date,
    "phone": _check_phone,
    "email": _check_email,
    "gender": _check_gender,
}


def validate_field(field: ExtractedField) -> FieldQualityReport:
    """Kiểm tra giá trị một trường đã trích xuất."""
    validator = _VALIDATORS.get(field.name)
    if validator is None:
        return FieldQualityReport(
            name=field.name, confidence=field.confidence, validity="valid"
        )
    reason = validator(field.value)
    if reason:
        return FieldQualityReport(
            name=field.name,
            confidence=min(field.confidence, 40.0),
            validity="invalid",
            reason=reason,
        )
    return FieldQualityReport(
        name=field.name, confidence=field.confidence, validity="valid"
    )


def assess_extraction(result: ExtractionResult) -> dict:
    """Đánh giá toàn bộ kết quả trích xuất."""
    reports = [validate_field(f) for f in result.fields]
    valid = [r for r in reports if r.is_ok]
    invalid = [r for r in reports if not r.is_ok]

    if not result.fields:
        return {
            "overall_confidence": 0.0,
            "confidence_type": "not_estimated",
            "quality": "low",
            "valid_count": 0,
            "invalid_count": 0,
            "reports": [],
        }

    mean_conf = sum(r.confidence for r in reports) / len(reports)
    if mean_conf >= HIGH_CONFIDENCE and not invalid:
        quality = "high"
    elif mean_conf >= LOW_CONFIDENCE:
        quality = "medium"
    else:
        quality = "low"

    return {
        "overall_confidence": round(mean_conf, 2),
        "confidence_type": "not_estimated" if all(f.confidence_type == "not_estimated" for f in result.fields) else "heuristic",
        "quality": quality,
        "valid_count": len(valid),
        "invalid_count": len(invalid),
        "reports": [{"name": r.name, "validity": r.validity, "reason": r.reason,
                     "confidence_type": f.confidence_type, "matched_label": f.matched_pattern}
                    for r, f in zip(reports, result.fields)],
    }
