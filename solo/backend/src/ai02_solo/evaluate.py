"""Field metrics and hash-verified evaluation using exactly the HTTP pipeline."""

import argparse
from collections import defaultdict
from dataclasses import replace
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
import subprocess

from .contracts import LABELS, folded, validate_values
from .ocr import DocumentError
from .pipeline import run, source_hash
from .settings import ROOT, Settings

TAXONOMY = ["input_quality", "preprocessing", "ocr_text", "field_mapping", "normalization", "validation", "unsupported_layout", "model_generation", "unverified"]


def metric(pairs):
    tp = fp = fn = exact = null_pairs = support = 0
    for expected, predicted in pairs:
        exact += expected == predicted
        null_pairs += expected is None and predicted is None
        support += expected is not None
        tp += expected is not None and predicted == expected
        fp += predicted is not None and predicted != expected
        fn += expected is not None and predicted != expected
    ratio = lambda numerator, denominator: numerator / denominator if denominator else None
    return {"count": len(pairs), "support": support, "exact_match": ratio(exact, len(pairs)), "null_pairs": null_pairs,
        "tp": tp, "fp": fp, "fn": fn, "precision": ratio(tp, tp + fp), "recall": ratio(tp, tp + fn),
        "f1": ratio(2 * tp, 2 * tp + fp + fn)}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load_dataset(directory):
    raw = (directory / "manifest.json").read_bytes()
    manifest = json.loads(raw)
    if manifest["schema_version"] != "solo-1.0":
        raise ValueError("Dataset schema version differs")
    seen_ids, seen_paths, seen_hashes, loaded = set(), set(), set(), []
    for item in manifest["documents"]:
        if item["id"] in seen_ids or item["kind"] not in LABELS or item["split"] not in {"dev", "test"}:
            raise ValueError("Invalid ID/kind/split")
        seen_ids.add(item["id"])
        if item["sha256"] in seen_hashes:
            raise ValueError("Duplicate document bytes across dataset records")
        seen_hashes.add(item["sha256"])
        content = {}
        for key, hash_key in [("file", "sha256"), ("truth", "truth_sha256")]:
            relative = Path(item[key])
            path = (directory / relative).resolve()
            if relative.is_absolute() or not path.is_relative_to(directory.resolve()) or path in seen_paths:
                raise ValueError("Unsafe or duplicate dataset path")
            seen_paths.add(path)
            data = path.read_bytes()
            if digest(data) != item[hash_key]:
                raise ValueError("Dataset integrity check failed")
            content[key] = data
        truth = json.loads(content["truth"])
        validated = validate_values(item["kind"], truth)
        if validated["values"] != truth or any(truth[key] is not None for key in validated["errors"]):
            raise ValueError("Ground truth must contain canonical valid values or explicit nulls")
        loaded.append((item, content["file"], truth))
    if not loaded:
        raise ValueError("Empty dataset")
    return manifest, digest(raw), loaded


def evaluate(directory, split, mode, settings):
    manifest, manifest_sha, loaded = load_dataset(directory)
    if mode != "rules" and not settings.vlm_model:
        raise ValueError("VLM is not configured; no model quality report can be produced")
    all_pairs, slices, records, mismatches, errors = defaultdict(list), defaultdict(list), [], [], []
    provenance = None
    for item, data, truth in loaded:
        if split != "all" and item["split"] != split:
            continue
        try:
            result = run(data, item["kind"], mode, settings)
            predicted = {key: result.fields[key].value for key in truth}
            if provenance is not None and provenance != result.provenance:
                # Request hash includes the image/context; compare stable deployment/config only.
                previous = json.loads(json.dumps(provenance))
                current = json.loads(json.dumps(result.provenance))
                previous.get("vlm", {}).pop("request_sha256", None)
                current.get("vlm", {}).pop("request_sha256", None)
                if previous != current:
                    raise ValueError("Model/config changed within one evaluation run")
            provenance = result.provenance
        except DocumentError as exc:
            errors.append({"id": item["id"], "code": exc.code})
            predicted = {key: None for key in truth}
        record = {"id": item["id"], "kind": item["kind"], "split": item["split"], "layout": item["layout"],
            "condition": item["condition"], "expected": truth, "predicted": predicted}
        records.append(record)
        for key, expected in truth.items():
            pair = (expected, predicted[key])
            all_pairs[f"{item['kind']}.{key}"].append(pair)
            for dimension in ["kind", "split", "layout", "condition"]:
                slices[f"{dimension}:{item[dimension]}"].append(pair)
            if expected != predicted[key]:
                symptom = "missing_prediction" if predicted[key] is None else ("unexpected_prediction" if expected is None else "wrong_value")
                if isinstance(expected, str) and isinstance(predicted[key], str) and folded(expected) == folded(predicted[key]):
                    symptom = "diacritic_or_case_difference"
                mismatches.append({"id": item["id"], "field": key, "expected": expected, "predicted": predicted[key],
                    "symptom": symptom,
                    "cause": "unverified"})
    if not records:
        raise ValueError("Selected split has no documents")
    fields = {key: metric(pairs) for key, pairs in sorted(all_pairs.items())}
    try:
        git_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())
    except (OSError, subprocess.SubprocessError):
        git_sha, dirty = "unavailable", None
    # Per-document request fingerprints remain in API results; report stable model/config.
    if provenance:
        provenance.get("vlm", {}).pop("request_sha256", None)
    return {"report_version": "solo-eval-1", "dataset_version": manifest["version"], "manifest_sha256": manifest_sha,
        "split": split, "mode": mode, "ocr_provider": settings.ocr_provider, "documents": len(records), "macro_exact_match": sum(m["exact_match"] for m in fields.values()) / len(fields),
        "fields": fields, "micro": metric([pair for pairs in all_pairs.values() for pair in pairs]),
        "slices": {key: metric(pairs) for key, pairs in sorted(slices.items())}, "execution_errors": errors,
        "mismatches": mismatches, "records": records, "taxonomy": TAXONOMY,
        "provenance": {"pipeline": provenance, "source_sha256": source_hash(), "git_sha": git_sha,
            "git_dirty": dirty, "python": platform.python_version(), "platform": platform.platform(),
            "dependencies": {name: version(name) for name in ["pillow", "pymupdf", "pydantic", "fastapi"]},
            "lock_sha256": digest((ROOT / "uv.lock").read_bytes()), "deadline_seconds": settings.deadline}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=ROOT / "data/golden-v1")
    parser.add_argument("--split", choices=["dev", "test", "all"], default="test")
    parser.add_argument("--mode", choices=["rules", "vlm", "hybrid"], default="rules")
    parser.add_argument("--ocr-provider", choices=["tesseract", "ocrspace"], default=None)
    parser.add_argument("--output", type=Path, default=ROOT / "evaluation/reports/test-rules.json")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--min-exact", type=float, default=.85)
    args = parser.parse_args()
    try:
        settings = Settings.from_env()
        if args.ocr_provider:
            settings = replace(settings, ocr_provider=args.ocr_provider)
        report = evaluate(args.dataset, args.split, args.mode, settings)
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(2, f"Evaluation failed: {exc}\n")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ["mode", "ocr_provider", "split", "documents", "macro_exact_match", "execution_errors"]}))
    if args.check and (report["execution_errors"] or report["macro_exact_match"] < args.min_exact):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
