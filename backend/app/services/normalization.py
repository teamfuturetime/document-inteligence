"""Convert only documented raw formats; retain a detached copy of the source.

Candidates still require business validation. No confidence, evidence spans or
extraction status is manufactured by this service.
"""

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
import re
import unicodedata

from app.schemas.validation import FieldIssue, FieldName

NORMALIZATION_VERSION = "invoice-normalization-1"
FIELD_NAMES: tuple[FieldName, ...] = (
    "invoice_number", "invoice_date", "seller_name", "total_amount", "currency"
)
_VND_ALIASES = {"vnd", "vnđ", "đồng", "đ", "₫"}
_VND_SUFFIX = re.compile(r"(?<=[0-9\s])(?:VND|VNĐ|đồng|đ|₫)$", re.IGNORECASE)
_CURRENCY_MARKS = re.compile(r"(?<!\w)(?:vnđ|đồng|đ|₫|[a-z]{3})(?!\w)")


@dataclass(frozen=True)
class NormalizationResult:
    raw_values: object
    candidates: dict[str, object]
    errors: list[FieldIssue]
    source_locale: str | None
    normalization_version: str = NORMALIZATION_VERSION


def _issue(field: FieldName | None, code: str, message: str) -> FieldIssue:
    return FieldIssue(field=field, code=code, message=message)


def normalize_invoice(
    raw_values: object, *, source_locale: str | None = None
) -> NormalizationResult:
    """Normalize a five-key raw record; DMY requires explicit vi-VN context.

    Unknown/missing keys are contract errors. Explicit null/blank fields remain
    missing for business validation, except currency evidenced by a VND suffix.
    """
    source = deepcopy(raw_values)
    candidates: dict[str, object] = dict.fromkeys(FIELD_NAMES)
    errors: list[FieldIssue] = []
    if source_locale not in (None, "vi-VN"):
        errors.append(_issue(None, "schema.unsupported_locale", "Source locale is not supported"))
    if not isinstance(source, Mapping):
        errors.append(_issue(None, "schema.invalid_input", "Input must be a five-key object"))
        return NormalizationResult(source, candidates, errors, source_locale)
    for key in source:
        if key not in FIELD_NAMES:
            errors.append(_issue(None, "schema.extra_forbidden", "Input contains an unknown key"))

    suffix_currency = False
    for field in FIELD_NAMES:
        if field not in source:
            errors.append(_issue(field, "schema.missing_key", "Required input key is missing"))
            continue
        raw = source[field]
        if raw is None:
            continue
        if field == "total_amount" and type(raw) is int:
            candidates[field] = raw
            continue
        if not isinstance(raw, str):
            errors.append(_issue(field, "schema.invalid_type", "Expected text or null, or an integer amount"))
            continue
        text = unicodedata.normalize("NFC", raw).strip()
        if field == "seller_name":
            text = " ".join(text.split())
        if not text:
            continue
        if any(unicodedata.category(char) in {"Cc", "Cf", "Cs"} for char in text):
            errors.append(_issue(field, "normalization.invalid_character", "Input contains unsupported control characters"))
            continue

        if field == "invoice_date":
            if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", text):
                candidates[field] = text
            elif match := re.fullmatch(r"([0-9]{2})/([0-9]{2})/([0-9]{4})", text):
                if source_locale != "vi-VN":
                    errors.append(_issue(field, "normalization.ambiguous_date", "DMY dates require an explicit vi-VN source"))
                else:
                    day, month, year = match.groups()
                    candidates[field] = f"{year}-{month}-{day}"
            else:
                errors.append(_issue(field, "normalization.invalid_date_format", "Date must use ISO or documented DMY format"))
        elif field == "total_amount":
            suffix = _VND_SUFFIX.search(text)
            if suffix:
                suffix_currency = True
                text = text[:suffix.start()].strip()
            if re.fullmatch(r"[0-9]+", text) or re.fullmatch(r"[1-9][0-9]{0,2}(?:\.[0-9]{3})+", text):
                digits = text.replace(".", "").lstrip("0") or "0"
                # Avoid Python's huge-int parsing limit; anything over 16 digits
                # is necessarily beyond the documented safe integer maximum.
                if len(digits) > 16:
                    errors.append(_issue(field, "normalization.amount_out_of_range", "Amount exceeds the supported integer range"))
                else:
                    candidates[field] = int(digits)
            elif re.fullmatch(r"[0-9]+,[0-9]+", text):
                errors.append(_issue(field, "normalization.ambiguous_amount", "Comma-separated amount is ambiguous"))
            else:
                errors.append(_issue(field, "normalization.invalid_amount_format", "Amount format is not supported"))
        elif field == "currency":
            folded = text.casefold()
            marks = {"VND" if token in _VND_ALIASES else token.upper()
                     for token in _CURRENCY_MARKS.findall(folded)}
            if folded == "d" or len(marks) > 1:
                errors.append(_issue(field, "normalization.ambiguous_currency", "Currency evidence is ambiguous or conflicting"))
            else:
                candidates[field] = "VND" if folded in _VND_ALIASES else text
        else:
            candidates[field] = text

    if suffix_currency and "currency" in source and not any(error.field == "currency" for error in errors):
        if candidates["currency"] is None:
            candidates["currency"] = "VND"
        elif candidates["currency"] != "VND":
            candidates["currency"] = None
            errors.append(_issue("currency", "normalization.ambiguous_currency", "Currency field conflicts with the amount suffix"))
    return NormalizationResult(source, candidates, errors, source_locale)
