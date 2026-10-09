"""Integrity checks for curated synthetic fixtures, no OCR required."""

import hashlib
import json
from pathlib import Path

from document_contracts.models import InvoiceValues

SAMPLES = Path(__file__).resolve().parents[1] / "samples"
MANIFEST = json.loads((SAMPLES / "manifest.json").read_text())


def test_sample_manifest_ids_are_unique_and_development_only():
    documents = MANIFEST["documents"]
    assert len({doc["id"] for doc in documents}) == len(documents)
    assert MANIFEST["purpose"] == "development-only"
    assert MANIFEST["schema_version"] == "1.0.0"
    assert all(doc["split"] == "dev" for doc in documents)
    assert "pending" in MANIFEST["ground_truth_review"]


def test_ground_truths_match_versioned_contract_and_hash():
    for doc in MANIFEST["documents"]:
        path = SAMPLES / doc["ground_truth"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == doc["ground_truth_sha256"]
        values = InvoiceValues.model_validate_json(path.read_bytes())
        assert values.invoice_number.startswith("SYN-")


def test_document_hashes_and_file_signatures():
    magic = {".png": b"\x89PNG\r\n\x1a\n", ".jpg": b"\xff\xd8", ".pdf": b"%PDF-"}
    formats = set()
    for doc in MANIFEST["documents"]:
        for variant in doc["variants"]:
            path = SAMPLES / variant["file"]
            data = path.read_bytes()
            assert data.startswith(magic[path.suffix])
            assert hashlib.sha256(data).hexdigest() == variant["sha256"]
            assert variant["pages"] == 1
            assert len(data) < 10 * 1024 * 1024
            formats.add(path.suffix)
    assert formats == {".png", ".jpg", ".pdf"}


def test_missing_currency_is_explicit_not_guessed():
    path = SAMPLES / "synthetic-002-missing.ground-truth.json"
    assert json.loads(path.read_text())["currency"] is None
