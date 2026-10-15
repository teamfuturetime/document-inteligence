import unicodedata

from fastapi.testclient import TestClient
import pytest

from document_backend.main import create_app
from document_backend.services.validation import validate_review
from document_contracts.models import MAX_SAFE_INTEGER, ValidationRequest, ValidationResponse


def payload(**changes):
    return {"schema_version": "1.0.0", "values": {
        "invoice_number": "SYN-1", "invoice_date": "2024-02-29",
        "seller_name": "Cửa hàng Mây Việt", "total_amount": "125.000", "currency": "VND",
        **changes,
    }}


def test_normalizes_unicode_spaces_amount_currency_without_mutating_request():
    request = ValidationRequest.model_validate(payload(
        seller_name=unicodedata.normalize("NFD", " Cửa  hàng Mây Việt "), currency="vnđ"))
    before = request.model_dump_json()
    result = validate_review(request)
    assert result.valid and result.errors == []
    assert result.normalized_values.total_amount == 125000
    assert result.normalized_values.seller_name == "Cửa hàng Mây Việt"
    assert result.normalized_values.currency == "VND"
    assert request.model_dump_json() == before


@pytest.mark.parametrize("field,value,code", [
    ("invoice_number", None, "required"), ("seller_name", " ", "required"),
    ("invoice_date", "2026-02-29", "invalid_date"),
    ("invoice_date", "03/04/2026", "invalid_format"),
    ("invoice_date", "0000-01-01", "invalid_date"),
    ("total_amount", "-1", "out_of_range"),
    ("total_amount", str(MAX_SAFE_INTEGER + 1), "out_of_range"),
    ("total_amount", "9" * 999, "out_of_range"),
    ("total_amount", "1e3", "invalid_format"),
    ("total_amount", "125,50", "invalid_format"),
    ("currency", "USD", "unsupported_currency"),
    ("invoice_number", "x" * 101, "out_of_range"),
    ("seller_name", "x" * 201, "out_of_range"),
])
def test_invalid_field_is_null_and_has_exact_error(field, value, code):
    result = validate_review(ValidationRequest.model_validate(payload(**{field: value})))
    assert not result.valid
    assert getattr(result.normalized_values, field) is None
    assert [(error.field, error.code) for error in result.errors] == [(field, code)]


@pytest.mark.parametrize("amount", ["0", str(MAX_SAFE_INTEGER)])
def test_amount_boundaries(amount):
    result = validate_review(ValidationRequest.model_validate(payload(total_amount=amount)))
    assert result.valid and result.normalized_values.total_amount == int(amount)


def test_actual_endpoint_returns_200_for_field_errors_and_contract_response():
    with TestClient(create_app()) as client:
        response = client.post("/api/v1/validate", json=payload(invoice_date="2026-02-30", currency=None))
    assert response.status_code == 200
    result = ValidationResponse.model_validate(response.json())
    assert not result.valid and {error.field for error in result.errors} == {"invoice_date", "currency"}


@pytest.mark.parametrize("bad", [
    {"schema_version": "2.0.0", "values": {}},
    payload(total_amount=123), payload(total_amount=True),
    {**payload(), "extra": "private-input"},
])
def test_bad_wire_input_is_422_and_does_not_echo_input(bad):
    with TestClient(create_app()) as client:
        response = client.post("/api/v1/validate", json=bad)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
    assert "private-input" not in response.text
