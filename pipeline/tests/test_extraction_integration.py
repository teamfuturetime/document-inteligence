"""Development-sample extraction smoke tests with the actual native OCR engine."""

import json
from pathlib import Path

import pytest

from document_pipeline.extraction import extract_invoice
from document_pipeline.ocr import recognize
from document_pipeline.preprocessing import prepare_document

pytestmark = pytest.mark.ocr_integration
SAMPLES = Path(__file__).resolve().parents[2] / "data/samples"


@pytest.mark.parametrize("filename,truth", [
    ("synthetic-001.png", "synthetic-001.ground-truth.json"),
    ("synthetic-001.jpg", "synthetic-001.ground-truth.json"),
    ("synthetic-001.pdf", "synthetic-001.ground-truth.json"),
    ("synthetic-002-missing.png", "synthetic-002-missing.ground-truth.json"),
])
def test_preprocess_ocr_extract_matches_development_ground_truth(filename, truth, tessdata_dir):
    ocr = recognize(prepare_document((SAMPLES / filename).read_bytes()), tessdata_dir)
    result = extract_invoice(ocr.result, filename)
    assert result.mode == "real" and result.ocr_version == ocr.result.ocr_version
    assert {key: field.value for key, field in result.fields} == json.loads((SAMPLES / truth).read_text())
    for _, field in result.fields:
        if field.value is not None:
            assert field.evidence and field.confidence is not None
    if "missing" in filename:
        assert result.fields.currency.value is None
        assert result.fields.currency.confidence is None
        assert result.fields.currency.warnings == ["missing_field"]
