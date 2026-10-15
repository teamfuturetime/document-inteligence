"""Run exactly the HTTP pipeline on a hash-verified frozen synthetic dataset."""

import argparse
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
import subprocess

from document_evaluation.dataset import load_dataset
from document_evaluation.metrics import FIELDS, canonical, field_metrics
from document_pipeline.runner import PipelineError, run_document


def code_identity():
    root = Path(__file__).resolve().parents[3]
    digest = hashlib.sha256()
    for package in ("pipeline", "schemas", "evaluation"):
        for path in sorted((root / package / "src").rglob("*")):
            if path.suffix in {".py", ".json"}:
                digest.update(str(path.relative_to(root)).encode() + b"\0" + path.read_bytes())
    digest.update((root / "uv.lock").read_bytes())
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=False)
    dirty = subprocess.run(["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True, check=False)
    return {"git_sha": sha.stdout.strip() if sha.returncode == 0 else None,
            "git_dirty": bool(dirty.stdout), "source_sha256": digest.hexdigest(),
            "python": platform.python_version(), "platform": platform.platform(),
            "dependencies": {name: version(name) for name in ("Pillow", "PyMuPDF", "pydantic")}}


def evaluate(manifest: Path, tessdata_dir: Path, split="test"):
    dataset, manifest_hash, rows = load_dataset(manifest, split)
    if not rows:
        raise ValueError("Selected split is empty")
    pairs, records = [], []
    for item, data, truth in rows:
        expected = truth.model_dump()
        record = {"id": item["id"], "split": item["split"], "layout": item["layout"],
                  "condition": item["condition"], "expected": expected}
        try:
            run = run_document(data, tessdata_dir, item["id"])
            if run.result.mode != "real":
                raise ValueError("Evaluation refuses mock output")
            predicted = {field: getattr(run.result.fields, field).value for field in FIELDS}
            record.update(prediction=run.result.model_dump(), ocr=run.ocr.model_dump(), metadata=run.metadata)
        except PipelineError as exc:
            predicted = dict.fromkeys(FIELDS)
            record["execution_error"] = exc.code
        record["mismatches"] = [
            {"field": field, "expected": expected[field], "predicted": predicted[field],
             "symptom": "missing" if predicted[field] is None else "unexpected" if expected[field] is None else "wrong_value",
             "cause": "unverified"}
            for field in FIELDS if canonical(predicted[field]) != canonical(expected[field])
        ]
        pairs.append((predicted, expected))
        records.append(record)
    metrics = field_metrics(pairs)
    slices = {}
    for dimension in ("layout", "condition", "split"):
        slices[dimension] = {label: field_metrics([pair for pair, record in zip(pairs, records)
                                                  if record[dimension] == label])
                             for label in sorted({record[dimension] for record in records})}
    score = metrics["macro"]["exact_match"]
    return {"report_version": "1.0.0", "dataset_version": dataset["dataset_version"],
            "manifest_sha256": manifest_hash, "split": split, "documents": len(rows),
            "ground_truth_review": dataset["ground_truth_review"], "code": code_identity(),
            "metrics": metrics, "slices": slices, "records": records,
            "execution_errors": sum("execution_error" in record for record in records),
            "target": {"macro_exact_match": .85, "met": score is not None and score >= .85}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("data/golden/manifest.json"))
    parser.add_argument("--tessdata-dir", type=Path, required=True)
    parser.add_argument("--split", choices=["dev", "test", "all"], default="test")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check", action="store_true", help="Fail when target .85 is unmet")
    args = parser.parse_args()
    try:
        if args.output.resolve().is_relative_to(args.manifest.parent.resolve()):
            raise ValueError("Keep evaluation output outside the frozen dataset")
        report = evaluate(args.manifest, args.tessdata_dir, args.split)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"documents": report["documents"], "macro": report["metrics"]["macro"],
                          "execution_errors": report["execution_errors"], "target": report["target"]}))
        if report["execution_errors"] or args.check and not report["target"]["met"]:
            raise SystemExit(2)
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(1, f"evaluation_error: {exc}\n")


if __name__ == "__main__":
    main()
