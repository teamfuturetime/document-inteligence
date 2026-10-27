"""Hậu xử lý văn bản tiếng Việt sau OCR: chuẩn hóa dấu, khoảng trắng, lỗi thường gặp."""
from __future__ import annotations

import re
import unicodedata

# Chỉ giữ các thay thế ký tự mojibake có bằng chứng rõ ràng. Không thay chữ/số
# theo ngữ cảnh vì có thể làm hỏng MST, số tiền, ngày tháng hoặc mã giấy tờ.
_COMMON_FIXES = {
    "cå": "cá",
    "då": "dá",
    "lå": "lá",
    "nå": "ná",
    "tå": "tá",
    "uå": "uá",
    "vå": "vá",
    "xå": "xá",
    "å": "á",
    "ä": "ă",
    "ë": "ê",
    "ï": "í",
    "ö": "ô",
    "ü": "ư",
    "ÿ": "ý",
    "ç": "c",
    "ñ": "n",
    "ø": "o",
    "æ": "a",
    "ð": "d",
    "þ": "t",
    "ß": "s",
}

# Dấu câu tiếng Việt hợp lệ
_VIETNAMESE_PUNCTUATION = set(".,;:!?()[]{}'\"-–—/\\%&@#$*+=")


def normalize_unicode(text: str) -> str:
    """Chuẩn hóa Unicode về dạng tổ hợp (NFC) để đồng nhất dấu tiếng Việt."""
    return unicodedata.normalize("NFC", text)


def fix_common_ocr_errors(text: str) -> str:
    """Sửa các lỗi OCR phổ biến trên tiếng Việt."""
    result = text
    for wrong, right in _COMMON_FIXES.items():
        result = result.replace(wrong, right)
    return result


def clean_whitespace(text: str) -> str:
    """Dọn khoảng trắng: gộp nhiều space, bỏ space thừa trước dấu câu."""
    result = re.sub(r"[ \t]+", " ", text)
    result = re.sub(r" *([.,;:!?])", r"\1", result)
    result = re.sub(r" *\n *", "\n", result)
    return result.strip()


def fix_vietnamese_diacritics(text: str) -> str:
    """Preserve recognized diacritics; NFC is the only safe automatic change."""

    return normalize_unicode(text)


def is_valid_word(word: str) -> bool:
    """Kiểm tra từ có hợp lệ (chứa ký tự chữ cái hoặc số)."""
    if not word:
        return False
    return any(ch.isalnum() for ch in word)


def postprocess_text(text: str, *, fix_errors: bool = False) -> str:
    """Safely normalize OCR text without guessing words or numeric tokens."""
    result = normalize_unicode(text)
    if fix_errors:
        result = fix_common_ocr_errors(result)
    result = fix_vietnamese_diacritics(result)
    result = clean_whitespace(result)
    return result


def postprocess_result(result) -> str:
    """Hậu xử lý trực tiếp một OCRResult, trả về text đã làm sạch."""
    return postprocess_text(result.text)
