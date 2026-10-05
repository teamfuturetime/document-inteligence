import argparse
import json
import platform
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from docintel.config import ROOT
from docintel.domain.models import ExtractionRun, FixtureManifest
from docintel.domain.versioning import ComponentVersion, RunManifest
from docintel.evaluation.manifest import checksum, validate_manifest
from docintel.evaluation.metrics import evaluate


def write_json(path: Path, value: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Kiểm tra evaluator trên fixture; không benchmark AI"
    )
    parser.add_argument(
        "--output", type=Path, default=ROOT / "evaluation/reports/fixture-contract.json"
    )
    args = parser.parse_args()
    manifest_path = ROOT / "data/manifests/fixtures.json"
    prediction_path = ROOT / "data/fixtures/predictions.json"
    manifest = FixtureManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    gold = validate_manifest(ROOT, manifest)
    predictions = [
        ExtractionRun.model_validate(value)
        for value in json.loads(prediction_path.read_text(encoding="utf-8")).values()
    ]
    report = evaluate(gold, predictions, source="fixture")
    config_path = ROOT / "configs/foundation.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    now = datetime.now(UTC)
    run_id = f"fixture_check_{now.strftime('%Y%m%dT%H%M%SZ')}"
    git_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = bool(
        subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()
    )
    run_manifest = RunManifest(
        run_id=run_id,
        started_at=now,
        status="succeeded",
        report_type=report["report_type"],
        prediction_source="fixture",
        git_commit=git_commit,
        git_dirty=dirty,
        dataset_version=manifest.dataset_version,
        manifest_sha256=checksum(manifest_path),
        split="contract_fixture",
        ocr=ComponentVersion(
            component="fixture_ocr", package_version=None, model_revision=None, artifact_sha256=None
        ),
        extraction=ComponentVersion(
            component="fixture_extraction",
            package_version=None,
            model_revision=None,
            artifact_sha256=checksum(prediction_path),
        ),
        versions={key: str(value) for key, value in config.items() if key.endswith("version")},
        hashes={
            "config": checksum(config_path),
            "predictions": checksum(prediction_path),
            "evaluation_code": checksum(Path(__file__).with_name("metrics.py")),
            "normalization_code": checksum(ROOT / "backend/src/docintel/domain/normalization.py"),
        },
        resolved_config=config,
        runtime={
            "python": platform.python_version(),
            "backend_lock": "backend/uv.lock",
            "backend_lock_sha256": checksum(ROOT / "backend/uv.lock"),
        },
        hardware={"platform": platform.platform(), "machine": platform.machine()},
        seed=config["seed"],
        prediction_artifact="data/fixtures/predictions.json",
        report_artifact=args.output.resolve().relative_to(ROOT).as_posix(),
        reproducibility_limitations=["Không chạy OCR/model; seed chỉ thuộc generator fixture."],
    )
    report["run_id"] = run_id
    write_json(args.output, report)
    write_json(
        args.output.with_name(args.output.stem + "-run.json"), run_manifest.model_dump(mode="json")
    )
    print(f"Evaluator contract check PASS: {len(gold)} fixtures; report written.")


if __name__ == "__main__":
    main()
