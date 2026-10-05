from docintel.config import ROOT
from docintel.domain.models import FixtureManifest
from docintel.evaluation.manifest import validate_manifest

manifest = FixtureManifest.model_validate_json(
    (ROOT / "data/manifests/fixtures.json").read_text(encoding="utf-8")
)
annotations = validate_manifest(ROOT, manifest)
print(f"Manifest PASS: {len(annotations)} samples; purpose={manifest.purpose}")
