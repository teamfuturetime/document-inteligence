from fastapi.testclient import TestClient

from ai02_solo.api import create_app
from ai02_solo.contracts import Extraction
from ai02_solo.extract import field
from ai02_solo.settings import Settings

VALUES = dict(invoice_number="SYN-1", invoice_date="2026-11-11", seller_name="Cửa hàng Mẫu", total_amount=1000, currency="VND")


def extraction():
    return Extraction(document_type="invoice", document_sha256="a" * 64, mode="rules",
        fields={key: field(value, "rules", [str(value)], [.9]) for key, value in VALUES.items()},
        ocr_text="synthetic", provenance={}, warnings=[])


def test_upload_uses_selected_schema_mode_and_cleans_response(monkeypatch):
    seen = []
    def run(data, kind, mode, settings):
        seen.append((data, kind, mode))
        return extraction()
    monkeypatch.setattr("ai02_solo.api.run", run)
    with TestClient(create_app(Settings())) as client:
        result = client.post("/api/extract", data={"document_type": "invoice", "mode": "rules"}, files={"file": ("x.png", b"data")})
    assert result.status_code == 200
    assert seen == [(b"data", "invoice", "rules")]
    assert result.json()["mode"] == "rules"


def test_review_export_checks_latest_values_and_preserves_ai_original():
    with TestClient(create_app(Settings())) as client:
        invalid = {**VALUES, "invoice_date": "2026-02-30"}
        assert not client.post("/api/validate", json={"document_type": "invoice", "values": invalid}).json()["valid"]
        assert client.post("/api/export", json={"original": extraction().model_dump(), "values": invalid}).status_code == 422
        final = {**VALUES, "seller_name": "Cửa hàng Tổng hợp"}
        result = client.post("/api/export", json={"original": extraction().model_dump(), "values": final})
    assert result.status_code == 200
    assert "attachment" in result.headers["content-disposition"]
    assert result.json()["edited_fields"] == ["seller_name"]
    assert result.json()["original_extraction"]["fields"]["seller_name"]["value"] == VALUES["seller_name"]


def test_schema_and_invalid_requests_are_safe():
    with TestClient(create_app(Settings())) as client:
        assert set(client.get("/api/schemas").json()) == {"invoice", "application"}
        response = client.post("/api/validate", json={"document_type": "other", "values": {"secret": "private"}})
    assert response.status_code == 422
    assert "private" not in response.text


def test_raw_upload_limit_is_enforced_before_multipart_parsing():
    with TestClient(create_app(Settings())) as client:
        response = client.post("/api/extract", content=b"x" * (11 * 1024 * 1024),
                               headers={"Content-Type": "multipart/form-data; boundary=x"})
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "file_size"


def test_ocr_provider_is_selected_per_upload_without_changing_defaults(monkeypatch):
    seen = []
    def run(data, kind, mode, settings):
        seen.append(settings.ocr_provider)
        return extraction()
    monkeypatch.setattr("ai02_solo.api.run", run)
    with TestClient(create_app(Settings())) as client:
        for provider in ["ocrspace", "tesseract"]:
            response = client.post("/api/extract", data={"document_type": "invoice", "mode": "rules", "ocr_provider": provider},
                                   files={"file": ("synthetic.png", b"image")})
            assert response.status_code == 200
        response = client.post("/api/extract", data={"document_type": "invoice", "mode": "rules", "ocr_provider": "unknown"},
                               files={"file": ("synthetic.png", b"image")})
        assert response.status_code == 422
    assert seen == ["ocrspace", "tesseract"]


def test_health_never_exposes_secret_or_calls_cloud(monkeypatch):
    monkeypatch.setenv("SOLO_OCRSPACE_API_KEY", "fake-secret-ocrspace")
    def must_not_call(*args):
        raise AssertionError("Health must not consume cloud quota")
    monkeypatch.setattr("ai02_solo.ocrspace.post_image", must_not_call)
    with TestClient(create_app(Settings())) as client:
        response = client.get("/health")
    assert response.json()["ocr_providers"]["ocrspace"]["configured"] is True
    assert response.json()["ocr_providers"]["ocrspace"]["configuration_only"] is True
    assert "fake-secret-ocrspace" not in response.text
