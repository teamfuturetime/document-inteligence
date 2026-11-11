import json

import pytest

from ai02_solo.ocr import DocumentError
from ai02_solo.settings import Settings
from ai02_solo.vlm import extract_vlm, parse_output

VALUES = dict(invoice_number="M-1", invoice_date=None, seller_name=None, total_amount=10, currency="VND")


@pytest.mark.parametrize("content", ["```json\n{}\n```", "{}", "[]", json.dumps({**VALUES, "extra": "bad"}),
    json.dumps({**VALUES, "total_amount": True}), json.dumps({**VALUES, "total_amount": "10"})])
def test_schema_rejects_malformed_and_coerced_model_responses(content):
    with pytest.raises(DocumentError):
        parse_output(content, "invoice")


def test_ollama_sends_real_image_schema_and_records_server_digest(monkeypatch):
    calls = []
    def transport(url, payload=None, **kwargs):
        calls.append((url, payload))
        if url.endswith("/tags"):
            return {"models": [{"name": "vision:small", "digest": "a" * 64}]}
        if url.endswith("/version"):
            return {"version": "test-server"}
        return {"done": True, "done_reason": "stop", "message": {"content": json.dumps(VALUES)}}
    monkeypatch.setattr("ai02_solo.vlm.request_json", transport)
    values, metadata = extract_vlm(b"image-bytes", "OCR context", "invoice", Settings(vlm_model="vision:small"))
    assert values == VALUES
    payload = calls[-1][1]
    assert payload["messages"][1]["images"] == ["aW1hZ2UtYnl0ZXM="]
    assert payload["format"]["required"] == list(VALUES)
    assert metadata["model_revision"] == "a" * 64
    assert metadata["revision_source"] == "server_digest"


def test_remote_adapter_uses_multimodal_schema_and_operator_revision(monkeypatch):
    calls = []
    monkeypatch.setenv("SOLO_VLM_API_KEY", "test-only-key")
    def transport(url, payload, **kwargs):
        calls.append((url, payload, kwargs))
        return {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(VALUES)}}]}
    monkeypatch.setattr("ai02_solo.vlm.request_json", transport)
    values, metadata = extract_vlm(b"image", "context", "invoice", Settings(vlm_provider="remote",
        vlm_url="https://model.example/v1", vlm_model="vision", vlm_revision="deployment-001"))
    assert values == VALUES
    assert calls[0][0] == "https://model.example/v1/chat/completions"
    assert calls[0][1]["messages"][1]["content"][1]["image_url"]["url"].startswith("data:image/png;base64,")
    assert calls[0][1]["response_format"]["type"] == "json_schema"
    assert metadata["revision_source"] == "operator_declared"
    assert "test-only-key" not in json.dumps(metadata)


def test_unconfigured_model_is_explicit_and_never_mock():
    with pytest.raises(DocumentError, match="Chưa cấu hình"):
        extract_vlm(b"", "", "invoice", Settings())
