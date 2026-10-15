from dataclasses import dataclass

from ai_service.ocr.normalization import normalize_vietnamese_text


@dataclass(frozen=True)
class Classification:
    document_type: str
    confidence: float
    matched_keywords: tuple[str, ...]


KEYWORDS = {
    "identity_card": ("căn cước công dân", "số định danh cá nhân", "quê quán"),
    "birth_certificate": ("giấy khai sinh", "nơi sinh", "họ và tên cha"),
    "application_form": ("đơn đề nghị", "kính gửi", "người làm đơn"),
}


def classify_document(text: str) -> Classification:
    haystack = normalize_vietnamese_text(text).casefold()
    scores = {
        kind: tuple(keyword for keyword in keywords if keyword in haystack)
        for kind, keywords in KEYWORDS.items()
    }
    kind, matches = max(scores.items(), key=lambda item: len(item[1]))
    if not matches:
        return Classification("unknown", 0.0, ())
    confidence = min(0.5 + 0.2 * len(matches), 0.95)
    return Classification(kind, confidence, matches)
