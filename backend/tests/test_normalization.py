"""Raw-format normalization is deterministic, offline and non-mutating."""

from copy import deepcopy
import socket
import unicodedata

import pytest

from app.services.normalization import normalize_invoice

CANONICAL = {
    "invoice_number": "0000123",
    "invoice_date": "2026-04-03",
    "seller_name": "Cửa hàng Mây Việt",
    "total_amount": 125000,
    "currency": "VND",
}


@pytest.fixture(autouse=True)
def block_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def reject(*args, **kwargs):
        raise AssertionError("Normalization tests must not open network connections")

    monkeypatch.setattr(socket.socket, "connect", reject)
    monkeypatch.setattr(socket.socket, "connect_ex", reject)
    monkeypatch.setattr(socket, "create_connection", reject)


def test_canonical_input_is_unchanged_and_versioned() -> None:
    result = normalize_invoice(CANONICAL)

    assert result.candidates == CANONICAL
    assert result.raw_values == CANONICAL
    assert result.raw_values is not CANONICAL
    assert result.errors == []
    assert result.normalization_version == "invoice-normalization-1"
    assert result.source_locale is None


@pytest.mark.parametrize(
    ("field", "raw", "expected"),
    [
        ("invoice_number", " \t0000123\n", "0000123"),
        ("invoice_number", "HD-O001", "HD-O001"),
        ("seller_name", "  Mây\t\nViệt\u00a0 ", "Mây Việt"),
        ("seller_name", unicodedata.normalize("NFD", "Mây Việt"), "Mây Việt"),
        ("invoice_date", " 03/04/2026 ", "2026-04-03"),
        ("invoice_date", "29/02/2024", "2024-02-29"),
        ("invoice_date", "01/01/0001", "0001-01-01"),
        ("invoice_date", "2026-04-03", "2026-04-03"),
        ("total_amount", 0, 0),
        ("total_amount", "000000", 0),
        ("total_amount", "125000", 125000),
        ("total_amount", "125.000", 125000),
        ("total_amount", "1.250.000", 1250000),
        ("total_amount", " 125.000 ₫ ", 125000),
        ("total_amount", "125000 VND", 125000),
        ("total_amount", "125000đ", 125000),
        ("total_amount", "0009007199254740991", 9007199254740991),
        ("currency", " vNd ", "VND"),
        ("currency", "VNĐ", "VND"),
        ("currency", "ĐỒNG", "VND"),
        ("currency", "đ", "VND"),
        ("currency", "₫", "VND"),
    ],
)
def test_supported_formats(field: str, raw: object, expected: object) -> None:
    values = {**CANONICAL, field: raw}
    snapshot = deepcopy(values)

    result = normalize_invoice(values, source_locale="vi-VN")

    assert result.errors == []
    assert result.candidates[field] == expected
    assert type(result.candidates[field]) is type(expected)
    assert values == snapshot
    assert result.raw_values == snapshot


@pytest.mark.parametrize(
    ("field", "raw", "code"),
    [
        ("invoice_date", "03/04/2026", "normalization.ambiguous_date"),
        ("invoice_date", "31/12/2026", "normalization.ambiguous_date"),
        ("invoice_date", "01/02/03", "normalization.invalid_date_format"),
        ("invoice_date", "2026-4-03", "normalization.invalid_date_format"),
        ("invoice_date", "2026-04-03T00:00:00Z", "normalization.invalid_date_format"),
        ("total_amount", "125,000", "normalization.ambiguous_amount"),
        ("total_amount", "1,5 triệu", "normalization.invalid_amount_format"),
        ("total_amount", "125 000", "normalization.invalid_amount_format"),
        ("total_amount", "125.00", "normalization.invalid_amount_format"),
        ("total_amount", "01.000", "normalization.invalid_amount_format"),
        ("total_amount", "-1", "normalization.invalid_amount_format"),
        ("total_amount", "1e3", "normalization.invalid_amount_format"),
        ("total_amount", "１２５０００", "normalization.invalid_amount_format"),
        ("total_amount", "9" * 5000, "normalization.amount_out_of_range"),
        ("currency", "d", "normalization.ambiguous_currency"),
        ("currency", "VND/USD", "normalization.ambiguous_currency"),
        ("currency", "₫ EUR", "normalization.ambiguous_currency"),
        ("seller_name", "Mây\u200bViệt", "normalization.invalid_character"),
        ("seller_name", "Mây\x00Việt", "normalization.invalid_character"),
        ("seller_name", "A\ud800B", "normalization.invalid_character"),
        ("invoice_number", "00\t0123", "normalization.invalid_character"),
    ],
)
def test_unsupported_or_ambiguous_input_is_not_guessed(
    field: str, raw: object, code: str
) -> None:
    result = normalize_invoice({**CANONICAL, field: raw})

    assert result.candidates[field] is None
    assert [(error.field, error.code) for error in result.errors] == [(field, code)]
    assert result.raw_values[field] == raw


@pytest.mark.parametrize("field", CANONICAL)
@pytest.mark.parametrize("raw", [None, "", " \t\n "])
def test_explicit_missing_values_are_not_defaulted(field: str, raw: object) -> None:
    result = normalize_invoice({**CANONICAL, field: raw})

    assert result.candidates[field] is None
    assert result.errors == []


@pytest.mark.parametrize("field", CANONICAL)
def test_absent_key_is_distinct_from_explicit_null(field: str) -> None:
    result = normalize_invoice({key: value for key, value in CANONICAL.items() if key != field})

    assert result.candidates[field] is None
    assert [(error.field, error.code) for error in result.errors] == [(field, "schema.missing_key")]


@pytest.mark.parametrize("raw", [None, [], "invoice", 123, True])
def test_non_object_input_reports_a_root_schema_error(raw: object) -> None:
    result = normalize_invoice(raw)

    assert all(value is None for value in result.candidates.values())
    assert [(error.field, error.code) for error in result.errors] == [(None, "schema.invalid_input")]


@pytest.mark.parametrize("field", CANONICAL)
@pytest.mark.parametrize("raw", [True, 1.5, [], {}])
def test_wrong_raw_types_are_schema_errors(field: str, raw: object) -> None:
    result = normalize_invoice({**CANONICAL, field: raw})

    assert result.candidates[field] is None
    assert [(error.field, error.code) for error in result.errors] == [(field, "schema.invalid_type")]


@pytest.mark.parametrize("currency", [None, "", "  "])
def test_currency_can_come_from_explicit_amount_suffix(currency: object) -> None:
    result = normalize_invoice({**CANONICAL, "total_amount": "125.000 ₫", "currency": currency})

    assert result.candidates["currency"] == "VND"
    assert result.raw_values["currency"] == currency
    assert result.raw_values["total_amount"] == "125.000 ₫"
    assert result.errors == []


@pytest.mark.parametrize("currency", ["USD", "d", "VND/USD", 123])
def test_suffix_does_not_override_conflicting_or_invalid_currency(currency: object) -> None:
    result = normalize_invoice({**CANONICAL, "total_amount": "125000 VND", "currency": currency})

    assert result.candidates["currency"] is None
    assert any(error.field == "currency" for error in result.errors)


def test_suffix_does_not_hide_a_missing_currency_key() -> None:
    raw = {key: value for key, value in CANONICAL.items() if key != "currency"}
    raw["total_amount"] = "125000 VND"

    result = normalize_invoice(raw)

    assert result.candidates["currency"] is None
    assert result.errors[0].code == "schema.missing_key"


@pytest.mark.parametrize("amount", ["abcVND", "125000-VND", "VND"])
def test_suffix_requires_a_separate_marker_after_digits_or_whitespace(amount: str) -> None:
    result = normalize_invoice({**CANONICAL, "total_amount": amount, "currency": None})

    assert result.candidates["currency"] is None
    assert result.candidates["total_amount"] is None
    assert result.errors[0].code == "normalization.invalid_amount_format"


def test_clear_currency_suffix_is_independent_of_invalid_amount_text() -> None:
    result = normalize_invoice({**CANONICAL, "total_amount": "bad VND", "currency": None})

    assert result.candidates["currency"] == "VND"
    assert result.candidates["total_amount"] is None
    assert result.errors[0].code == "normalization.invalid_amount_format"


def test_source_snapshot_is_detached_including_unknown_nested_values() -> None:
    raw = {**CANONICAL, "unexpected": {"items": ["original"]}}
    snapshot = deepcopy(raw)
    result = normalize_invoice(raw)

    result.raw_values["unexpected"]["items"].append("changed result")
    result.candidates["invoice_number"] = "changed result"

    assert raw == snapshot
    assert result.errors[0].code == "schema.extra_forbidden"


def test_unsupported_source_locale_does_not_default_to_vietnamese() -> None:
    result = normalize_invoice({**CANONICAL, "invoice_date": "03/04/2026"}, source_locale="en-US")

    assert result.candidates["invoice_date"] is None
    assert {error.code for error in result.errors} == {
        "schema.unsupported_locale", "normalization.ambiguous_date"
    }


def test_normalization_alone_does_not_claim_business_validity() -> None:
    result = normalize_invoice({**CANONICAL, "invoice_date": "31/04/2026", "total_amount": -1}, source_locale="vi-VN")

    assert result.candidates["invoice_date"] == "2026-04-31"
    assert result.candidates["total_amount"] == -1
    assert result.errors == []
