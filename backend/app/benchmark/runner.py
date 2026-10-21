"""Deterministic fixture runner. Inference providers are deliberately not enabled."""

from time import perf_counter

from pydantic import ValidationError

from app.benchmark.contracts import BenchmarkDataset, BenchmarkProvider, BenchmarkRequest, MODES, digest, json_digest
from app.benchmark.metrics import METRICS_VERSION, field_metrics, summarize
from app.benchmark.parser import PARSER_VERSION, adapt_response
from app.providers.contracts import ProviderError
from app.services.normalization import NORMALIZATION_VERSION

RUNNER_VERSION = "offline-invoice-benchmark-1"


def run_benchmark(
    dataset: BenchmarkDataset, provider: BenchmarkProvider, *, fixture_sha256: str,
    modes=MODES, measure: bool = False, code_revision: str | None = None,
) -> dict:
    identity = provider.identity
    if identity.provider.mode != "fake" or identity.model_id is not None or identity.model_revision is not None:
        raise ValueError("S3.3.2a enables fixture responses only; no model inference")
    if not modes or len(set(modes)) != len(modes) or any(mode not in MODES for mode in modes):
        raise ValueError("Expected distinct benchmark modes")
    metadata = {
        "runner_version": RUNNER_VERSION, "parser_version": PARSER_VERSION, "metrics_version": METRICS_VERSION,
        "document_type": "sales_invoice", "schema_version": "1.0.0", "normalization_version": NORMALIZATION_VERSION,
        "identity": identity.model_dump(), "code_revision": code_revision,
        "dataset_version": dataset.version, "manifest_sha256": dataset.manifest_sha256,
        "labels_version": dataset.labels_version, "labels_sha256": dataset.labels_sha256,
        "ocr_sources_sha256": dataset.ocr_sources_sha256, "fixture_sha256": fixture_sha256,
        "modes": list(modes), "measure": measure,
    }
    records = []
    for case in dataset.cases:
        for mode in modes:
            started = perf_counter() if measure else None
            result = None
            request = None
            raw = None
            issues = []
            status = "input_error"
            try:
                request = BenchmarkRequest(
                    sample_id=case.image.document_id, mode=mode,
                    image=case.image.model_copy(deep=True) if mode != "ocr-text-only" else None,
                    ocr=None if mode == "image-only" or case.ocr is None else case.ocr.model_copy(deep=True),
                    source_locale=case.source_locale,
                )
            except ValidationError:
                issues.append({"field": None, "code": "input.invalid_request", "message": "Invalid mode/source input"})
            else:
                try:
                    # Provider receives a detached request, without evaluator ground truth.
                    raw = provider.respond(request.model_copy(deep=True))
                except ProviderError as exc:
                    code = exc.code if exc.code in {"provider_timeout", "provider_failed", "provider_unavailable", "invalid_document"} else "provider_failed"
                    status = "provider_error"
                    issues.append({"field": None, "code": code, "message": code})
                except Exception:
                    status = "provider_error"
                    issues.append({"field": None, "code": "provider_failed", "message": "Provider failed"})
                else:
                    result = adapt_response(raw, request)
                    status = result.status
                    issues.extend(issue.model_dump() for issue in result.issues)
                    if result.candidate_validation:
                        issues.extend(issue.model_dump() for issue in result.candidate_validation.errors)
                    if result.accepted_validation:
                        issues.extend(issue.model_dump() for issue in result.accepted_validation.errors)
            unique_issues = {}
            for issue in issues:
                unique_issues.setdefault((issue["field"], issue["code"]), issue)
            if isinstance(raw, str):
                try:
                    raw.encode("utf-8")
                except UnicodeError:
                    raw = None  # Not representable as a UTF-8 response; retain the parse error.
            record = {
                "sample_id": case.image.document_id, "mode": mode, "status": status,
                "input_sha256": digest(case.image.content),
                "request_sha256": None if request is None else request.fingerprint(),
                "ocr_context": None if request is None or request.ocr is None else request.ocr.model_dump(),
                "raw_response": raw if isinstance(raw, str) else None,
                "response_sha256": digest(raw.encode()) if isinstance(raw, str) else None,
                "issues": list(unique_issues.values()),
                "provider_output": None if result is None or result.output is None else result.output.model_dump(),
                "candidate_validation": None if result is None or result.candidate_validation is None else result.candidate_validation.model_dump(),
                "accepted_validation": None if result is None or result.accepted_validation is None else result.accepted_validation.model_dump(),
                "model_reported_scores": {} if result is None else result.model_reported_scores,
                "metrics": field_metrics(result, case.ground_truth),
                "elapsed_seconds": None if started is None else perf_counter()-started,
            }
            record["run_id"] = json_digest({"metadata": metadata, "sample_id": record["sample_id"],
                                            "mode": mode, "request": record["request_sha256"], "response": record["response_sha256"]})
            records.append(record)
    return {
        "result_kind": "fixture_simulation", "is_model_quality_benchmark": False, "inference_performed": False,
        "timing_scope": None if not measure else "fixture_response_parse_evaluate_not_model_latency",
        "metadata": metadata, "records": records,
        "fixture_diagnostics": {"overall": summarize(records),
                                "by_mode": {mode: summarize([r for r in records if r["mode"] == mode]) for mode in modes}},
    }
