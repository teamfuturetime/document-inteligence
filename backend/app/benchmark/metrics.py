"""Typed exact/normalized diagnostics; nulls and missing annotations stay separate."""

from app.benchmark.parser import AdaptedResponse
from app.schemas.invoice import InvoiceValues
from app.services.normalization import FIELD_NAMES

METRICS_VERSION = "invoice-benchmark-metrics-1"


def typed_equal(left, right) -> bool:
    return type(left) is type(right) and left == right


def field_metrics(result: AdaptedResponse | None, truth: InvoiceValues | None) -> dict:
    metrics = {}
    for field in FIELD_NAMES:
        if truth is None:
            metrics[field] = {"annotated": False, "truth_is_null": None, "exact": None,
                              "normalized": None, "accepted": None, "predicted_non_null": None}
            continue
        expected = truth.model_dump()[field]
        available = result is not None and result.output is not None
        raw = result.output.raw_values[field] if available else None
        predicted = None if not available else (
            (raw is not None and not (isinstance(raw, str) and not raw.strip()))
            or result.candidate_validation.normalized_values.model_dump()[field] is not None
        )

        def matches(validation):
            if not available or validation is None:
                return False
            value = validation.normalized_values.model_dump()[field]
            # Invalid data that was nulled by validation is not correct abstention.
            harmful = any(issue.field in (field, None) and issue.code != "business.required"
                          for issue in validation.errors)
            return not harmful and typed_equal(value, expected)

        metrics[field] = {
            "annotated": True, "truth_is_null": expected is None,
            "exact": available and typed_equal(raw, expected),
            "normalized": matches(None if result is None else result.candidate_validation),
            "accepted": matches(None if result is None else result.accepted_validation),
            "predicted_non_null": predicted,
        }
    return metrics


def summarize(records: list[dict]) -> dict:
    def ratio(correct, total):
        return None if total == 0 else correct / total

    fields = {}
    for field in FIELD_NAMES:
        cells = [record["metrics"][field] for record in records if record["metrics"][field]["annotated"]]
        present = [cell for cell in cells if not cell["truth_is_null"]]
        absent = [cell for cell in cells if cell["truth_is_null"]]
        known = [cell for cell in absent if cell["predicted_non_null"] is not None]
        candidates = [r for r in records if r["candidate_validation"] is not None
                      and r["candidate_validation"]["normalized_values"][field] is not None]
        supported = [r for r in candidates if r["provider_output"]["field_metadata"][field]["evidence"]]
        fields[field] = {
            "non_null_total": len(present),
            **{f"{name}_correct": sum(cell[name] is True for cell in present) for name in ("exact", "normalized", "accepted")},
            **{f"{name}_rate": ratio(sum(cell[name] is True for cell in present), len(present)) for name in ("exact", "normalized", "accepted")},
            "null_total": len(absent), "null_unknown": len(absent)-len(known),
            "null_normalized_correct": sum(cell["normalized"] is True for cell in absent),
            "null_false_positives": sum(cell["predicted_non_null"] is True for cell in known),
            "null_false_positive_rate_observed": ratio(sum(cell["predicted_non_null"] is True for cell in known), len(known)),
            "null_pass_rate_planned": ratio(sum(cell["normalized"] is True for cell in absent), len(absent)),
            "candidate_runs": len(candidates), "evidence_supported_candidate_runs": len(supported),
            "evidence_coverage_on_candidates": ratio(len(supported), len(candidates)),
            "evidence_error_runs": sum(any(i["field"] == field and i["code"].startswith("evidence.")
                                            for i in r["issues"]) for r in records),
        }
    errors = {}
    for record in records:
        # A code counts at most once per record, even if several fields fail.
        for code in {issue["code"] for issue in record["issues"]}:
            errors[code] = errors.get(code, 0) + 1
    annotated = [r for r in records if all(cell["annotated"] for cell in r["metrics"].values())]
    positives = [r for r in annotated if all(not cell["truth_is_null"] for cell in r["metrics"].values())]
    negatives = [r for r in annotated if all(cell["truth_is_null"] for cell in r["metrics"].values())]
    return {
        "scheduled_runs": len(records), "annotated_runs": len(annotated), "unannotated_runs": len(records)-len(annotated),
        "processed_runs": sum(r["status"] == "processed" for r in records),
        "parse_error_runs": sum(r["status"] == "parse_error" for r in records),
        "schema_error_runs": sum(r["status"] == "schema_error" for r in records),
        "evidence_error_runs": sum(any(i["code"].startswith("evidence.") for i in r["issues"]) for r in records),
        "all_fields_normalized_correct_positive": sum(all(c["normalized"] is True for c in r["metrics"].values()) for r in positives),
        "positive_runs": len(positives),
        "all_null_correct_negative": sum(all(c["normalized"] is True for c in r["metrics"].values()) for r in negatives),
        "negative_runs": len(negatives), "fields": fields, "error_runs_by_code": dict(sorted(errors.items())),
        "non_null_field_slots": sum(cell["non_null_total"] for cell in fields.values()),
        "normalized_correct_field_slots": sum(cell["normalized_correct"] for cell in fields.values()),
    }
