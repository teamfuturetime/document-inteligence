import re
import unicodedata


def normalize_vietnamese_text(text: str) -> str:
    """Normalize Unicode and OCR whitespace without changing semantic content."""
    normalized = unicodedata.normalize("NFC", text)
    normalized = normalized.replace("\u00a0", " ").replace("\u200b", "")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in normalized.splitlines()]
    return "\n".join(line for line in lines if line)


def normalize_identifier(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z]", "", normalize_vietnamese_text(value))


def fold_vietnamese_for_matching(text: str) -> str:
    """Remove Vietnamese tone marks for OCR-tolerant keyword matching."""
    decomposed = unicodedata.normalize("NFD", normalize_vietnamese_text(text).casefold())
    without_marks = "".join(char for char in decomposed if not unicodedata.combining(char))
    return without_marks.replace("đ", "d")
