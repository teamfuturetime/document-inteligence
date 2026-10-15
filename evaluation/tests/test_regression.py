from pathlib import Path

import pytest

from document_evaluation.cli import evaluate

pytestmark = pytest.mark.ocr_integration
MANIFEST = Path(__file__).resolve().parents[2] / "data/golden/manifest.json"


def test_frozen_held_out_quality_target_on_real_pipeline(tessdata_dir):
    report = evaluate(MANIFEST, tessdata_dir, "test")
    assert report["documents"] == 12
    assert report["execution_errors"] == 0
    assert report["metrics"]["macro"]["exact_match"] >= .85
