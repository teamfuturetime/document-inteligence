"""Audit failures must be caught even when annotation checksums are updated."""

import hashlib
import json

import pytest

from docintel.config import ROOT
from docintel.evaluation.data_audit import audit_product_manifest


@pytest.fixture
def dataset(tmp_path):
    manifest = json.loads((ROOT / "data/manifests/product.json").read_text(encoding="utf-8"))
    manifest["samples"] = manifest["samples"][:2]
    for sample in manifest["samples"]:
        for kind in ("input", "annotation"):
            relative = sample[f"{kind}_path"]
            target = tmp_path / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / relative).read_bytes())
    return tmp_path, manifest


def audit(dataset, mutate=None):
    root, manifest = dataset
    sample = manifest["samples"][0]
    annotation_path = root / sample["annotation_path"]
    if mutate:
        annotation = json.loads(annotation_path.read_text(encoding="utf-8"))
        mutate(annotation)
        annotation_path.write_text(json.dumps(annotation), encoding="utf-8")
        sample["annotation_sha256"] = hashlib.sha256(annotation_path.read_bytes()).hexdigest()
    manifest_path = root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return audit_product_manifest(root, manifest_path)


def test_bundled_coverage_and_template_overlap_are_explicit():
    report = audit_product_manifest(ROOT, ROOT / "data/manifests/product.json")
    assert report["samples"] == report["parents"] == 150
    assert report["splits"] == {"development": 90, "validation": 30, "test": 30}
    assert report["field_statuses"] == {"present": 882, "absent": 10, "unreadable": 8}
    assert len(report["templates_shared_across_splits"]) == 6
    assert all(
        set(counts) == {"development", "validation", "test"}
        for counts in report["template_splits"].values()
    )
    assert report["new_inference"] is False
    assert report["visual_review_performed"] is False


@pytest.mark.parametrize(
    "mutate,match",
    [
        (lambda a: a.update(sample_id="other"), "sample_id mismatch"),
        (lambda a: a["fields"].pop("currency"), "fields mismatch"),
        (
            lambda a: a["fields"].update(extra={"status": "absent", "value": None}),
            "fields mismatch",
        ),
        (lambda a: a["fields"].update(currency={"value": "VND"}), "label shape"),
        (lambda a: a["fields"]["currency"].update(status="unknown"), "label status"),
        (lambda a: a["fields"]["seller_name"].update(status="unreadable"), "must be null"),
        (lambda a: a["fields"]["seller_name"].update(status="absent"), "must be null"),
        (lambda a: a["fields"]["invoice_number"].update(value=41000), "nonempty NFC"),
        (lambda a: a["fields"]["invoice_number"].update(value=None), "nonempty NFC"),
        (lambda a: a["fields"]["seller_name"].update(value="  Seller  "), "nonempty NFC"),
        (lambda a: a["fields"]["seller_name"].update(value=""), "nonempty NFC"),
        (lambda a: a["fields"]["seller_name"].update(value="Nguye\u0302n"), "nonempty NFC"),
        (lambda a: a["fields"]["total_amount"].update(value=True), "integer label"),
        (lambda a: a["fields"]["total_amount"].update(value="125000"), "integer label"),
    ],
)
def test_reject_invalid_gold_with_matching_hash(dataset, mutate, match):
    with pytest.raises(ValueError, match=match):
        audit(dataset, mutate)


def test_visible_invalid_date_and_zero_are_preserved(dataset):
    def mutate(annotation):
        annotation["fields"]["invoice_date"]["value"] = "31/02/2026"
        annotation["fields"]["total_amount"]["value"] = 0

    assert audit(dataset, mutate)["samples"] == 2


def test_cross_split_identical_labels_fail(dataset):
    root, manifest = dataset
    first, second = manifest["samples"]
    annotation = json.loads((root / first["annotation_path"]).read_text(encoding="utf-8"))
    annotation["sample_id"] = second["sample_id"]
    path = root / second["annotation_path"]
    path.write_text(json.dumps(annotation), encoding="utf-8")
    second["annotation_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="identical label content"):
        audit(dataset)


@pytest.mark.parametrize("kind", ["input", "annotation"])
def test_changed_bytes_fail_existing_hash_guard(dataset, kind):
    root, manifest = dataset
    (root / manifest["samples"][0][f"{kind}_path"]).write_bytes(b"tampered")
    with pytest.raises(ValueError, match="hash mismatch"):
        audit(dataset)


def test_parent_overlap_fails(dataset):
    _, manifest = dataset
    manifest["samples"][1]["parent_document_id"] = manifest["samples"][0]["parent_document_id"]
    with pytest.raises(ValueError, match="Parent document overlaps"):
        audit(dataset)
