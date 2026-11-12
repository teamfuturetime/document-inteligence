import re
import unicodedata
from datetime import date

from docintel.domain.models import DraftApplicationData, FieldId

NORMALIZATION_VERSION = "nfc-whitespace-date-1.0.0"
DATE_FIELDS = {"date_of_birth", "request_date"}


def normalize_value(field_id: FieldId, value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("Giá trị phải là string hoặc null; không chuyển mã số từ integer")
    result = " ".join(unicodedata.normalize("NFC", value).split())
    if not result:
        return None
    if field_id in DATE_FIELDS:
        # dd/mm/yyyy là quy ước schema Việt Nam này, không đoán mm/dd/yyyy.
        match = re.fullmatch(r"([0-9]{2})/([0-9]{2})/([0-9]{4})", result)
        if match:
            day, month, year = map(int, match.groups())
            try:
                return date(year, month, day).isoformat()
            except ValueError:
                return result  # Giữ giá trị sai để validation chỉ ra lỗi.
    return result


def normalize_draft(draft: DraftApplicationData) -> DraftApplicationData:
    return DraftApplicationData.model_validate(
        {key: normalize_value(key, value) for key, value in draft.model_dump().items()}
    )
