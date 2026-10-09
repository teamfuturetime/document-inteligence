"""Run from repository root: python -m backend.export_schemas [--check]."""

import argparse
import json
from pathlib import Path

from document_contracts.models import CONTRACT_MODELS

ROOT = Path(__file__).resolve().parents[1]


def schema_text(name, model):
    schema = model.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = f"urn:ai02:1.0.0:{name}"
    return json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    directory = ROOT / "schemas" / "v1"
    if not args.check:
        directory.mkdir(parents=True, exist_ok=True)
    for name, model in CONTRACT_MODELS.items():
        path = directory / f"{name}.schema.json"
        expected = schema_text(name, model)
        if args.check:
            if not path.exists() or path.read_text() != expected:
                raise SystemExit(f"Schema drift: {path.relative_to(ROOT)}")
        else:
            path.write_text(expected)
    print(f"{'Checked' if args.check else 'Exported'} {len(CONTRACT_MODELS)} schemas")


if __name__ == "__main__":
    main()
