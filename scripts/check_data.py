from docintel.config import ROOT
from docintel.domain.models import FixtureManifest
from docintel.evaluation.data_audit import audit_product_manifest
from docintel.evaluation.manifest import validate_manifest

manifest = FixtureManifest.model_validate_json(
    (ROOT / "data/manifests/fixtures.json").read_text(encoding="utf-8")
)
annotations = validate_manifest(ROOT, manifest)
print(f"Manifest PASS: {len(annotations)} samples; purpose={manifest.purpose}")
product = audit_product_manifest(ROOT, ROOT / "data/manifests/product.json")
print(
    f"Product manifest/labels PASS: {product['samples']} samples; {product['parents']} parents"
)
print(
    f"Templates shared across splits (not unseen-layout): {product['templates_shared_across_splits']}"
)
