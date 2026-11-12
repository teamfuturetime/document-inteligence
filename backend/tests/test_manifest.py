import json

import pytest

from docintel.config import ROOT
from docintel.domain.models import FixtureManifest
from docintel.evaluation.manifest import safe_path, validate_manifest


def manifest():
    return FixtureManifest.model_validate_json(
        (ROOT / "data/manifests/fixtures.json").read_text(encoding="utf-8")
    )


def test_seed_manifest():
    data = manifest()
    assert len(validate_manifest(ROOT, data)) == 6
    assert all(sample.split == "contract_fixture" for sample in data.samples)


@pytest.mark.parametrize("path", ["../outside.json", str(ROOT.parent / "outside.json")])
def test_path_traversal(path):
    with pytest.raises(ValueError, match="ngoài"):
        safe_path(ROOT, path)


def test_parent_overlap_and_checksums():
    data = manifest()
    data.samples[1].parent_document_id = data.samples[0].parent_document_id
    data.samples[1].split = "test"
    with pytest.raises(ValueError, match="overlap"):
        validate_manifest(ROOT, data)
    data = manifest()
    data.samples[0].input_sha256 = "0" * 64
    with pytest.raises(ValueError, match="Checksum"):
        validate_manifest(ROOT, data)


def test_duplicate_ids_and_files():
    data = manifest()
    data.samples[1].sample_id = data.samples[0].sample_id
    with pytest.raises(ValueError, match="sample_id"):
        validate_manifest(ROOT, data)
    data = manifest()
    data.samples[1].input_path = data.samples[0].input_path
    data.samples[1].input_sha256 = data.samples[0].input_sha256
    with pytest.raises(ValueError, match="trùng checksum"):
        validate_manifest(ROOT, data)


def test_gold_has_no_secret_unreadable_value():
    record = json.loads(
        (ROOT / "data/fixtures/annotations/fixture_006.json").read_text(encoding="utf-8")
    )
    assert record["fields"]["student_id"] == {"status": "unreadable", "value": None}
