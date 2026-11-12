"""Replay selected platform's frozen native predictions; NOT new OCR inference."""

import hashlib
import json

from docintel.config import ROOT
from docintel.evaluation.product import evaluate, read_manifest


def main():
    run = ROOT / "evaluation/runs/2026-10-24-test-frozen"
    expected = json.loads((run / "report.json").read_text(encoding="utf-8"))
    records = json.loads((run / "predictions.json").read_text(encoding="utf-8"))
    manifest_path = ROOT / "data/manifests/product.json"
    manifest = read_manifest(ROOT, manifest_path)
    if (
        hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        != expected["manifest_sha256"]
    ):
        raise SystemExit(
            "Frozen regression dataset changed; review/version it explicitly"
        )
    samples = {
        item["sample_id"]: item
        for item in manifest["samples"]
        if item["split"] == "test"
    }
    if len(records) != len(samples) or {r["sample_id"] for r in records} != set(
        samples
    ):
        raise SystemExit("Frozen prediction membership drift")
    for record in records:
        sample = samples[record["sample_id"]]
        gold = json.loads(
            (ROOT / sample["annotation_path"]).read_text(encoding="utf-8")
        )
        if record["gold"] != gold:
            raise SystemExit("Frozen evaluator labels do not match checked dataset")
        if record["prediction"]["metadata"]["prediction_source"] != "model":
            raise SystemExit(
                "Frozen regression requires recorded native predictions, not fixtures"
            )
    actual = evaluate(records)
    for key, value in actual.items():
        if value != expected[key]:
            raise SystemExit(
                f"Evaluation regression in {key}; do not update gold to mask it"
            )
    print(
        json.dumps(
            {
                "status": "passed",
                "purpose": "evaluator_regression_on_frozen_native_predictions",
                "documents": len(records),
                "original_engine": expected["run_metadata"]["engine_version"],
                "original_source": expected["run_metadata"]["pipeline_source_sha256"],
                "new_inference": False,
                "micro": actual["micro"],
            }
        )
    )


if __name__ == "__main__":
    main()
