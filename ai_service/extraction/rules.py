"""Document-specific, line-bounded extraction from Vietnamese OCR evidence."""

from __future__ import annotations

from datetime import date
import re
import unicodedata

from ai_service.classification.engine import (
    build_vietnamese_classifier,
    fold_diacritics,
)
from ai_service.extraction.engine import (
    ExtractedField,
    ExtractionEngine,
    ExtractionResult,
)

DATE_PATTERN = re.compile(r"\d{1,2}[/\-.]\d{1,2}[/\-.]\d{4}")

# Longest labels delimit neighbours even if their fields are not applicable.
LABELS = {
    "invoice_number": [
        "số hóa đơn",
        "số hđ",
        "invoice no.",
        "invoice no",
        "invoice number",
    ],
    "issue_date": [
        "ngày lập hóa đơn",
        "ngày hóa đơn",
        "ngày phát hành",
        "ngày lập",
        "ngày làm đơn",
        "invoice date",
        "ngày:",
    ],
    "seller": [
        "tên đơn vị bán hàng",
        "đơn vị bán hàng",
        "đơn vị bán",
        "tên người bán",
        "người bán hàng",
        "người bán",
        "seller",
        "supplier",
    ],
    "address": [
        "địa chỉ người bán",
        "địa chỉ đơn vị bán",
        "nơi thường trú",
        "nơi cư trú",
        "địa chỉ thường trú",
        "permanent residence",
        "place of residence",
        "địa chỉ",
        "address",
        "DC:",
    ],
    "total_amount": [
        "tổng số tiền thanh toán",
        "tổng tiền thanh toán",
        "tổng cộng thanh toán",
        "tổng thanh toán",
        "cộng thanh toán",
        "tổng tiền",
        "tổng cộng",
        "grand total",
        "total amount",
        "amount due",
        "total:",
    ],
    "vat_rate": [
        "thuế suất thuế gtgt",
        "thuế suất gtgt",
        "thuế suất vat",
        "thuế suất",
        "vat rate",
    ],
    "vat": [
        "tiền thuế gtgt",
        "tiền thuế vat",
        "tiền thuế",
        "thuế gtgt",
        "thuế vat",
        "vat amount",
        "vat",
    ],
    "payment_method": [
        "phương thức thanh toán",
        "hình thức thanh toán",
        "payment method",
    ],
    "cccd": [
        "số định danh cá nhân",
        "số định danh",
        "số cccd",
        "số cmnd",
        "personal identification number",
    ],
    "full_name": [
        "họ và tên người làm đơn",
        "họ tên người làm đơn",
        "tên người làm đơn",
        "tôi tên là",
        "họ và tên",
        "họ tên",
        "full name",
        "applicant name",
    ],
    "birth_date": ["ngày tháng năm sinh", "ngày sinh", "date of birth", "NS:"],
    "gender": ["giới tính", "sex", "gender", "GT:"],
    "nationality": ["quốc tịch", "nationality"],
    "hometown": ["quê quán", "place of origin", "QQ:"],
    "phone": ["số điện thoại", "điện thoại", "sđt", "sdt", "phone"],
    "email": ["email", "e-mail"],
    "tax_code": ["mã số thuế", "mst", "tax code"],
    "content": ["nội dung đề nghị", "nội dung chính", "nội dung", "lý do"],
    "_buyer": [
        "tên đơn vị mua hàng",
        "đơn vị mua hàng",
        "họ tên người mua hàng",
        "người mua hàng",
        "người mua",
        "buyer",
    ],
    "_buyer_address": ["địa chỉ người mua", "buyer address"],
    "_other": [
        "cộng tiền hàng",
        "tiền hàng",
        "thành tiền",
        "ngày cấp",
        "nơi cấp",
        "có giá trị đến",
        "bằng chữ",
        "ghi chú",
        "fax",
        "mẫu số",
        "ký hiệu",
    ],
}
ALIASES = {
    fold_diacritics(label).casefold(): name
    for name, labels in LABELS.items()
    for label in labels
}
LABEL_PATTERN = re.compile(
    r"(?<!\w)(?:"
    + "|".join(
        re.escape(alias) + (r"(?=[ \t:|/]|$)" if alias[-1].isalnum() else "")
        for alias in sorted(ALIASES, key=len, reverse=True)
    )
    + ")",
    re.IGNORECASE,
)
IDENTITY_LABEL = re.compile(
    r"^\s*(?:so(?:\s*/\s*no\.?)?|no\.?)\s*(?::|(?=\s+[0-9]))\s*", re.IGNORECASE
)
FORM_TITLE = re.compile(
    r"^(?:don\s+(?!gia\b|vi\b)[^:]{2,100}|bieu mau[^:]{0,100}|to khai[^:]{0,100}|phieu dang ky[^:]{0,100})$",
    re.IGNORECASE,
)
COMMON = {"full_name", "address", "phone", "email", "tax_code"}
INVOICE = {
    "invoice_number",
    "issue_date",
    "seller",
    "address",
    "total_amount",
    "vat",
    "vat_rate",
    "payment_method",
    "tax_code",
    "phone",
    "email",
}
IDENTITY = COMMON | {"cccd", "birth_date", "gender", "nationality", "hometown"}
FORM = COMMON | {"form_name", "issue_date", "content"}
NUMBER_FIXES = str.maketrans({"O": "0", "o": "0", "I": "1", "i": "1", "l": "1"})


def _fold(value: str) -> str:
    folded = fold_diacritics(value).casefold()
    # Only label matching uses these substitutions, never arbitrary free text.
    return folded.replace("h0a", "hoa").replace("d0n", "don").replace("s0 ", "so ")


def _label_matches(line: str):
    text, positions = [], []
    for index, char in enumerate(line):
        folded = _fold(char)
        text.extend(folded)
        positions.extend([index] * len(folded))
    folded = _fold("".join(text))
    matches = [
        (
            positions[m.start()],
            positions[m.end() - 1] + 1,
            ALIASES[m.group().casefold()],
            m.group(),
        )
        for m in LABEL_PATTERN.finditer(folded)
    ]
    identity = IDENTITY_LABEL.match(folded)
    if identity and not any(start < identity.end() for start, *_ in matches):
        matches.insert(0, (0, positions[identity.end() - 1] + 1, "cccd", "so/no"))
    return matches


def _meaningful(value: str) -> str | None:
    value = value.strip(" \t:|;/_")
    if not value or not any(char.isalnum() for char in value):
        return None
    if _fold(value) in {
        "n/a",
        "na",
        "khong co",
        "chua ro",
        "khong xac dinh",
        "none",
        "null",
    }:
        return None
    return value


def _boundary(line: str) -> bool:
    return bool(
        re.match(
            r"(?:can cuoc|chung minh|hoa don|h0a d0n|cong hoa|doc lap|nguoi (?:lam don|mua|ban)|ky ten|ky va ghi|chu ky|stt\b|hang muc\b)",
            _fold(line),
        )
    )


def _digits(value: str, lengths: tuple[int, ...]) -> str | None:
    compact = re.sub(r"[ .\-]", "", value)
    if not any(char.isdigit() for char in compact):
        return None
    compact = compact.translate(NUMBER_FIXES)
    return (
        compact
        if compact.isascii() and compact.isdigit() and len(compact) in lengths
        else None
    )


def _date(value: str) -> str | None:
    match = re.fullmatch(
        r"\s*([0-9OIloi]{1,2})\s*[/.-]\s*([0-9OIloi]{1,2})\s*[/.-]\s*([0-9OIloi]{4})\s*",
        value,
    )
    if not match:
        match = re.fullmatch(
            r"\s*(?:ngay\s+)?([0-9oil]{1,2})\s+thang\s+([0-9oil]{1,2})\s+nam\s+([0-9oil]{4})\s*",
            _fold(value),
        )
    if not match:
        return None
    day, month, year = (int(part.translate(NUMBER_FIXES)) for part in match.groups())
    try:
        date(year, month, day)
    except ValueError:
        return None
    return f"{day:02d}/{month:02d}/{year:04d}"


def _amount(value: str, percent: bool = False) -> str | None:
    match = re.fullmatch(
        r"(?:vnd\s*|usd\s*|\$\s*)?([0-9oil][0-9oil., ]{0,35})\s*(vnd|vnd\.|dong|d|₫|usd|\$|%)?",
        _fold(value),
    )
    if (
        not match
        or (match[2] == "%" and not percent)
        or not any(c.isdigit() for c in match[1])
    ):
        return None
    number = match[1].replace(" ", "").translate(NUMBER_FIXES)
    if not re.fullmatch(r"[0-9]+(?:[.,][0-9]+)*", number):
        return None
    return number + ("%" if match[2] == "%" else "")


def _value(name: str, value: str) -> str | None:
    value = _meaningful(value)
    if value is None:
        return None
    if name in {"seller", "full_name"} and re.fullmatch(
        r"(?:ky|ky ten|ky va ghi ro ho ten|chu ky|signature)", _fold(value)
    ):
        return None
    if name == "cccd":
        return _digits(value, (9, 12))
    if name == "tax_code":
        return _digits(value, (10, 13))
    if name == "phone":
        digits = _digits(value, (10, 11))
        return digits if digits and digits.startswith("0") else None
    if name in {"birth_date", "issue_date"}:
        return _date(value)
    if name in {"total_amount", "vat", "vat_rate"}:
        return _amount(value, percent=name != "total_amount")
    if name == "invoice_number":
        return (
            value
            if re.fullmatch(r"[\w./-]{1,50}", value) and any(c.isdigit() for c in value)
            else None
        )
    if name == "email":
        return value if re.fullmatch(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", value) else None
    if name == "gender":
        return value if _fold(value) in {"nam", "nu", "male", "female"} else None
    if name in {"full_name", "nationality", "hometown"} and not any(
        c.isalpha() for c in value
    ):
        return None
    return value if len(value) <= 1000 else None


class VietnameseFormEngine(ExtractionEngine):
    """Reuse the extraction contract with profiles and explicit label evidence."""

    def extract(self, text: str, document_type: str | None = None) -> ExtractionResult:
        text = (
            unicodedata.normalize("NFC", (text or "")[:1_000_000])
            .replace("\r\n", "\n")
            .replace("\r", "\n")
        )
        kind = (
            document_type or build_vietnamese_classifier().classify(text).document_type
        )
        allowed = (
            INVOICE
            if kind in {"hoa_don", "invoice"}
            else IDENTITY
            if kind in {"cccd", "cmnd"}
            else FORM
            if kind in {"application_form", "don_xin_viec"}
            else COMMON
        )
        lines = [
            re.sub(r"[^\S\n\f]+", " ", line).strip(" \t")[:2048]
            for line in text.replace("\f", "\n\f\n").split("\n")
        ]
        candidates: dict[str, dict[str, tuple[str, str]]] = {}
        party = "seller"

        def add(name: str, value: str, label: str):
            parsed = _value(name, value)
            if parsed is not None and name in allowed:
                candidates.setdefault(name, {})[parsed.casefold()] = (parsed, label)

        for index, line in enumerate(lines):
            if not line or line == "\f":
                continue
            folded = _fold(line)
            if folded.startswith(("(ky", "ky va ghi", "chu ky")):
                continue
            if kind in {"application_form", "don_xin_viec"} and FORM_TITLE.fullmatch(
                folded
            ):
                add("form_name", line, "document title")
            matches = _label_matches(line)
            for position, (start, end, name, label) in enumerate(matches):
                if name == "_buyer":
                    party = "buyer"
                elif name == "seller" or (
                    name == "address"
                    and ("nguoi ban" in label or "don vi ban" in label)
                ):
                    party = "seller"
                if (
                    kind in {"hoa_don", "invoice"}
                    and party == "buyer"
                    and name in {"address", "phone", "email", "tax_code"}
                ):
                    continue
                if name not in allowed:
                    continue
                next_start = (
                    matches[position + 1][0]
                    if position + 1 < len(matches)
                    else len(line)
                )
                value = line[end:next_start].strip(" \t:|;/")
                value_index = index
                if not value and position + 1 < len(matches):
                    continue
                if not value and index + 1 < len(lines):
                    value_index = index + 1
                    if not lines[value_index] and value_index + 1 < len(lines):
                        value_index += 1
                    following = lines[value_index]
                    if (
                        following
                        and following != "\f"
                        and not _label_matches(following)
                        and not FORM_TITLE.fullmatch(_fold(following))
                        and not _boundary(following)
                    ):
                        value = following
                if (
                    name in {"address", "hometown", "content"}
                    and value
                    and next_start == len(line)
                ):
                    empty_lines = 0
                    added_lines = 0
                    for continuation in lines[value_index + 1 : value_index + 5]:
                        if not continuation and name != "content" and empty_lines == 0:
                            empty_lines += 1
                            continue
                        if (
                            not continuation
                            or continuation == "\f"
                            or _label_matches(continuation)
                        ):
                            break
                        if name != "content" and not re.search(
                            r"\b(?:phuong|xa|quan|huyen|tinh|thanh pho|tp\.?|q\.?|p\.?)\b",
                            _fold(continuation),
                        ):
                            break
                        if name == "content" and (
                            re.match(
                                r"(?:nguoi lam don|kinh gui|ky ten|ngay\b)",
                                _fold(continuation),
                            )
                            or re.search(r",\s*ngay\s+\d", _fold(continuation))
                        ):
                            break
                        value += " " + continuation
                        added_lines += 1
                        if added_lines == 2:
                            break
                add(name, value, label)
            if (
                kind in {"application_form", "don_xin_viec", "hoa_don", "invoice"}
                and not matches
            ):
                dated = re.fullmatch(r"(?:[^\n]{1,60},\s*)?ngay\s+(.{1,60})", folded)
                if dated:
                    add("issue_date", dated[1], "ngay/thang/nam")
        result = ExtractionResult(document_type=kind)
        for name, values in candidates.items():
            # Conflicting occurrences are omitted instead of choosing a party/page.
            if len(values) == 1:
                value, label = next(iter(values.values()))
                result.fields.append(
                    ExtractedField(
                        name,
                        value,
                        source="rule",
                        matched_pattern=label,
                        confidence_type="not_estimated",
                    )
                )
        return result


def build_vietnamese_form_engine() -> ExtractionEngine:
    return VietnameseFormEngine()


def extract_dates(text: str) -> list[str]:
    return [match.group(0) for match in DATE_PATTERN.finditer(text)]
