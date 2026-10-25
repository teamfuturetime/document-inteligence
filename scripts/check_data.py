from docintel.config import ROOT
from docintel.domain.models import FixtureManifest
from docintel.evaluation.manifest import validate_manifest
from docintel.evaluation.product import read_manifest

manifest = FixtureManifest.model_validate_json(
    (ROOT / "data/manifests/fixtures.json").read_text(encoding="utf-8")
)
annotations = validate_manifest(ROOT, manifest)
print(f"Manifest PASS: {len(annotations)} samples; purpose={manifest.purpose}")
product = read_manifest(ROOT, ROOT / "data/manifests/product.json")
print(f"Product manifest PASS: {len(product['samples'])} independent parent samples")
