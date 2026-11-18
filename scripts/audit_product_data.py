"""Audit product labels/splits/hashes without reading predictions or changing data."""

import argparse
import json
from pathlib import Path

from docintel.config import ROOT
from docintel.evaluation.data_audit import audit_product_manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        help="New JSON file; existing output is never overwritten",
    )
    args = parser.parse_args()
    report = audit_product_manifest(ROOT, ROOT / "data/manifests/product.json")
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8", newline="\n") as output:
            output.write(serialized)
    else:
        print(serialized, end="")


if __name__ == "__main__":
    main()
