import json
import unicodedata

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from docintel.config import ROOT
from docintel.domain.models import (
    Confidence,
    DraftApplicationData,
    ExportArtifact,
    FieldPrediction,
    FinalApplicationData,
    OCRSpan,
    ReviewedField,
)
from docintel.domain.normalization import normalize_draft, normalize_value
from docintel.domain.review import effective_value
from docintel.domain.validation import validate_draft


def valid_data():
    return json.loads(
        (ROOT / "contracts/examples/export-fixture.json").read_text(encoding="utf-8")
    )["data"]


def test_leading_zero_and_vietnamese():
    name = unicodedata.normalize("NFD", "Nguyễn Minh An")
    assert normalize_value("full_name", "  " + name + "\n") == "Nguyễn Minh An"
    assert normalize_value("student_id", " 00123456 ") == "00123456"
    assert normalize_value("request_content", "Xin\n  xác nhận") == "Xin xác nhận"
    with pytest.raises(TypeError):
        normalize_value("student_id", 123456)
    with pytest.raises(ValidationError):
        DraftApplicationData(student_id=123456)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("12/03/2005", "2005-03-12"),
        ("29/02/2024", "2024-02-29"),
        ("31/02/2005", "31/02/2005"),
        ("03/04/05", "03/04/05"),
        ("", None),
    ],
)
def test_deterministic_dates(raw, expected):
    assert normalize_value("date_of_birth", raw) == expected


@pytest.mark.parametrize("invalid", ["2005-02-31", "2025-02-29", "2026-13-01", "20050312"])
def test_calendar_invalid_in_draft_and_final(invalid):
    data = {**valid_data(), "date_of_birth": invalid}
    draft = DraftApplicationData(**data)
    assert any(issue.code == "INVALID_DATE" for issue in validate_draft(draft))
    with pytest.raises(ValidationError):
        FinalApplicationData(**data)


def test_missing_and_date_order():
    draft = normalize_draft(
        DraftApplicationData(**{**valid_data(), "faculty": "  ", "request_date": "2000-01-01"})
    )
    codes = {issue.code for issue in validate_draft(draft)}
    assert codes == {"MISSING_REQUIRED", "DATE_ORDER"}
    with pytest.raises(ValidationError):
        FinalApplicationData(**{**valid_data(), "request_date": "2000-01-01"})
    assert len(validate_draft(DraftApplicationData())) == 7


def test_reviewed_null_never_restores_machine():
    assert effective_value("An", ReviewedField(is_reviewed=True, reviewed_value=None)) is None
    assert effective_value("An", ReviewedField(is_reviewed=False, reviewed_value=None)) == "An"
    with pytest.raises(ValidationError):
        ReviewedField(is_reviewed=False, reviewed_value="Bảo")


def test_export_example_and_confirmation_gate():
    payload = json.loads(
        (ROOT / "contracts/examples/export-fixture.json").read_text(encoding="utf-8")
    )
    artifact = ExportArtifact.model_validate(payload)
    assert artifact.data.student_id.startswith("00")
    assert artifact.provenance.prediction_source == "fixture"
    with pytest.raises(ValidationError):
        ExportArtifact.model_validate({**payload, "review_status": "draft"})
    with pytest.raises(ValidationError):
        ExportArtifact.model_validate({**payload, "revision": 0})
    with pytest.raises(ValidationError):
        ExportArtifact.model_validate({**payload, "data": {**payload["data"], "faculty": None}})


def test_generated_schemas_and_examples():
    for path in (ROOT / "contracts/generated").glob("*.schema.json"):
        Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))
    for schema_name, example_name in [
        ("ExportArtifact", "export-fixture"),
        ("DraftApplicationData", "draft-invalid"),
        ("FixtureView", "fixture-view"),
    ]:
        schema = json.loads(
            (ROOT / f"contracts/generated/{schema_name}.schema.json").read_text(encoding="utf-8")
        )
        example = json.loads(
            (ROOT / f"contracts/examples/{example_name}.json").read_text(encoding="utf-8")
        )
        Draft202012Validator(schema).validate(example)


def test_extra_keys_rejected():
    with pytest.raises(ValidationError):
        DraftApplicationData(full_name="An", invented="Không có")


def test_final_requires_normalized_text():
    with pytest.raises(ValidationError):
        FinalApplicationData(**{**valid_data(), "full_name": "  Nguyễn Minh An  "})


def test_evidence_bounds_and_unknown_confidence():
    with pytest.raises(ValidationError):
        Confidence(method="unknown", score=0.9)
    with pytest.raises(ValidationError):
        OCRSpan(
            span_id="s",
            page_index=0,
            text="An",
            image_width=100,
            image_height=100,
            polygon=[
                {"x": 0.0, "y": 0.0},
                {"x": 101.0, "y": 0.0},
                {"x": 101.0, "y": 10.0},
                {"x": 0.0, "y": 10.0},
            ],
        )
    with pytest.raises(ValidationError):
        FieldPrediction(
            field_id="full_name",
            raw_value="An",
            normalized_value="An",
            observation="unknown",
            evidence_status="unavailable",
        )
