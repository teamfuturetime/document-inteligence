# ruff: noqa: E402
import pytest

pytest.importorskip("fastapi", reason="FastAPI chưa được cài trong môi trường test")
from fastapi.testclient import TestClient

from ai_service.main import app
from ai_service.pipeline import DocumentPipeline


def test_health_contract():
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json()["status"] in {"ready", "degraded"}


def test_process_rejects_spoofed_file():
    response = TestClient(app).post(
        "/process", files={"file": ("fake.pdf", b"not a pdf", "application/pdf")}
    )
    assert response.status_code == 400


def test_process_coordinates_pipeline(monkeypatch):
    expected = {"ocr": {}, "classification": {}, "extraction": {}}
    monkeypatch.setattr(DocumentPipeline, "process", lambda self, path: expected)
    response = TestClient(app).post(
        "/process", files={"file": ("valid.pdf", b"%PDF-1.4\n%%EOF", "application/pdf")}
    )
    assert response.status_code == 200
    assert response.json() == expected
