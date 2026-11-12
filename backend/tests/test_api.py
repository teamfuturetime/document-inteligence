from fastapi.testclient import TestClient

from docintel import __version__
from docintel.adapters.fixture import FixtureExtractionAdapter, FixtureOCRAdapter
from docintel.api.app import create_app
from docintel.config import ROOT, Settings


def client(mode="unconfigured"):
    return TestClient(create_app(Settings(_env_file=None, provider_mode=mode)))


def test_health_does_not_claim_ocr():
    with client() as api:
        assert api.get("/api/v1/health").json() == {"status": "ok", "app_version": __version__}
        capabilities = api.get("/api/v1/capabilities").json()
        assert capabilities["ocr_ready"] is False
        assert capabilities["model_benchmark_status"] == "not_measured"
        assert capabilities["features"]["export"] == "implemented"
        assert capabilities["features"]["ocr"] == "unavailable"
        assert len(api.get("/api/v1/schemas").json()[0]["required_fields"]) == 7
        response = api.get("/api/v1/fixtures")
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "PROVIDER_UNAVAILABLE"
        assert response.json()["error"]["request_id"] == response.headers["X-Request-ID"]


def test_fixture_and_unknown_id():
    with client("fixture") as api:
        assert len(api.get("/api/v1/fixtures").json()["sample_ids"]) == 6
        payload = api.get("/api/v1/fixtures/fixture_004").json()
        assert payload["run"]["provenance"]["prediction_source"] == "fixture"
        assert payload["label"] == "Mẫu giả lập — chưa chạy OCR"
        assert api.get("/api/v1/fixtures/fixture_001/image").headers["content-type"] == "image/png"
        assert api.get("/api/v1/fixtures/unknown").status_code == 404
        # The product route now exists, but fixture mode must never process a real upload.
        response = api.post(
            "/api/v1/documents?document_type=hoa_don&data_origin=synthetic", content=b"x"
        )
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "PROVIDER_UNAVAILABLE"


def test_explicit_fixture_gate():
    import pytest

    for adapter in (FixtureOCRAdapter, FixtureExtractionAdapter):
        with pytest.raises(ValueError):
            adapter(ROOT, enabled=False)


def test_corrupt_fixture_fails_with_safe_error(monkeypatch):
    from docintel.services.fixtures import FixtureService

    def corrupted(service):
        raise ValueError("Internal path and data must not leak")

    monkeypatch.setattr(FixtureService, "catalog", corrupted)
    api = TestClient(
        create_app(Settings(_env_file=None, provider_mode="fixture")), raise_server_exceptions=False
    )
    response = api.get("/api/v1/fixtures")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "Internal path" not in response.text


def test_inference_never_reads_gold(monkeypatch):
    from pathlib import Path

    original = Path.read_text

    def guard(path, *args, **kwargs):
        assert "annotations" not in path.parts, "Inference đọc gold"
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guard)
    with client("fixture") as api:
        assert api.get("/api/v1/fixtures/fixture_001").status_code == 200
