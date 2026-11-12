import re
import unicodedata
from datetime import date


def text_value(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value).split())


def fold_label(value: str) -> str:
    value = unicodedata.normalize("NFD", value.casefold().replace("đ", "d"))
    return "".join(char for char in value if not unicodedata.combining(char))


def normalize(field: str, value: str) -> str | int:
    value = text_value(value)
    if field in {"invoice_date", "date_of_birth", "request_date"}:
        match = re.fullmatch(r"(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})", value)
        if match:
            try:
                return date(int(match[3]), int(match[2]), int(match[1])).isoformat()
            except ValueError:
                return value
    if field == "currency" and value.upper() in {"VND", "VNĐ", "Đ", "ĐỒNG"}:
        return "VND"
    if field == "total_amount":
        number = re.sub(r"\s*(VND|VNĐ|đ|đồng)\s*$", "", value, flags=re.I).strip()
        if re.fullmatch(r"\d+", number) or re.fullmatch(r"\d{1,3}([., ])\d{3}(?:\1\d{3})*", number):
            amount = int(re.sub(r"[., ]", "", number))
            if amount <= 9_007_199_254_740_991:
                return amount
    return value


def folded_offsets(value: str) -> tuple[str, list[int]]:
    """Keep raw offsets when folding expands characters or removes accents."""
    folded, offsets = [], []
    for index, character in enumerate(value):
        part = fold_label(character)
        folded.append(part)
        offsets.extend([index] * len(part))
    return "".join(folded), offsets
