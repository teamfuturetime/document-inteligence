import re
from datetime import datetime

from ai_service.extraction.schemas import DOCUMENT_FIELDS, ExtractionResult, ExtractedField
from ai_service.ocr.normalization import normalize_vietnamese_text


PATTERNS = {
    "id_number": r"(?:số|no)[.:\s]*([0-9]{9,12})",
    "full_name": r"(?:họ và tên|họ tên)[.:\s]*([^\n]+)",
    "applicant_name": r"(?:người làm đơn|tôi tên)[.:\s]*([^\n]+)",
    "date_of_birth": r"(?:ngày sinh|sinh ngày)[.:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{4})",
    "place_of_birth": r"nơi sinh[.:\s]*([^\n]+)",
    "address": r"(?:nơi thường trú|địa chỉ)[.:\s]*([^\n]+)",
    "father_name": r"họ và tên cha[.:\s]*([^\n]+)",
    "mother_name": r"họ và tên mẹ[.:\s]*([^\n]+)",
    "recipient": r"kính gửi[.:\s]*([^\n]+)",
    "subject": r"(?:về việc|nội dung)[.:\s]*([^\n]+)",
    "customer": r"(?:hóa đơn được gửi cho|khách hàng)[.:\t ]+([^\n:][^\n]*)",
    "payment_recipient": r"thanh toán cho[.:\t ]+([^\n:][^\n]*)",
    "total_amount": r"(?:tổng cộng|thành tiền)[.:\s]*([0-9][0-9.,\s]*(?:đ|vnd)?)",
    "date": r"ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})",
}


def _extract(pattern: str, text: str) -> tuple[str | None, str | None]:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None, None
    groups = match.groups()
    if len(groups) == 3 and "tháng" in match.group(0).casefold():
        try:
            value = datetime(int(groups[2]), int(groups[1]), int(groups[0])).date().isoformat()
        except ValueError:
            return None, None
    else:
        value = groups[0].strip(" .:-")
    return value, match.group(0)


def extract_fields(text: str, document_type: str) -> ExtractionResult:
    normalized = normalize_vietnamese_text(text)
    fields: dict[str, ExtractedField] = {}
    for name in DOCUMENT_FIELDS.get(document_type, set()):
        value, source = _extract(PATTERNS[name], normalized)
        fields[name] = ExtractedField(value=value, confidence=0.8 if value else 0.0, source_text=source)
    missing = [name for name, field in fields.items() if field.value is None]
    warnings = [f"Không tìm thấy trường: {name}" for name in sorted(missing)]
    return ExtractionResult(document_type=document_type, fields=fields, warnings=warnings)
