"""Profile heuristic abstention on cached validation predictions, never test labels."""

import argparse
import copy
import hashlib
import json
from pathlib import Path

from docintel.evaluation.product import evaluate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = json.loads((args.run_dir / "report.json").read_text(encoding="utf-8"))
    if report["split"] != "validation" or report["report_type"] != "model_benchmark":
        parser.error("Policy selection only accepts a validation model benchmark")
    source = (args.run_dir / "predictions.json").read_bytes()
    records = json.loads(source)
    if any(
        record["prediction"]["metadata"]["config"].get("minimum_field_ocr_score", 0)
        != 0
        for record in records
    ):
        parser.error("Use baseline predictions without score abstention")
    profiles = []
    for threshold in (0.0, 0.25, 0.5, 0.75):
        candidate = copy.deepcopy(records)
        for record in candidate:
            for field in record["prediction"]["fields"]:
                if field["ocr_score"] is not None and field["ocr_score"] < threshold:
                    field["raw_value"] = field["normalized_value"] = None
                    field["observation"] = "unknown"
        counts = evaluate(candidate)["micro"]
        profiles.append(
            {
                "threshold": threshold,
                "correct_present": counts["correct"],
                "present": counts["present"],
                "predicted_non_null": counts["predicted_non_null"],
                "incorrect_non_null": counts["fp"],
                "unreadable": counts["unreadable"],
                "unreadable_abstained": counts["unreadable_abstained"],
            }
        )
    eligible = [
        profile
        for profile in profiles
        if profile["unreadable"] > 0
        and profile["unreadable_abstained"] == profile["unreadable"]
        and profile["correct_present"] >= profiles[0]["correct_present"]
    ]
    result = {
        "report_type": "validation_policy_selection",
        "source_run_id": report["run_id"],
        "source_manifest_sha256": report["manifest_sha256"],
        "source_predictions_sha256": hashlib.sha256(source).hexdigest(),
        "profiles": profiles,
        "selected_threshold": eligible[0]["threshold"] if eligible else None,
        "selection_rule": "Smallest grid threshold rejecting unreadable without losing correct present",
        "limitations": "Tiny unreadable support; not calibration or general accuracy",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps(
            {
                "selected_threshold": result["selected_threshold"],
                "profiles": len(profiles),
            }
        )
    )


if __name__ == "__main__":
    main()
