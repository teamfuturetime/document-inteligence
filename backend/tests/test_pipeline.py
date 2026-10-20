"""Offline provider contract and orchestration checks, with no OCR or image IO."""

from copy import deepcopy
import os
import socket

import pytest
from pydantic import ValidationError

from app.providers.contracts import ExtractionProvider, ProviderError
from app.providers.fake import FakeExtractionProvider
from app.schemas.extraction import (
    DocumentInput, FieldConfidence, PipelineFailure, PipelineSuccess, ProviderIdentity,
    ProviderOutput,
)
from app.schemas.invoice import InvoiceValues
from app.services.pipeline import run_pipeline


@pytest.fixture(autouse=True)
def block_external_resources(monkeypatch: pytest.MonkeyPatch) -> None:
    def reject(*args, **kwargs):
        raise AssertionError("Pipeline tests must not connect or read environment secrets")

    monkeypatch.setattr(socket.socket, "connect", reject)
    monkeypatch.setattr(socket.socket, "connect_ex", reject)
    monkeypatch.setattr(socket, "create_connection", reject)
    monkeypatch.setattr(os, "getenv", reject)


@pytest.fixture
def document() -> DocumentInput:
    # A synthetic marker, deliberately not a PNG. Fake does not decode images.
    return DocumentInput(document_id="synthetic-001", media_type="image/png",
                         content=b"AI02 SYNTHETIC TEST INPUT - NOT AN IMAGE")


class StubProvider:
    """Test-only stand-in; exercises contract boundaries without a provider SDK."""

    identity = ProviderIdentity(name="test-stub", implementation_version="1",
                                config_version="test-1", mode="real")

    def __init__(self, output: object = None, error: Exception | None = None) -> None:
        self.output = output
        self.error = error
        self.calls = 0

    def extract(self, document: DocumentInput) -> ProviderOutput:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.output


def test_fake_implements_protocol_and_returns_explicit_synthetic_raw_candidates(document: DocumentInput) -> None:
    provider = FakeExtractionProvider()

    assert isinstance(provider, ExtractionProvider)
    output = provider.extract(document)

    assert isinstance(output, ProviderOutput)
    assert output.raw_values["invoice_number"] == "FAKE-0000123"
    assert output.raw_values["invoice_date"] == "03/04/2026"
    assert output.raw_values["total_amount"] == "125.000"
    assert provider.identity.mode == "fake"
    assert {"fake_data", "not_derived_from_document"}.issubset(output.warnings)
    assert output.ocr_text is None
    assert all(item.confidence is None and item.evidence == [] for item in output.field_metadata.values())


def test_success_reuses_canonical_model_and_current_schema(document: DocumentInput) -> None:
    result = run_pipeline(document, FakeExtractionProvider(), code_revision="test-code-revision")

    assert isinstance(result, PipelineSuccess)
    assert result.status == "succeeded"
    assert result.document_type == "sales_invoice"
    assert result.schema_version == "1.0.0"
    assert result.validation.valid is True
    assert type(result.validation.normalized_values) is InvoiceValues
    assert result.validation.normalized_values.invoice_number == "FAKE-0000123"
    assert result.validation.normalized_values.invoice_date == "2026-04-03"
    assert result.validation.normalized_values.total_amount == 125000
    assert result.run_metadata.provider.name == "fake-invoice-fixture"
    assert result.run_metadata.provider.implementation_version == "1.0.0"
    assert result.run_metadata.provider.config_version == "synthetic-complete-1"
    assert result.run_metadata.normalization_version == "invoice-normalization-1"
    assert result.run_metadata.pipeline_version == "extraction-pipeline-1"
    assert result.run_metadata.code_revision == "test-code-revision"
    assert PipelineSuccess.model_validate_json(result.model_dump_json()) == result


def test_partial_success_is_not_a_valid_invoice_and_preserves_raw_ambiguity(document: DocumentInput) -> None:
    result = run_pipeline(document, FakeExtractionProvider("partial"))

    assert isinstance(result, PipelineSuccess)
    assert result.validation.valid is False
    assert result.provider_output.raw_values["seller_name"] is None
    assert result.provider_output.raw_values["total_amount"] == "125,000"
    assert result.provider_output.uncertain_fields == ["total_amount"]
    assert result.validation.normalized_values.seller_name is None
    assert result.validation.normalized_values.total_amount is None
    assert {(error.field, error.code) for error in result.validation.errors} == {
        ("seller_name", "business.required"),
        ("total_amount", "normalization.ambiguous_amount"),
    }
    assert all(item.confidence is None and not item.evidence for item in result.provider_output.field_metadata.values())


@pytest.mark.parametrize("scenario", ["complete", "partial", "failure", "timeout"])
def test_same_input_and_configuration_give_identical_results(document: DocumentInput, scenario: str) -> None:
    provider = FakeExtractionProvider(scenario)

    first = run_pipeline(document, provider)
    second = run_pipeline(document, provider)

    assert first.model_dump_json() == second.model_dump_json()
    assert first.run_metadata.code_revision is None


def test_input_and_config_are_part_of_stable_run_identity(document: DocumentInput) -> None:
    first = run_pipeline(document, FakeExtractionProvider())
    changed = DocumentInput(document_id=document.document_id, media_type=document.media_type, content=b"different synthetic bytes")
    other_document = run_pipeline(changed, FakeExtractionProvider())
    other_config = run_pipeline(document, FakeExtractionProvider("partial"))

    assert first.run_metadata.run_id != other_document.run_metadata.run_id
    assert first.run_metadata.content_sha256 != other_document.run_metadata.content_sha256
    assert first.run_metadata.run_id != other_config.run_metadata.run_id
    # Raw fake fixture deliberately does not depend on document contents.
    assert first.provider_output == other_document.provider_output


def test_returned_objects_are_not_shared_fixture_state(document: DocumentInput) -> None:
    provider = FakeExtractionProvider()
    original = provider.extract(document)
    original.raw_values["invoice_number"] = "CHANGED"
    original.field_metadata["invoice_number"].evidence.append("bad mutation")

    fresh = provider.extract(document)

    assert fresh.raw_values["invoice_number"] == "FAKE-0000123"
    assert fresh.field_metadata["invoice_number"].evidence == []


@pytest.mark.parametrize(("scenario", "code"), [("failure", "provider_failed"), ("timeout", "provider_timeout")])
def test_fake_failure_has_no_success_payload(document: DocumentInput, scenario: str, code: str) -> None:
    result = run_pipeline(document, FakeExtractionProvider(scenario))

    assert isinstance(result, PipelineFailure)
    assert result.status == "failed"
    assert result.error.code == code
    assert result.run_metadata.provider.mode == "fake"
    assert "validation" not in result.model_dump()
    assert "provider_output" not in result.model_dump()
    assert PipelineFailure.model_validate_json(result.model_dump_json()) == result


@pytest.mark.parametrize("code", ["provider_unavailable", "provider_timeout", "provider_failed", "invalid_document"])
def test_expected_provider_errors_have_consistent_codes(document: DocumentInput, code: str) -> None:
    result = run_pipeline(document, StubProvider(error=ProviderError(code)))

    assert isinstance(result, PipelineFailure)
    assert result.error.code == code


@pytest.mark.parametrize("error", [TimeoutError("private timeout detail"), RuntimeError("secret=DO_NOT_EXPOSE")])
def test_unexpected_exceptions_are_sanitized(document: DocumentInput, error: Exception, caplog: pytest.LogCaptureFixture) -> None:
    result = run_pipeline(document, StubProvider(error=error))

    assert isinstance(result, PipelineFailure)
    assert result.error.code == ("provider_timeout" if isinstance(error, TimeoutError) else "provider_failed")
    assert str(error) not in result.model_dump_json()
    assert caplog.text == ""
    assert "AI02 SYNTHETIC" not in repr(document)


@pytest.mark.parametrize("field", ["name", "implementation_version", "config_version"])
@pytest.mark.parametrize("value", ["", " "])
def test_identity_requires_actual_nonblank_versions(field: str, value: str) -> None:
    data = FakeExtractionProvider().identity.model_dump()
    data[field] = value

    with pytest.raises(ValidationError):
        ProviderIdentity.model_validate(data)


@pytest.mark.parametrize("mutation", ["missing_key", "wrong_type", "extra_key", "metadata_missing", "unknown_uncertain", "duplicate_uncertain"])
def test_malformed_output_is_rejected_at_pipeline_boundary(document: DocumentInput, mutation: str) -> None:
    data = FakeExtractionProvider().extract(document).model_dump()
    if mutation == "missing_key":
        del data["raw_values"]["invoice_number"]
    elif mutation == "wrong_type":
        data["raw_values"]["total_amount"] = 125000.0
    elif mutation == "extra_key":
        data["raw_values"]["tax"] = "10%"
    elif mutation == "metadata_missing":
        del data["field_metadata"]["currency"]
    elif mutation == "unknown_uncertain":
        data["uncertain_fields"] = ["tax"]
    else:
        data["uncertain_fields"] = ["currency", "currency"]
    invalid = ProviderOutput.model_construct(**data)

    result = run_pipeline(document, StubProvider(output=invalid))

    assert isinstance(result, PipelineFailure)
    assert result.error.code == "invalid_provider_output"


def test_untyped_output_is_not_silently_accepted(document: DocumentInput) -> None:
    data = FakeExtractionProvider().extract(document).model_dump()

    assert run_pipeline(document, StubProvider(output=data)).error.code == "invalid_provider_output"


def test_wrong_schema_version_is_not_accepted(document: DocumentInput) -> None:
    data = run_pipeline(document, FakeExtractionProvider()).model_dump()
    data["schema_version"] = "2.0.0"

    with pytest.raises(ValidationError):
        PipelineSuccess.model_validate(data)


def test_parseable_but_provider_uncertain_field_is_not_accepted(document: DocumentInput) -> None:
    output = FakeExtractionProvider().extract(document)
    output.uncertain_fields = ["invoice_number"]
    original = deepcopy(output.model_dump())

    result = run_pipeline(document, StubProvider(output=output))

    assert isinstance(result, PipelineSuccess)
    assert result.validation.valid is False
    assert result.provider_output.raw_values["invoice_number"] == "FAKE-0000123"
    assert result.validation.normalized_values.invoice_number is None
    assert [(error.field, error.code) for error in result.validation.errors] == [("invoice_number", "extraction.uncertain_field")]
    assert output.model_dump() == original


def test_bad_business_values_remain_errors_not_provider_failure(document: DocumentInput) -> None:
    output = FakeExtractionProvider().extract(document)
    output.raw_values["invoice_date"] = "31/04/2026"
    output.raw_values["currency"] = "USD"

    result = run_pipeline(document, StubProvider(output=output))

    assert isinstance(result, PipelineSuccess)
    assert result.validation.valid is False
    assert result.validation.normalized_values.invoice_date is None
    assert result.validation.normalized_values.currency is None
    assert {(item.field, item.code) for item in result.validation.errors} == {
        ("invoice_date", "business.invalid_date"), ("currency", "business.unsupported_currency")
    }


@pytest.mark.parametrize("kind", ["confidence", "evidence", "ocr", "missing_warning"])
def test_fake_output_cannot_claim_real_evidence_or_hide_its_mode(document: DocumentInput, kind: str) -> None:
    output = FakeExtractionProvider().extract(document)
    if kind in {"confidence", "evidence"}:
        output.field_metadata["invoice_number"].evidence = [
            {"id": "e1", "text": "not genuine evidence", "page": 1, "bbox": None}
        ]
        if kind == "confidence":
            output.field_metadata["invoice_number"].confidence = FieldConfidence(
                score=0.9, source="ocr_aggregation", method_version="test-only",
                calibration_version=None, evidence_ids=["e1"],
            )
    elif kind == "ocr":
        output.ocr_text = "not genuine OCR"
    else:
        output.warnings = []
    provider = StubProvider(output=output)
    provider.identity = FakeExtractionProvider().identity

    result = run_pipeline(document, provider)

    assert isinstance(result, PipelineFailure)
    assert result.error.code == "invalid_provider_output"


def test_bad_document_is_rejected_without_calling_provider() -> None:
    provider = StubProvider()
    document = DocumentInput.model_construct(document_id="bad", media_type="image/png", content=b"")

    result = run_pipeline(document, provider)

    assert isinstance(result, PipelineFailure)
    assert result.error.code == "invalid_input"
    assert provider.calls == 0


def test_bad_identity_is_not_replaced_by_a_fake_default(document: DocumentInput) -> None:
    provider = StubProvider()
    provider.identity = ProviderIdentity.model_construct(name="broken", implementation_version="", config_version="1", mode="real")

    result = run_pipeline(document, provider)

    assert isinstance(result, PipelineFailure)
    assert result.error.code == "invalid_provider_output"
    assert provider.calls == 0


def test_all_missing_values_remain_null(document: DocumentInput) -> None:
    data = FakeExtractionProvider().extract(document).model_dump()
    data["raw_values"] = dict.fromkeys(InvoiceValues.model_fields)
    result = run_pipeline(document, StubProvider(output=ProviderOutput.model_validate(data)))

    assert isinstance(result, PipelineSuccess)
    assert result.validation.valid is False
    assert all(value is None for value in result.validation.normalized_values.model_dump().values())
    assert {issue.field for issue in result.validation.errors} == set(InvoiceValues.model_fields)


@pytest.mark.parametrize("mutation", [
    "unknown_evidence", "duplicate_evidence", "missing_calibration", "nan_score",
    "high_score", "uncertain", "null_value", "bad_box", "wrong_page",
])
def test_invalid_field_metadata_is_rejected(document: DocumentInput, mutation: str) -> None:
    # Test-only metadata, never emitted by the fake provider as model predictions.
    data = FakeExtractionProvider().extract(document).model_dump()
    metadata = data["field_metadata"]["invoice_number"]
    metadata["evidence"] = [{"id": "e1", "text": "synthetic test", "page": 1, "bbox": None}]
    metadata["confidence"] = {
        "score": 0.5, "source": "ocr_aggregation", "method_version": "test-only",
        "calibration_version": None, "evidence_ids": ["e1"],
    }
    if mutation == "unknown_evidence":
        metadata["confidence"]["evidence_ids"] = ["different-field-evidence"]
    elif mutation == "duplicate_evidence":
        metadata["evidence"].append(deepcopy(metadata["evidence"][0]))
    elif mutation == "missing_calibration":
        metadata["confidence"]["source"] = "calibrated_extraction"
    elif mutation == "nan_score":
        metadata["confidence"]["score"] = float("nan")
    elif mutation == "high_score":
        metadata["confidence"]["score"] = 1.1
    elif mutation == "uncertain":
        data["uncertain_fields"] = ["invoice_number"]
    elif mutation == "null_value":
        data["raw_values"]["invoice_number"] = None
    elif mutation == "bad_box":
        metadata["evidence"][0]["bbox"] = {"x0": 4, "y0": 0, "x1": 2, "y1": 2}
    else:
        metadata["evidence"][0]["page"] = 2

    result = run_pipeline(document, StubProvider(output=ProviderOutput.model_construct(**data)))

    assert isinstance(result, PipelineFailure)
    assert result.error.code == "invalid_provider_output"
