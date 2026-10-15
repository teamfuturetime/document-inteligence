from pathlib import Path
import subprocess
import sys

from fastapi.testclient import TestClient
import pytest

from document_backend.main import create_app
from document_backend.settings import Settings
from document_pipeline.runner import PipelineError, run_document

SAMPLES = Path(__file__).resolve().parents[2] / "data/samples"


@pytest.mark.parametrize("code,status", [("ocr_unavailable", 503), ("processing_timeout", 504),
                                         ("internal_error", 500), ("invalid_document", 422)])
def test_pipeline_failures_are_safe_and_never_fallback_to_mock(monkeypatch, tmp_path, code, status):
    def fail(*args):
        raise PipelineError(code)
    monkeypatch.setattr("document_backend.api.extract.run_document", fail)
    with TestClient(create_app(Settings("real", tmp_path))) as client:
        response = client.post("/api/v1/extract", files={"file": ("sample.png", b"data")})
    assert response.status_code == status and response.json()["error"]["code"] == code
    assert "mock" not in response.text


def test_health_real_mode_missing_models_is_not_ready(tmp_path):
    with TestClient(create_app(Settings("real", tmp_path))) as client:
        assert client.get("/health").json() == {"status": "ok", "mode": "real", "ocr_ready": False}


def test_pipeline_deadline_terminates_actual_worker(monkeypatch, tmp_path):
    popen = subprocess.Popen
    def sleeping_worker(command, **kwargs):
        return popen([sys.executable, "-c", "import time; time.sleep(60)"], **kwargs)
    monkeypatch.setattr("document_pipeline.runner.subprocess.Popen", sleeping_worker)
    with pytest.raises(PipelineError) as error:
        run_document(b"input", tmp_path, "timeout-test", timeout=.05)
    assert error.value.code == "processing_timeout"


@pytest.mark.ocr_integration
@pytest.mark.parametrize("extension", ["png", "jpg", "pdf"])
def test_real_http_extract_validate_flow(extension, tessdata_dir):
    with TestClient(create_app(Settings("real", tessdata_dir))) as client:
        assert client.get("/health").json()["ocr_ready"] is True
        response = client.post("/api/v1/extract", files={"file": (
            f"sample.{extension}", (SAMPLES / f"synthetic-001.{extension}").read_bytes())})
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["mode"] == "real" and result["fields"]["total_amount"]["value"] == 125000
        values = {name: str(field["value"]) if field["value"] is not None else None
                  for name, field in result["fields"].items()}
        validated = client.post("/api/v1/validate", json={"schema_version": "1.0.0", "values": values})
        assert validated.json()["valid"] is True
