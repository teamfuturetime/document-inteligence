"""Offline contract tests against the documented sales_invoice 1.0.0 decisions."""

from datetime import date
from decimal import Decimal
import json
import socket
import unicodedata

import pytest
from pydantic import ValidationError

from app.schemas import FinalInvoiceValues, InvoiceValues

InvoiceModel = type[InvoiceValues] | type[FinalInvoiceValues]
VALID_INVOICE = {
    "invoice_number": "HD-0000123",
    "invoice_date": "2026-04-03",
    "seller_name": "Cửa hàng Mây Việt — DỮ LIỆU GIẢ",
    "total_amount": 125000,
    "currency": "VND",
}
FIELDS = tuple(VALID_INVOICE)


@pytest.fixture(autouse=True)
def block_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def reject_connection(*args, **kwargs):
        raise AssertionError("Schema tests must not open network connections")

    monkeypatch.setattr(socket.socket, "connect", reject_connection)
    monkeypatch.setattr(socket.socket, "connect_ex", reject_connection)
    monkeypatch.setattr(socket, "create_connection", reject_connection)


@pytest.fixture(params=[InvoiceValues, FinalInvoiceValues], ids=["partial", "final"])
def model_type(request: pytest.FixtureRequest) -> InvoiceModel:
    return request.param


def test_valid_values_round_trip_without_changes(model_type: InvoiceModel) -> None:
    result = model_type.model_validate(VALID_INVOICE)

    assert result.model_dump() == VALID_INVOICE
    assert model_type.model_validate_json(result.model_dump_json()).model_dump() == VALID_INVOICE


@pytest.mark.parametrize("field", FIELDS)
def test_partial_values_allow_explicit_null(field: str) -> None:
    values = {**VALID_INVOICE, field: None}

    assert InvoiceValues.model_validate(values).model_dump() == values


def test_all_null_values_round_trip_without_defaults() -> None:
    values = dict.fromkeys(FIELDS)
    result = InvoiceValues.model_validate_json(json.dumps(values))

    assert result.model_dump() == values
    assert json.loads(result.model_dump_json()) == values


@pytest.mark.parametrize("field", FIELDS)
def test_omitted_keys_are_errors_even_for_partial_values(
    model_type: InvoiceModel, field: str
) -> None:
    values = {key: value for key, value in VALID_INVOICE.items() if key != field}

    with pytest.raises(ValidationError) as error:
        model_type.model_validate(values)

    assert [(item["loc"], item["type"]) for item in error.value.errors()] == [
        ((field,), "missing")
    ]


@pytest.mark.parametrize("field", FIELDS)
def test_final_values_reject_null(field: str) -> None:
    with pytest.raises(ValidationError) as error:
        FinalInvoiceValues.model_validate({**VALID_INVOICE, field: None})

    assert error.value.errors()[0]["loc"] == (field,)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("invoice_number", "0"),
        ("invoice_number", "0000123"),
        ("invoice_number", "AbC-00/01._Z"),
        ("invoice_number", "A" * 100),
        ("invoice_date", "0001-01-01"),
        ("invoice_date", "9999-12-31"),
        ("invoice_date", "2024-02-29"),
        ("invoice_date", "2000-02-29"),
        ("seller_name", "Đại lý 02"),
        ("seller_name", "A"),
        ("seller_name", "A" * 200),
        ("seller_name", "A" + "😀" * 199),
        ("total_amount", 0),
        ("total_amount", 9_007_199_254_740_991),
    ],
)
def test_documented_valid_boundaries_are_preserved(
    model_type: InvoiceModel, field: str, value: object
) -> None:
    result = model_type.model_validate({**VALID_INVOICE, field: value})

    assert result.model_dump()[field] == value
    assert type(result.model_dump()[field]) is type(value)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("invoice_number", ""),
        ("invoice_number", "A" * 101),
        ("invoice_number", " 0000123"),
        ("invoice_number", "0000123 "),
        ("invoice_number", "00 0123"),
        ("invoice_number", "0000123\n"),
        ("invoice_number", "HD\x00-123"),
        ("invoice_number", "HĐ-123"),
        ("invoice_number", "-123"),
        ("invoice_number", 123),
        ("invoice_number", b"0000123"),
        ("invoice_number", True),
        ("invoice_date", ""),
        ("invoice_date", "03/04/2026"),
        ("invoice_date", "2026-4-03"),
        ("invoice_date", "20260403"),
        ("invoice_date", "2026-04-03T00:00:00Z"),
        ("invoice_date", "2026-02-29"),
        ("invoice_date", "1900-02-29"),
        ("invoice_date", "2026-04-31"),
        ("invoice_date", "2026-13-01"),
        ("invoice_date", "0000-01-01"),
        ("invoice_date", "２０２６-04-03"),
        ("invoice_date", "2026-04-03\n"),
        ("invoice_date", date(2026, 4, 3)),
        ("seller_name", ""),
        ("seller_name", "   "),
        ("seller_name", "123-456"),
        ("seller_name", "A" * 201),
        ("seller_name", "A" + "😀" * 200),
        ("seller_name", unicodedata.normalize("NFD", "Mây Việt")),
        ("seller_name", " Mây Việt"),
        ("seller_name", "Mây Việt "),
        ("seller_name", "Mây  Việt"),
        ("seller_name", "Mây\tViệt"),
        ("seller_name", "Mây\nViệt"),
        ("seller_name", "Mây\u00a0Việt"),
        ("seller_name", "Mây\u200bViệt"),
        ("seller_name", "Mây\x00Việt"),
        ("seller_name", "A\ud800B"),
        ("seller_name", 123),
        ("total_amount", -1),
        ("total_amount", 9_007_199_254_740_992),
        ("total_amount", 125000.0),
        ("total_amount", 1.5),
        ("total_amount", True),
        ("total_amount", False),
        ("total_amount", "125000"),
        ("total_amount", "125.000"),
        ("total_amount", "125,000"),
        ("total_amount", "125000 VND"),
        ("total_amount", "1e3"),
        ("total_amount", ""),
        ("total_amount", Decimal("125000")),
        ("total_amount", float("inf")),
        ("total_amount", float("nan")),
        ("currency", "USD"),
        ("currency", "vnd"),
        ("currency", "VNĐ"),
        ("currency", "đồng"),
        ("currency", "đ"),
        ("currency", "₫"),
        ("currency", " VND "),
        ("currency", ""),
        ("currency", b"VND"),
    ],
)
def test_invalid_or_unnormalized_values_are_rejected(
    model_type: InvoiceModel, field: str, value: object
) -> None:
    with pytest.raises(ValidationError) as error:
        model_type.model_validate({**VALID_INVOICE, field: value})

    assert error.value.errors()[0]["loc"] == (field,)


@pytest.mark.parametrize("value", [True, 125000.0, "125,000"])
def test_json_input_keeps_amount_type_strict(
    model_type: InvoiceModel, value: object
) -> None:
    with pytest.raises(ValidationError) as error:
        model_type.model_validate_json(json.dumps({**VALID_INVOICE, "total_amount": value}))

    assert error.value.errors()[0]["loc"] == ("total_amount",)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("status", "candidate"),
        ("warnings", []),
        ("confidence", None),
        ("confidence", 1.0),
        ("schema_version", "1.0.0"),
        ("document_type", "sales_invoice"),
        ("confirmed", True),
        ("unexpected", "extra"),
    ],
)
def test_values_reject_envelope_metadata_and_unknown_keys(
    model_type: InvoiceModel, field: str, value: object
) -> None:
    with pytest.raises(ValidationError) as error:
        model_type.model_validate({**VALID_INVOICE, field: value})

    assert [(item["loc"], item["type"]) for item in error.value.errors()] == [
        ((field,), "extra_forbidden")
    ]


def test_value_fields_do_not_accept_extraction_wrappers(model_type: InvoiceModel) -> None:
    field = {"value": "0000123", "status": "candidate", "warnings": [], "confidence": None}

    with pytest.raises(ValidationError) as error:
        model_type.model_validate({**VALID_INVOICE, "invoice_number": field})

    assert error.value.errors()[0]["loc"] == ("invoice_number",)


def test_assignment_also_preserves_value_constraints(model_type: InvoiceModel) -> None:
    result = model_type.model_validate(VALID_INVOICE)

    with pytest.raises(ValidationError):
        result.total_amount = -1

    assert result.total_amount == 125000
    result.invoice_number = "0000456"
    assert result.invoice_number == "0000456"
