"""Offline fixture/parser/metric checks; no assertions about VLM quality or speed."""

from dataclasses import replace
import json
from pathlib import Path
import socket
import subprocess
import sys

import pytest
from pydantic import ValidationError

from app.benchmark.contracts import BenchmarkIdentity, BenchmarkRequest, OCRContext, digest
from app.benchmark.fixtures import FixtureResponseProvider, load_dataset
from app.benchmark.metrics import field_metrics, summarize
from app.benchmark.parser import adapt_response
from app.benchmark.runner import run_benchmark
from app.providers.contracts import ProviderError
from app.schemas.extraction import ProviderIdentity
from app.schemas.invoice import InvoiceValues
from app.services.normalization import FIELD_NAMES

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data/benchmark-fixture"


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def reject(*args, **kwargs):
        raise AssertionError("Benchmark fixture tests must stay offline")
    monkeypatch.setattr(socket.socket, "connect", reject)
    monkeypatch.setattr(socket.socket, "connect_ex", reject)
    monkeypatch.setattr(socket, "create_connection", reject)
    monkeypatch.setattr("app.providers.tesseract.TesseractOCRProvider.recognize", reject)


@pytest.fixture
def dataset():
    return load_dataset(ROOT / "data/ocr-smoke/manifest.json", DATA / "ocr-inputs.json", DATA / "labels.json")


@pytest.fixture
def provider():
    return FixtureResponseProvider(DATA / "responses.json")


@pytest.fixture
def request_data(dataset):
    case = dataset.cases[0]
    return BenchmarkRequest(sample_id=case.image.document_id, mode="image+ocr", image=case.image,
                            ocr=case.ocr, source_locale=case.source_locale)


@pytest.fixture
def response(provider, request_data):
    fenced = provider.respond(request_data)
    return json.loads(fenced.splitlines()[1])


def run(dataset, provider, **kwargs):
    return run_benchmark(dataset, provider, fixture_sha256="fixture-test-version", **kwargs)


def test_complete_response_preserves_values_evidence_and_separates_scores(request_data, response, dataset):
    response["model_reported_scores"] = {"invoice_number": 0.99}  # Simulated, uncalibrated model output.
    before = request_data.model_dump()
    result = adapt_response(json.dumps(response), request_data)
    assert result.status == "processed"
    assert result.candidate_validation.valid and result.accepted_validation.valid
    assert result.accepted_validation.normalized_values == dataset.cases[0].ground_truth
    assert result.output.raw_values["invoice_number"] == "HD-0000123"
    assert result.output.raw_values["total_amount"] == "125.000"
    assert result.model_reported_scores == {"invoice_number": 0.99}
    assert all(metadata.confidence is None for metadata in result.output.field_metadata.values())
    for field, metadata in result.output.field_metadata.items():
        span = next(s for s in request_data.ocr.spans if s.id == metadata.evidence[0].id)
        assert metadata.evidence[0].text == request_data.ocr.text[span.start:span.end]
        assert metadata.evidence[0].bbox is None
    assert request_data.model_dump() == before


@pytest.mark.parametrize("fence", [None, "json", "JSON", ""])
def test_json_and_whole_markdown_fence_are_supported(request_data, response, fence):
    raw = json.dumps(response)
    if fence is not None:
        raw = f"```{fence}\n{raw}\n```"
    assert adapt_response(raw, request_data).status == "processed"


@pytest.mark.parametrize("raw", ["", "not json", '{"raw_values":', '{"a":NaN}', '{"a":Infinity}',
    '{"a":1,"a":2}', '{"raw_values":{"currency":"VND","currency":null}}',
    'Here is JSON: {}', '```python\n{}\n```', '```json\n{}\n```\nextra', '```json\n{}',
    '```json\n{}\n```\n```json\n{}\n```'])
def test_malformed_json_is_reported_without_repair(request_data, raw):
    result = adapt_response(raw, request_data)
    assert result.status == "parse_error"
    assert result.output is None
    assert all(issue.code.startswith("parse.") for issue in result.issues)


@pytest.mark.parametrize("kind", ["missing", "extra_field", "extra_top", "bool_amount", "float_amount", "numeric_id", "bad_evidence_type", "unknown_evidence_field", "confidence_extra", "array_root"])
def test_schema_errors_are_distinct_from_parse_errors(request_data, response, kind):
    if kind == "missing": del response["raw_values"]["seller_name"]
    elif kind == "extra_field": response["raw_values"]["tax"] = 10
    elif kind == "extra_top": response["other"] = True
    elif kind == "bool_amount": response["raw_values"]["total_amount"] = True
    elif kind == "float_amount": response["raw_values"]["total_amount"] = 125000.0
    elif kind == "numeric_id": response["raw_values"]["invoice_number"] = 123
    elif kind == "bad_evidence_type": response["evidence"]["seller_name"] = "s3"
    elif kind == "unknown_evidence_field": response["evidence"]["tax"] = []
    elif kind == "confidence_extra": response["confidence"] = 1
    else: response = []
    result = adapt_response(json.dumps(response), request_data)
    assert result.status == "schema_error"
    assert result.output is None
    assert all(issue.code.startswith("schema.") for issue in result.issues)
    if kind == "missing": assert result.issues[0].field == "seller_name"
    if kind == "numeric_id": assert result.issues[0].field == "invoice_number"


@pytest.mark.parametrize("kind,code", [("missing", "evidence.missing"), ("unknown", "evidence.unknown_id"),
    ("duplicate", "evidence.duplicate_id"), ("wrong_field", "evidence.value_mismatch"),
    ("noncontiguous", "evidence.noncontiguous")])
def test_bad_evidence_blocks_field_but_keeps_candidate_diagnostic(request_data, response, kind, code):
    response["evidence"]["invoice_number"] = {
        "missing": [], "unknown": ["invented"], "duplicate": ["s1", "s1"],
        "wrong_field": ["s2"], "noncontiguous": ["s1", "s2"],
    }[kind]
    result = adapt_response(json.dumps(response), request_data)
    assert result.status == "processed"
    assert result.candidate_validation.normalized_values.invoice_number == "HD-0000123"
    assert result.accepted_validation.normalized_values.invoice_number is None
    assert not result.accepted_validation.valid
    assert result.output.field_metadata["invoice_number"].evidence == []
    assert ("invoice_number", code) in {(i.field, i.code) for i in result.issues}


def test_explicit_uncertainty_is_never_accepted(request_data, response):
    response["uncertain_fields"] = ["invoice_number"]
    result = adapt_response(json.dumps(response), request_data)
    assert result.output.raw_values["invoice_number"] == "HD-0000123"
    assert result.accepted_validation.normalized_values.invoice_number is None
    assert result.output.field_metadata["invoice_number"].confidence is None


def test_annotated_blank_is_not_missing_ground_truth(dataset, provider):
    report = run(dataset, provider)
    blank = next(r for r in report["records"] if r["sample_id"] == "blank")
    assert blank["candidate_validation"]["valid"] is False  # Final invoice still requires values.
    assert all(cell["normalized"] is True for cell in blank["metrics"].values())
    assert all(cell["annotated"] for cell in blank["metrics"].values())
    assert report["fixture_diagnostics"]["overall"]["all_null_correct_negative"] == 3


@pytest.mark.parametrize("raw_amount", ["125,000", -1, "not a number"])
def test_normalization_business_errors_do_not_become_correct_values(request_data, response, dataset, raw_amount):
    response["raw_values"]["total_amount"] = raw_amount
    result = adapt_response(json.dumps(response), request_data)
    metrics = field_metrics(result, dataset.cases[0].ground_truth)
    assert result.status == "processed"
    assert result.candidate_validation.normalized_values.total_amount is None
    assert metrics["total_amount"]["normalized"] is False
    assert any(i.field == "total_amount" for i in result.candidate_validation.errors)


def test_exact_and_normalized_match_keep_types_and_zero_prefix(request_data, response, dataset):
    response["raw_values"]["invoice_number"] = "  HD-0000123  "
    result = adapt_response(json.dumps(response), request_data)
    metrics = field_metrics(result, dataset.cases[0].ground_truth)
    assert metrics["invoice_number"]["exact"] is False and metrics["invoice_number"]["normalized"] is True
    assert metrics["invoice_date"]["exact"] is False and metrics["invoice_date"]["normalized"] is True
    assert metrics["total_amount"]["exact"] is False and metrics["total_amount"]["normalized"] is True
    response["raw_values"]["invoice_number"] = "HD-123"
    assert field_metrics(adapt_response(json.dumps(response), request_data), dataset.cases[0].ground_truth)["invoice_number"]["normalized"] is False


def test_invalid_prediction_nulled_by_validation_is_not_correct_abstention(request_data, response):
    response["raw_values"]["currency"] = "USD"
    result = adapt_response(json.dumps(response), request_data)
    truth = InvoiceValues(**dict.fromkeys(FIELD_NAMES))
    cell = field_metrics(result, truth)["currency"]
    assert cell["normalized"] is False
    assert cell["predicted_non_null"] is True


@pytest.mark.parametrize("mode", ["image-only", "ocr-text-only", "image+ocr"])
def test_mode_contract_enforces_presence_and_identity(dataset, mode):
    case = dataset.cases[0]
    request = BenchmarkRequest(sample_id=case.image.document_id, mode=mode,
        image=None if mode == "ocr-text-only" else case.image, ocr=None if mode == "image-only" else case.ocr,
        source_locale="vi-VN")
    assert request.fingerprint() == request.model_copy(deep=True).fingerprint()
    broken = request.model_dump()
    broken["ocr" if mode == "image-only" else "image"] = case.ocr if mode == "image-only" else (None if mode == "image+ocr" else case.image)
    with pytest.raises(ValidationError): BenchmarkRequest.model_validate(broken)


@pytest.mark.parametrize("kind", ["hash", "span", "duplicate", "fake_box", "fake_score"])
def test_bad_source_context_is_rejected(request_data, kind):
    data = request_data.ocr.model_dump()
    if kind == "hash": data["text_sha256"] = "wrong"
    elif kind == "span": data["spans"][0]["end"] = len(data["text"])+1
    elif kind == "duplicate": data["spans"].append(data["spans"][0])
    elif kind == "fake_box": data["spans"][0]["bbox"] = dict(x0=1,y0=1,x1=2,y1=2)
    else: data["spans"][0]["ocr_native_score"] = 99.0
    with pytest.raises(ValidationError): OCRContext.model_validate(data)


def test_simulated_source_score_and_box_are_copied_not_reinterpreted(request_data, response):
    # Test-only stand-in for a trusted OCR snapshot; not a measured observation.
    data = request_data.ocr.model_dump()
    data["origin"] = "tesseract_snapshot"
    data["spans"][0].update(ocr_native_score=88.5, bbox=dict(x0=1,y0=2,x1=3,y1=4))
    request = request_data.model_copy(update={"ocr": OCRContext.model_validate(data)})
    result = adapt_response(json.dumps(response), request)
    assert result.output.field_metadata["invoice_number"].evidence[0].bbox.model_dump() == dict(x0=1,y0=2,x1=3,y1=4)
    assert request.ocr.spans[0].ocr_native_score == 88.5
    assert result.output.field_metadata["invoice_number"].confidence is None


def test_same_fixture_gives_identical_report_and_honest_metadata(dataset, provider):
    first, second = run(dataset, provider), run(dataset, provider)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert first["result_kind"] == "fixture_simulation"
    assert first["is_model_quality_benchmark"] is first["inference_performed"] is False
    meta = first["metadata"]
    assert meta["identity"]["model_id"] is meta["identity"]["model_revision"] is meta["code_revision"] is None
    assert meta["schema_version"] == "1.0.0" and meta["dataset_version"] == "ocr-smoke-1"
    assert all(meta[key] for key in ("runner_version", "parser_version", "metrics_version", "manifest_sha256", "labels_sha256", "ocr_sources_sha256"))
    assert all(r["elapsed_seconds"] is None for r in first["records"])


def test_hand_calculated_fixture_counts(dataset, provider):
    report = run(dataset, provider)
    summary = report["fixture_diagnostics"]["overall"]
    assert summary["scheduled_runs"] == 9 and summary["processed_runs"] == 9
    assert summary["positive_runs"] == 6 and summary["all_fields_normalized_correct_positive"] == 6
    assert summary["evidence_error_runs"] == 2  # Positive image-only runs have no OCR evidence context.
    amount = summary["fields"]["total_amount"]
    assert (amount["non_null_total"], amount["exact_correct"], amount["normalized_correct"], amount["accepted_correct"]) == (6, 0, 6, 4)
    assert amount["null_total"] == amount["null_normalized_correct"] == 3
    assert amount["null_false_positives"] == 0
    assert amount["evidence_supported_candidate_runs"] == 4
    assert amount["evidence_coverage_on_candidates"] == pytest.approx(4/6)
    assert summary["non_null_field_slots"] == summary["normalized_correct_field_slots"] == 30


def test_no_labels_means_na_not_perfect_null_matches(provider):
    dataset = load_dataset(ROOT / "data/ocr-smoke/manifest.json", DATA / "ocr-inputs.json")
    summary = run(dataset, provider)["fixture_diagnostics"]["overall"]
    assert summary["annotated_runs"] == 0 and summary["unannotated_runs"] == 9
    assert all(cell["normalized_rate"] is None and cell["null_pass_rate_planned"] is None for cell in summary["fields"].values())
    assert summarize([])["fields"]["currency"]["normalized_rate"] is None


def test_failure_does_not_disappear_from_denominator_or_count_as_negative_success(dataset, provider):
    class Broken:
        identity = provider.identity
        def respond(self, request): return "not JSON"
    report = run(dataset, Broken())
    summary = report["fixture_diagnostics"]["overall"]
    assert summary["parse_error_runs"] == summary["scheduled_runs"] == 9
    assert summary["all_null_correct_negative"] == 0
    for cell in summary["fields"].values():
        assert cell["non_null_total"] == 6 and cell["normalized_correct"] == 0
        assert cell["null_unknown"] == 3 and cell["null_false_positive_rate_observed"] is None


@pytest.mark.parametrize("error", [ProviderError("provider_timeout"), RuntimeError("secret=DO_NOT_EXPOSE")])
def test_provider_errors_are_sanitized(dataset, provider, error):
    class Broken:
        identity = provider.identity
        def respond(self, request): raise error
    report = run(dataset, Broken())
    assert all(r["status"] == "provider_error" for r in report["records"])
    assert "DO_NOT_EXPOSE" not in json.dumps(report)
    assert report["fixture_diagnostics"]["overall"]["fields"]["currency"]["non_null_total"] == 6


def test_provider_only_sees_mode_projected_inputs_and_cannot_mutate_source(dataset, provider):
    before = dataset.cases[0].ocr.model_dump()
    seen = []
    class Spy:
        identity = provider.identity
        def respond(self, request):
            assert set(type(request).model_fields) == {"sample_id", "mode", "image", "ocr", "source_locale"}
            assert not hasattr(request, "ground_truth") and not hasattr(request, "expected_text")
            seen.append((request.mode, request.image is not None, request.ocr is not None))
            raw = provider.respond(request)
            if request.ocr: request.ocr.spans.clear()
            return raw
    report = run(dataset, Spy())
    assert dataset.cases[0].ocr.model_dump() == before
    assert ("image-only", True, False) in seen and ("ocr-text-only", False, True) in seen and ("image+ocr", True, True) in seen
    assert report["fixture_diagnostics"]["overall"]["fields"]["currency"]["accepted_correct"] == 4


def test_real_provider_is_rejected_before_respond(dataset):
    class Forbidden:
        identity = BenchmarkIdentity(provider=ProviderIdentity(name="real",implementation_version="1",config_version="1",mode="real"), model_id="not-loaded",model_revision=None)
        def respond(self, request): raise AssertionError("Inference must not run")
    with pytest.raises(ValueError, match="fixture responses only"):
        run(dataset, Forbidden())


def test_actual_optional_timing_is_only_fixture_time(dataset, provider):
    report = run(dataset, provider, measure=True)
    assert report["timing_scope"] == "fixture_response_parse_evaluate_not_model_latency"
    assert all(r["elapsed_seconds"] >= 0 for r in report["records"])


def test_missing_ocr_context_is_counted_as_input_error(dataset, provider):
    changed = replace(dataset, cases=(replace(dataset.cases[0], ocr=None),))
    summary = run(changed, provider)["fixture_diagnostics"]["overall"]
    assert summary["scheduled_runs"] == 3 and summary["processed_runs"] == 1
    assert summary["fields"]["currency"]["non_null_total"] == 3
    assert summary["error_runs_by_code"]["input.invalid_request"] == 2


def test_fixture_cli_is_deterministic_json_without_inference():
    args = [sys.executable, "-m", "app.benchmark"]
    first = subprocess.run(args, cwd=ROOT / "backend", capture_output=True, check=True, timeout=15)
    second = subprocess.run(args, cwd=ROOT / "backend", capture_output=True, check=True, timeout=15)
    assert first.stdout == second.stdout and first.stderr == b""
    report = json.loads(first.stdout)
    assert report["result_kind"] == "fixture_simulation" and not report["inference_performed"]


def test_bad_manifest_hash_is_not_ignored(tmp_path):
    # Point to a tiny local synthetic file so no image/model is downloaded or decoded.
    (tmp_path / "image.png").write_bytes(b"synthetic")
    manifest={"version":"bad", "images":[{"id":"bad", "file":"image.png", "media_type":"image/png", "sha256":"wrong"}]}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="hash mismatch"):
        load_dataset(tmp_path / "manifest.json", DATA / "ocr-inputs.json")


def test_derived_currency_still_needs_its_own_evidence(request_data, response):
    response["raw_values"].update(total_amount="125000 VND", currency=None)
    response["evidence"]["currency"] = []
    result = adapt_response(json.dumps(response), request_data)
    assert result.candidate_validation.normalized_values.currency == "VND"
    assert result.accepted_validation.normalized_values.currency is None
    assert ("currency", "evidence.missing") in {(i.field, i.code) for i in result.issues}
    truth = InvoiceValues(**dict.fromkeys(FIELD_NAMES))
    assert field_metrics(result, truth)["currency"]["predicted_non_null"] is True


@pytest.mark.parametrize("raw", ['{"a":1e999}', '{"a":"\\ud800"}', '\ud800'])
def test_invalid_unicode_or_overflow_number_is_a_parse_error(request_data, raw):
    assert adapt_response(raw, request_data).status == "parse_error"


def test_zero_is_not_null_or_false(request_data, response, dataset):
    truth = dataset.cases[0].ground_truth.model_copy(update={"total_amount": 0})
    response["raw_values"]["total_amount"] = 0
    metrics = field_metrics(adapt_response(json.dumps(response), request_data), truth)
    assert metrics["total_amount"]["normalized"] is True
    assert metrics["total_amount"]["truth_is_null"] is False


def test_unicode_source_offsets_use_codepoints_and_source_hash_must_match(request_data):
    text = request_data.ocr.text
    span = request_data.ocr.spans[2]
    assert text[span.start:span.end].startswith('C\u1eeda')
    broken = request_data.model_dump()
    broken["ocr"]["input_sha256"] = "0" * 64
    with pytest.raises(ValidationError): BenchmarkRequest.model_validate(broken)


def test_partial_annotations_are_excluded_from_denominators_only_when_unannotated(dataset, provider):
    cases = list(dataset.cases)
    cases[1] = replace(cases[1], ground_truth=None)
    summary = run(replace(dataset, cases=tuple(cases)), provider)["fixture_diagnostics"]["overall"]
    assert summary["annotated_runs"] == 6 and summary["unannotated_runs"] == 3
    assert summary["fields"]["invoice_number"]["non_null_total"] == 3


def test_schema_failures_count_in_planned_denominator(dataset, provider):
    class Broken:
        identity = provider.identity
        def respond(self, request): return '{}'
    summary = run(dataset, Broken())["fixture_diagnostics"]["overall"]
    assert summary["schema_error_runs"] == 9
    assert summary["fields"]["total_amount"]["non_null_total"] == 6
    assert summary["fields"]["total_amount"]["normalized_correct"] == 0
