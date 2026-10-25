import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from docintel.config import ROOT, Settings
from docintel.evaluation.product import evaluate, read_manifest, safe_file
from document_pipeline.config import PipelineConfig
from document_pipeline.service import DocumentPipeline


def main():
    parser = argparse.ArgumentParser(
        description="Real model benchmark; gold is only read by evaluator"
    )
    parser.add_argument(
        "--manifest", type=Path, default=ROOT / "data/manifests/product.json"
    )
    parser.add_argument(
        "--split", choices=("development", "validation", "test"), required=True
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="New run directory; never overwritten",
    )
    parser.add_argument("--config", type=Path)
    args = parser.parse_args()
    manifest = read_manifest(ROOT, args.manifest)
    samples = [
        sample for sample in manifest["samples"] if sample["split"] == args.split
    ]
    if not samples:
        parser.error("Selected split has no samples")
    settings = Settings()
    config = (
        PipelineConfig.model_validate_json(args.config.read_text(encoding="utf-8"))
        if args.config
        else PipelineConfig()
    )
    pipeline = DocumentPipeline(
        settings.tessdata_dir, settings.tesseract_executable, config
    )
    records, run_id = [], uuid4().hex
    args.output.mkdir(parents=True, exist_ok=False)
    for sample in samples:
        prediction = pipeline.run(
            safe_file(ROOT, sample["input_path"]).read_bytes(), sample["document_type"]
        )
        # Labels are not passed to the pipeline; read them only after its prediction.
        gold = json.loads(
            safe_file(ROOT, sample["annotation_path"]).read_text(encoding="utf-8")
        )
        records.append(
            {
                "sample_id": sample["sample_id"],
                "document_type": sample["document_type"],
                "quality_tags": sample["quality_tags"],
                "gold": gold,
                "prediction": prediction.model_dump(mode="json"),
            }
        )
    report = {
        **evaluate(records),
        "run_id": run_id,
        "generated_at": datetime.now(UTC).isoformat(),
        "split": args.split,
        "dataset_version": manifest["dataset_version"],
        "manifest_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
        "run_metadata": records[0]["prediction"]["metadata"],
        "limitations": [
            "Self-designed synthetic typed documents; not representative of real invoices",
            "Layouts are shared across splits; no claim of unseen-layout performance",
            "Root causes of automatic error records need human triage",
            "OS cache uncontrolled; one native OCR process per document",
        ],
        "by_document_type": {
            kind: evaluate(
                [record for record in records if record["document_type"] == kind]
            )
            for kind in {record["document_type"] for record in records}
        },
    }
    for name, value in (("report.json", report), ("predictions.json", records)):
        (args.output / name).write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    print(
        json.dumps(
            {
                "run_id": run_id,
                "samples": len(records),
                "split": args.split,
                "present_accuracy": report["micro"]["present_accuracy"],
            }
        )
    )


if __name__ == "__main__":
    main()
