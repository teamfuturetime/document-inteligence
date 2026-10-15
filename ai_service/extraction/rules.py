"""Bộ quy tắc trích xuất cho các biểu mẫu tiếng Việt (CMND/CCCD, giấy tờ)."""
from __future__ import annotations

import re
from typing import List

from ai_service.extraction.engine import ExtractionEngine, FieldPattern

# ----------------------------------------------------------------------
# Pattern phổ biến cho giấy tờ tiếng Việt
# ----------------------------------------------------------------------

# Số CCCD/CMND: 9 hoặc 12 chữ số
CCCD_PATTERN = re.compile(r"(?:Số|So|SỐ|SO)[:\s]*([0-9]{9,12})", re.IGNORECASE)
CCCD_BARE_PATTERN = re.compile(r"\b([0-9]{12})\b")

# Ngày tháng: dd/mm/yyyy hoặc dd-mm-yyyy
DATE_PATTERN = re.compile(
    r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})"
)

# Họ và tên: sau nhãn "Họ và tên"
FULL_NAME_PATTERN = re.compile(
    r"(?:Họ và tên|Ho va ten|Họ tên|Ho ten)[:\s]*([A-ZÀ-Ỹ][\wÀ-ỹ\s]{2,50})",
    re.IGNORECASE,
)

# Ngày sinh: sau nhãn "Ngày sinh"
BIRTH_DATE_PATTERN = re.compile(
    r"(?:Ngày sinh|Ngay sinh|NS)[:\s]*(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{4})",
    re.IGNORECASE,
)

# Giới tính
GENDER_PATTERN = re.compile(
    r"(?:Giới tính|Gioi tinh|GT)[:\s]*(Nam|Nữ|Nu|Nam/Nữ)",
    re.IGNORECASE,
)

# Quê quán
HOMETOWN_PATTERN = re.compile(
    r"(?:Quê quán|Que quan|QQ)[:\s]*([A-ZÀ-Ỹ][\wÀ-ỹ\s,]{3,80})",
    re.IGNORECASE,
)

# Địa chỉ thường trú
ADDRESS_PATTERN = re.compile(
    r"(?:Địa chỉ|Dia chi|DC|Nơi thường trú|Noi thuong tru)[:\s]*"
    r"([A-ZÀ-Ỹ0-9][\wÀ-ỹ0-9\s,./-]{5,120})",
    re.IGNORECASE,
)

# Số điện thoại Việt Nam
PHONE_PATTERN = re.compile(
    r"(?:Điện thoại|Dien thoai|SDT|SĐT)[:\s]*(0\d{9,10})",
    re.IGNORECASE,
)

# Email
EMAIL_PATTERN = re.compile(
    r"(?:Email|email)[:\s]*([\w.+-]+@[\w-]+\.[\w.]+)"
)

# Mã số thuế
TAX_CODE_PATTERN = re.compile(
    r"(?:Mã số thuế|Ma so thue|MST)[:\s]*([0-9]{10,13})",
    re.IGNORECASE,
)


def build_vietnamese_form_engine() -> ExtractionEngine:
    """Tạo engine trích xuất với các pattern biểu mẫu tiếng Việt."""
    patterns: List[FieldPattern] = [
        FieldPattern("cccd", CCCD_PATTERN, confidence=95.0, required=True),
        FieldPattern("birth_date", BIRTH_DATE_PATTERN, confidence=90.0),
        FieldPattern("full_name", FULL_NAME_PATTERN, confidence=85.0, required=True),
        FieldPattern("gender", GENDER_PATTERN, confidence=80.0),
        FieldPattern("hometown", HOMETOWN_PATTERN, confidence=75.0),
        FieldPattern("address", ADDRESS_PATTERN, confidence=75.0),
        FieldPattern("phone", PHONE_PATTERN, confidence=90.0),
        FieldPattern("email", EMAIL_PATTERN, confidence=90.0),
        FieldPattern("tax_code", TAX_CODE_PATTERN, confidence=90.0),
    ]
    return ExtractionEngine(patterns)


def extract_dates(text: str) -> List[str]:
    """Trích xuất tất cả ngày tháng trong văn bản."""
    return [m.group(0) for m in DATE_PATTERN.finditer(text)]
