"""Hậu xử lý văn bản tiếng Việt sau OCR: chuẩn hóa dấu, khoảng trắng, lỗi thường gặp."""
from __future__ import annotations

import re
import unicodedata

# Bảng thay thế lỗi OCR phổ biến trên tiếng Việt
_COMMON_FIXES = {
    "|": "l",
    "0": "o",  # chỉ áp dụng trong từ, không áp dụng số
    "1": "l",
    "5": "s",
    "8": "B",
    "rn": "m",
    "cl": "d",
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
    """Sửa dấu tiếng Việt bị đặt sai vị trí (vd: 'hoà' → 'hòa')."""
    # Quy tắc đơn giản: nguyên âm đôi 'oa' khi có dấu huyền/sắc/hỏi/ngã
    # thường đặt trên 'o' (hòa, hóa) thay vì 'a' (hoà, hoá)
    replacements = {
        "òa": "oà",
        "óa": "oá",
        "ỏa": "oả",
        "õa": "oã",
        "ọa": "oạ",
        "òe": "oè",
        "óe": "oé",
        "ỏe": "oẻ",
        "õe": "oẽ",
        "ọe": "oẹ",
        "ùy": "uỳ",
        "úy": "uý",
        "ủy": "uỷ",
        "ũy": "uỹ",
        "ụy": "uỵ",
    }
    for wrong, right in replacements.items():
        text = text.replace(wrong, right)
    return text


def is_valid_word(word: str) -> bool:
    """Kiểm tra từ có hợp lệ (chứa ký tự chữ cái hoặc số)."""
    if not word:
        return False
    return any(ch.isalnum() for ch in word)


def postprocess_text(text: str, *, fix_errors: bool = True) -> str:
    """Pipeline hậu xử lý văn bản tiếng Việt hoàn chỉnh."""
    result = normalize_unicode(text)
    if fix_errors:
        result = fix_common_ocr_errors(result)
    result = fix_vietnamese_diacritics(result)
    result = clean_whitespace(result)
    return result


def postprocess_result(result) -> str:
    """Hậu xử lý trực tiếp một OCRResult, trả về text đã làm sạch."""
    return postprocess_text(result.text)
