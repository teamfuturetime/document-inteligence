import json
from pathlib import Path
import shutil

import pytest

from document_evaluation.dataset import load_dataset

MANIFEST = Path(__file__).resolve().parents[2] / "data/golden/manifest.json"


def test_frozen_dataset_is_hash_verified_unique_and_has_fixed_splits():
    manifest, digest, all_rows = load_dataset(MANIFEST, "all")
    assert len(all_rows) == 30 and len(digest) == 64
    assert len({row[0]["id"] for row in all_rows}) == 30
    assert len({row[0]["sha256"] for row in all_rows}) == 30
    assert len(load_dataset(MANIFEST, "dev")[2]) == 18
    assert len(load_dataset(MANIFEST, "test")[2]) == 12
    assert {row[0]["layout"] for row in all_rows} == {"labels-1", "labels-2", "labels-3"}
    assert {row[0]["condition"] for row in all_rows} == {"clean", "compression", "blur", "rotation", "missing-currency"}
    assert "pending" in manifest["ground_truth_review"]


@pytest.mark.parametrize("kind", ["escape", "hash", "duplicate"])
def test_invalid_manifest_is_rejected(tmp_path, kind):
    manifest = json.loads(MANIFEST.read_text())
    for item in manifest["documents"]:
        for key in ("file", "ground_truth"):
            shutil.copyfile(MANIFEST.parent / item[key], tmp_path / item[key])
    if kind == "escape":
        manifest["documents"][0]["file"] = "../outside.png"
    elif kind == "hash":
        manifest["documents"][0]["sha256"] = "0" * 64
    else:
        manifest["documents"][1]["id"] = manifest["documents"][0]["id"]
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match={"escape": "escapes", "hash": "hash mismatch", "duplicate": "Duplicate"}[kind]):
        load_dataset(path, "all")
