"""Contract regressions run without a server or OCR engine."""

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from pydantic import ValidationError

from document_contracts.models import (
    CONTRACT_MODELS, BoundingBox, ExtractionResponse, InvoiceValues, OCRResult,
    ReviewedExport, ValidationResponse,
)
from backend.export_schemas import schema_text

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "schemas" / "fixtures"
MANIFEST = json.loads((FIXTURES / "manifest.json").read_text())["cases"]


def fixture(name):
    return json.loads((FIXTURES / f"{name}.json").read_text())


@pytest.mark.parametrize("case", MANIFEST, ids=lambda case: case["file"])
def test_fixture_matches_python_and_json_schema(case):
    data = json.loads((FIXTURES / case["file"]).read_text())
    model = CONTRACT_MODELS[case["schema"]]
    schema = json.loads((ROOT / "schemas/v1" / f'{case["schema"]}.schema.json').read_text())
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = list(validator.iter_errors(data))
    if case["valid"]:
        assert not errors
        assert model.model_validate(data).model_dump(mode="json") == data
    else:
        assert errors
        with pytest.raises(ValidationError):
            model.model_validate(data)


@pytest.mark.parametrize("name,model", CONTRACT_MODELS.items())
def test_exported_schema_has_no_drift(name, model):
    path = ROOT / "schemas/v1" / f"{name}.schema.json"
    assert path.read_text() == schema_text(name, model)
    Draft202012Validator.check_schema(json.loads(path.read_text()))


@pytest.mark.parametrize("amount", [True, 1.5, "1", -1, 9_007_199_254_740_992])
def test_reject_unsafe_or_coerced_amount(amount):
    data = fixture("invoice-values")
    data["total_amount"] = amount
    with pytest.raises(ValidationError):
        InvoiceValues.model_validate(data)


def test_zero_amount_and_leap_day_are_valid():
    data = fixture("invoice-values")
    data.update(total_amount=0, invoice_date="2024-02-29")
    assert InvoiceValues.model_validate(data).total_amount == 0


@pytest.mark.parametrize("value", ["2025-02-29", "09/10/2026", "2026-1-01"])
def test_invalid_dates_rejected(value):
    data = fixture("invoice-values")
    data["invoice_date"] = value
    with pytest.raises(ValidationError):
        InvoiceValues.model_validate(data)


@pytest.mark.parametrize("value", ["", "   "])
def test_empty_seller_rejected(value):
    data = fixture("invoice-values")
    data["seller_name"] = value
    with pytest.raises(ValidationError):
        InvoiceValues.model_validate(data)


def test_missing_key_is_different_from_null():
    data = fixture("invoice-values")
    del data["currency"]
    with pytest.raises(ValidationError):
        InvoiceValues.model_validate(data)
    data["currency"] = None
    assert InvoiceValues.model_validate(data).currency is None


@pytest.mark.parametrize("score", [-0.1, 1.1, float("nan"), float("inf")])
def test_invalid_confidence_rejected(score):
    data = fixture("extraction-success")
    data["fields"]["currency"]["confidence"] = score
    with pytest.raises(ValidationError):
        ExtractionResponse.model_validate(data)


def test_missing_value_cannot_claim_confidence():
    data = fixture("extraction-missing")
    data["fields"]["invoice_number"]["confidence"] = 0.9
    with pytest.raises(ValidationError):
        ExtractionResponse.model_validate(data)


def test_success_response_cannot_hide_errors_or_missing_values():
    data = fixture("validation-field-error")
    data["valid"] = True
    with pytest.raises(ValidationError):
        ValidationResponse.model_validate(data)
    data["errors"] = []
    with pytest.raises(ValidationError):
        ValidationResponse.model_validate(data)


def test_invalid_response_requires_matching_field_errors():
    data = fixture("validation-field-error")
    data["errors"][0]["field"] = "seller_name"
    with pytest.raises(ValidationError):
        ValidationResponse.model_validate(data)


def test_bounding_box_reversed_or_outside_page_rejected():
    with pytest.raises(ValidationError):
        BoundingBox(x0=10, y0=0, x1=5, y1=20)
    data = fixture("ocr-mock")
    data["page"]["tokens"][0]["box"]["x1"] = 1201
    with pytest.raises(ValidationError):
        OCRResult.model_validate(data)


@pytest.mark.parametrize("edited", [[], ["seller_name"], ["total_amount", "total_amount"]])
def test_export_cannot_misrepresent_reviewed_fields(edited):
    data = fixture("reviewed-export")
    data["edited_fields"] = edited
    with pytest.raises(ValidationError):
        ReviewedExport.model_validate(data)


def test_export_does_not_change_original_ai_score():
    data = fixture("reviewed-export")
    before = copy.deepcopy(data["original_extraction"])
    result = ReviewedExport.model_validate(data)
    assert result.original_extraction.model_dump() == before
    assert result.values.total_amount != result.original_extraction.fields.total_amount.value
