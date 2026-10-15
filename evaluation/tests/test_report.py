from pathlib import Path

import pytest

from document_evaluation.cli import evaluate
from document_pipeline.runner import PipelineError

MANIFEST = Path(__file__).resolve().parents[2] / "data/golden/manifest.json"


def test_execution_failures_stay_in_denominator_and_reports_are_reproducible(monkeypatch, tmp_path):
    def unavailable(*args, **kwargs):
        raise PipelineError("ocr_unavailable")
    monkeypatch.setattr("document_evaluation.cli.run_document", unavailable)
    first = evaluate(MANIFEST, tmp_path, "test")
    second = evaluate(MANIFEST, tmp_path, "test")
    assert first == second
    assert first["documents"] == first["execution_errors"] == 12
    assert first["target"]["met"] is False
    assert first["metrics"]["fields"]["invoice_number"]["total"] == 12
    assert first["records"][0]["mismatches"][0]["cause"] == "unverified"


def test_evaluation_rejects_mock_pipeline_output(monkeypatch, tmp_path):
    from types import SimpleNamespace
    monkeypatch.setattr("document_evaluation.cli.run_document", lambda *args, **kwargs:
                        SimpleNamespace(result=SimpleNamespace(mode="mock")))
    with pytest.raises(ValueError, match="refuses mock"):
        evaluate(MANIFEST, tmp_path, "test")
