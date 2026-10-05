import argparse
import json

from docintel.api.app import create_app
from docintel.config import ROOT, Settings
from docintel.domain import models
from docintel.domain.versioning import RunManifest


def main():
    parser = argparse.ArgumentParser(
        description="Sinh contracts từ Pydantic/FastAPI hoặc kiểm tra drift"
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    config = Settings(_env_file=None, provider_mode="unconfigured")
    documents = {"openapi.json": create_app(config).openapi()}
    for name in (
        "Document",
        "OCRResult",
        "ExtractionRun",
        "DraftApplicationData",
        "FinalApplicationData",
        "ReviewRevision",
        "ReviewEvent",
        "ValidationIssue",
        "ExportArtifact",
        "GoldAnnotation",
        "FixtureManifest",
        "FixtureView",
    ):
        documents[name + ".schema.json"] = getattr(models, name).model_json_schema()
    documents["RunManifest.schema.json"] = RunManifest.model_json_schema()
    drift = []
    for name, document in documents.items():
        if name.endswith(".schema.json"):
            document["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        path = ROOT / "contracts/generated" / name
        expected = (
            json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        )
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != expected:
                drift.append(name)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(expected, encoding="utf-8")
    if drift:
        raise SystemExit("Contract drift: " + ", ".join(drift))
    print(f"Contracts {'CHECK PASS' if args.check else 'generated'}: {len(documents)}")


if __name__ == "__main__":
    main()
