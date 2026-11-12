"""Exact field metrics for both product schemas; never imported by inference."""

import hashlib
import json
from collections import Counter
from pathlib import Path

from docintel.domain.documents import DEFINITIONS

EVALUATION_VERSION = "product-exact-fields-1.0.0"


def safe_file(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError("Dataset path is outside root or missing")
    return path


def read_manifest(root: Path, path: Path) -> dict:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest["purpose"] != "model_benchmark":
        raise ValueError("A fixture manifest is not a model benchmark")
    ids, hashes, parents = set(), set(), {}
    for sample in manifest["samples"]:
        if sample["sample_id"] in ids:
            raise ValueError("Duplicate sample ID")
        ids.add(sample["sample_id"])
        previous = parents.setdefault(sample["parent_document_id"], sample["split"])
        if previous != sample["split"]:
            raise ValueError("Parent document overlaps splits")
        if sample["split"] not in {"development", "validation", "test"}:
            raise ValueError("Invalid split")
        if sample["document_type"] not in DEFINITIONS or sample["data_origin"] != "synthetic":
            raise ValueError("Unsupported dataset source/schema")
        for key in ("input", "annotation"):
            data = safe_file(root, sample[f"{key}_path"]).read_bytes()
            if hashlib.sha256(data).hexdigest() != sample[f"{key}_sha256"]:
                raise ValueError(f"{key} hash mismatch")
            if key == "input":
                if sample["input_sha256"] in hashes:
                    raise ValueError("Duplicate image bytes")
                hashes.add(sample["input_sha256"])
    return manifest


def ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def field_counts(pairs: list[tuple[dict, dict]]) -> dict:
    counts = Counter(
        {
            key: 0
            for key in (
                "present",
                "absent",
                "unreadable",
                "correct",
                "predicted_non_null",
                "tp",
                "fp",
                "fn",
                "extra_fill",
                "absent_abstained",
                "unreadable_abstained",
            )
        }
    )
    for gold, prediction in pairs:
        expected, actual, status = gold["value"], prediction["normalized_value"], gold["status"]
        if status not in ("present", "absent", "unreadable"):
            raise ValueError("Invalid gold status")
        if (status == "present") != (expected is not None):
            raise ValueError("Only visible present gold may contain a value")
        counts[status] += 1
        if status == "unreadable":
            counts["unreadable_abstained"] += actual is None
            continue
        counts["predicted_non_null"] += actual is not None
        if status == "absent":
            counts["extra_fill"] += actual is not None
            counts["fp"] += actual is not None
            counts["absent_abstained"] += actual is None
        elif actual is not None and type(expected) is type(actual) and expected == actual:
            counts["tp"] += 1
            counts["correct"] += 1
        else:
            counts["fn"] += 1
            counts["fp"] += actual is not None
    tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
    return {
        **counts,
        "present_accuracy": ratio(counts["correct"], counts["present"]),
        "precision": ratio(tp, tp + fp),
        "recall": ratio(tp, tp + fn),
        "f1": ratio(2 * tp, 2 * tp + fp + fn),
        "extra_fill_rate": ratio(counts["extra_fill"], counts["absent"]),
        "unreadable_abstention_rate": ratio(counts["unreadable_abstained"], counts["unreadable"]),
        "zero_denominator_policy": "null; support and denominators retained",
    }


def evaluate(records: list[dict]) -> dict:
    by_field, all_pairs, errors = {}, [], []
    eligible = exact = 0
    exclusions = Counter()
    buckets = {"below_0.5": [], "0.5_to_0.8": [], "at_least_0.8": []}
    for record in records:
        required = {field.field_id for field in DEFINITIONS[record["document_type"]]}
        gold = record["gold"]["fields"]
        predictions = {field["field_id"]: field for field in record["prediction"]["fields"]}
        if set(gold) != required or set(predictions) != required:
            raise ValueError("Gold/prediction fields must match selected schema")
        is_eligible = all(gold[key]["status"] == "present" for key in required)
        if is_eligible:
            eligible += 1
            exact += all(
                type(gold[key]["value"]) is type(predictions[key]["normalized_value"])
                and gold[key]["value"] == predictions[key]["normalized_value"]
                for key in required
            )
        else:
            exclusions["required_field_absent_or_unreadable"] += 1
        for key in sorted(required):
            pair = gold[key], predictions[key]
            by_field.setdefault(key, []).append(pair)
            all_pairs.append(pair)
            expected, actual = gold[key]["value"], predictions[key]["normalized_value"]
            score = predictions[key].get("ocr_score")
            correct = type(expected) is type(actual) and expected == actual
            if score is not None and gold[key]["status"] == "present":
                bucket = (
                    "below_0.5" if score < 0.5 else "0.5_to_0.8" if score < 0.8 else "at_least_0.8"
                )
                buckets[bucket].append(correct)
            if gold[key]["status"] != "unreadable" and not correct:
                errors.append(
                    {
                        "sample_id": record["sample_id"],
                        "field_id": key,
                        "expected": expected,
                        "predicted": actual,
                        "primary_cause": "UNTRIAGED",
                        "severity": "requires_review",
                        "status": "open",
                        "issue_reference": None,
                        "note": "Automatic symptom; root cause needs source/OCR review",
                    }
                )
    metrics = {field: field_counts(pairs) for field, pairs in by_field.items()}
    present_scores = [
        item["present_accuracy"]
        for item in metrics.values()
        if item["present_accuracy"] is not None
    ]
    return {
        "evaluation_version": EVALUATION_VERSION,
        "report_type": "model_benchmark",
        "prediction_source": "model",
        "documents": len(records),
        "fields": metrics,
        "micro": field_counts(all_pairs),
        "macro_present_accuracy": sum(present_scores) / len(present_scores)
        if present_scores
        else None,
        "document_exact_match": {
            "correct": exact,
            "support": eligible,
            "accuracy": ratio(exact, eligible),
            "exclusions": dict(exclusions),
        },
        "confidence_buckets": {
            key: {
                "support": len(values),
                "present_accuracy": ratio(sum(values), len(values)),
                "method": "heuristic minimum OCR evidence score; not calibrated",
            }
            for key, values in buckets.items()
        },
        "error_records": errors,
    }
