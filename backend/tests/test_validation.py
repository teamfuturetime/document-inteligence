"""Structured schema, normalization and business errors without external services."""

from copy import deepcopy
import socket

import pytest
from pydantic import ValidationError

from app.schemas.validation import ValidationResult
from app.services.normalization import normalize_invoice
from app.services.validation import validate_invoice

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
        raise AssertionError("Validation tests must not open network connections")

    monkeypatch.setattr(socket.socket, "connect", reject)
    monkeypatch.setattr(socket.socket, "connect_ex", reject)
    monkeypatch.setattr(socket, "create_connection", reject)


def test_valid_canonical_invoice_and_result_json_round_trip() -> None:
    result = validate_invoice(normalize_invoice(CANONICAL))

    assert result.valid is True
    assert result.normalized_values.model_dump() == CANONICAL
    assert result.errors == result.warnings == []
    assert ValidationResult.model_validate_json(result.model_dump_json()) == result


def test_normalize_then_validate_supported_source_formats() -> None:
    raw = {
        "invoice_number": " 0000123 ",
        "invoice_date": "03/04/2026",
        "seller_name": " Cửa hàng\nMây Việt ",
        "total_amount": "125.000 ₫",
        "currency": None,
    }
    snapshot = deepcopy(raw)

    result = validate_invoice(normalize_invoice(raw, source_locale="vi-VN"))

    assert result.valid is True
    assert result.normalized_values.model_dump() == CANONICAL
    assert raw == snapshot


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("invoice_date", "2026-02-29", "business.invalid_date"),
        ("invoice_date", "1900-02-29", "business.invalid_date"),
        ("invoice_date", "31/04/2026", "business.invalid_date"),
        ("invoice_date", "0000-01-01", "business.invalid_date"),
        ("total_amount", -1, "business.out_of_range"),
        ("total_amount", 9007199254740992, "business.out_of_range"),
        ("total_amount", "9.007.199.254.740.992", "business.out_of_range"),
        ("total_amount", "9" * 5000, "normalization.amount_out_of_range"),
        ("total_amount", 125000.0, "schema.invalid_type"),
        ("total_amount", True, "schema.invalid_type"),
        ("total_amount", "125,000", "normalization.ambiguous_amount"),
        ("total_amount", "1,5 triệu", "normalization.invalid_amount_format"),
        ("total_amount", "125.00", "normalization.invalid_amount_format"),
        ("currency", "USD", "business.unsupported_currency"),
        ("currency", "d", "normalization.ambiguous_currency"),
        ("currency", "VND/USD", "normalization.ambiguous_currency"),
        ("seller_name", "123-456", "business.invalid_seller_name"),
        ("seller_name", "A" * 201, "schema.invalid_length"),
        ("seller_name", "Mây\u200bViệt", "normalization.invalid_character"),
        ("invoice_number", "HĐ-0001", "schema.invalid_format"),
        ("invoice_number", "00 0123", "schema.invalid_format"),
        ("invoice_number", "A" * 101, "schema.invalid_length"),
        ("invoice_number", 123, "schema.invalid_type"),
    ],
)
def test_error_categories_and_field_locations(field: str, value: object, code: str) -> None:
    result = validate_invoice(normalize_invoice({**CANONICAL, field: value}, source_locale="vi-VN"))

    assert result.valid is False
    assert [(error.field, error.code) for error in result.errors] == [(field, code)]
    assert result.normalized_values.model_dump()[field] is None
    for key in CANONICAL.keys() - {field}:
        assert result.normalized_values.model_dump()[key] == CANONICAL[key]


@pytest.mark.parametrize("field", CANONICAL)
@pytest.mark.parametrize("value", [None, "", "  \n\t "])
def test_missing_values_are_required_business_errors(field: str, value: object) -> None:
    result = validate_invoice(normalize_invoice({**CANONICAL, field: value}))

    assert result.valid is False
    assert [(error.field, error.code) for error in result.errors] == [(field, "business.required")]
    assert result.normalized_values.model_dump()[field] is None


def test_multiple_errors_are_all_reported_once_and_inputs_remain_unchanged() -> None:
    raw = {"invoice_date": "31/04/2026", "seller_name": "123", "total_amount": "125,000", "currency": "USD"}
    original = deepcopy(raw)
    normalized = normalize_invoice(raw, source_locale="vi-VN")
    candidates = deepcopy(normalized.candidates)
    original_errors = deepcopy(normalized.errors)

    result = validate_invoice(normalized)

    assert result.valid is False
    assert {(error.field, error.code) for error in result.errors} == {
        ("invoice_number", "schema.missing_key"),
        ("invoice_date", "business.invalid_date"),
        ("seller_name", "business.invalid_seller_name"),
        ("total_amount", "normalization.ambiguous_amount"),
        ("currency", "business.unsupported_currency"),
    }
    assert len(result.errors) == 5
    assert all(value is None for value in result.normalized_values.model_dump().values())
    assert raw == original
    assert normalized.candidates == candidates
    assert normalized.errors == original_errors


@pytest.mark.parametrize("raw", [None, [], "invoice"])
def test_invalid_root_input_does_not_generate_five_spurious_required_errors(raw: object) -> None:
    result = validate_invoice(normalize_invoice(raw))

    assert result.valid is False
    assert [(error.field, error.code) for error in result.errors] == [(None, "schema.invalid_input")]
    assert all(value is None for value in result.normalized_values.model_dump().values())


def test_unknown_key_is_an_error_even_when_all_five_known_values_are_valid() -> None:
    result = validate_invoice(normalize_invoice({**CANONICAL, "confidence": 1.0}))

    assert result.valid is False
    assert result.normalized_values.model_dump() == CANONICAL
    assert [(error.field, error.code) for error in result.errors] == [(None, "schema.extra_forbidden")]
    assert "confidence" not in result.model_dump()
    assert "status" not in result.model_dump()
    assert "confirmed" not in result.model_dump()


def test_empty_object_reports_all_missing_keys_without_defaults() -> None:
    result = validate_invoice(normalize_invoice({}))

    assert result.valid is False
    assert {(error.field, error.code) for error in result.errors} == {
        (field, "schema.missing_key") for field in CANONICAL
    }
    assert all(value is None for value in result.normalized_values.model_dump().values())


def test_conflicting_suffix_is_not_silently_replaced_with_vnd() -> None:
    result = validate_invoice(normalize_invoice({**CANONICAL, "total_amount": "125000 VND", "currency": "USD"}))

    assert result.valid is False
    assert result.normalized_values.total_amount == 125000
    assert result.normalized_values.currency is None
    assert [(error.field, error.code) for error in result.errors] == [("currency", "normalization.ambiguous_currency")]


def test_dmy_with_unknown_source_is_an_error_but_iso_does_not_need_locale() -> None:
    result = validate_invoice(normalize_invoice({**CANONICAL, "invoice_date": "03/04/2026"}))

    assert result.valid is False
    assert result.errors[0].code == "normalization.ambiguous_date"
    assert validate_invoice(normalize_invoice(CANONICAL)).valid is True


@pytest.mark.parametrize("day", ["0001-01-01", "9999-12-31", "2000-02-29"])
def test_no_undocumented_past_or_future_date_rule(day: str) -> None:
    result = validate_invoice(normalize_invoice({**CANONICAL, "invoice_date": day}))

    assert result.valid is True
    assert result.normalized_values.invoice_date == day


@pytest.mark.parametrize("amount", [0, 9007199254740991])
def test_documented_money_boundaries_are_accepted(amount: int) -> None:
    result = validate_invoice(normalize_invoice({**CANONICAL, "total_amount": amount}))

    assert result.valid is True
    assert result.normalized_values.total_amount == amount


@pytest.mark.parametrize(
    ("valid", "values", "errors"),
    [
        (True, {**CANONICAL, "currency": None}, []),
        (False, CANONICAL, []),
        (False, {**CANONICAL, "currency": None}, []),
        (True, CANONICAL, [{"field": "currency", "code": "business.required", "message": "Required"}]),
    ],
)
def test_result_cannot_claim_success_with_errors_or_missing_values(
    valid: bool, values: dict, errors: list
) -> None:
    with pytest.raises(ValidationError):
        ValidationResult(valid=valid, normalized_values=values, errors=errors, warnings=[])
