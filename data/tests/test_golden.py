from collections import Counter
import hashlib
import json
from pathlib import Path

from document_contracts.models import InvoiceValues

ROOT = Path(__file__).resolve().parents[1] / "golden"


def test_frozen_golden_identity_splits_hashes_and_ground_truth():
    manifest = json.loads((ROOT / "manifest.json").read_text())
    rows = manifest["documents"]
    assert manifest["seed"] == 20261015
    assert len(rows) == len({row["id"] for row in rows}) == len({row["sha256"] for row in rows}) == 30
    assert Counter(row["split"] for row in rows) == {"dev": 18, "test": 12}
    assert {row["layout"] for row in rows} == {"labels-1", "labels-2", "labels-3"}
    assert "pending" in manifest["ground_truth_review"]
    for row in rows:
        for key, hash_key in [("file", "sha256"), ("ground_truth", "ground_truth_sha256")]:
            assert hashlib.sha256((ROOT / row[key]).read_bytes()).hexdigest() == row[hash_key]
        truth = InvoiceValues.model_validate_json((ROOT / row["ground_truth"]).read_bytes())
        assert (truth.currency is None) == (row["condition"] == "missing-currency")
