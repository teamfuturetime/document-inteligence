"""Print a fixture diagnostic report; does not download, infer, call APIs or write export files."""

import argparse
import json
from pathlib import Path
import sys

from app.benchmark.fixtures import FixtureResponseProvider, load_dataset
from app.benchmark.runner import run_benchmark


def main() -> int:
    root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description="OFFLINE FIXTURE SIMULATION — NOT MODEL QUALITY")
    parser.add_argument("--manifest", type=Path, default=root / "data/ocr-smoke/manifest.json")
    parser.add_argument("--sources", type=Path, default=root / "data/benchmark-fixture/ocr-inputs.json")
    parser.add_argument("--responses", type=Path, default=root / "data/benchmark-fixture/responses.json")
    parser.add_argument("--labels", type=Path, default=root / "data/benchmark-fixture/labels.json")
    parser.add_argument("--without-labels", action="store_true")
    parser.add_argument("--measure", action="store_true", help="Measure fixture runner time, never VLM latency")
    parser.add_argument("--code-revision", default=None)
    args = parser.parse_args()
    try:
        dataset = load_dataset(args.manifest, args.sources, None if args.without_labels else args.labels)
        provider = FixtureResponseProvider(args.responses)
        report = run_benchmark(dataset, provider, fixture_sha256=provider.source_sha256,
                               measure=args.measure, code_revision=args.code_revision)
    except (OSError, ValueError, KeyError, TypeError):
        print("invalid_benchmark_fixture", file=sys.stderr)
        return 1
    sys.stdout.buffer.write((json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)+"\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
