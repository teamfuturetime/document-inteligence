from dataclasses import asdict
from io import BytesIO
import json
from urllib.error import HTTPError

import pytest

from ai02_solo import ocr_backends, ocrspace
from ai02_solo.ocr import DocumentError
from ai02_solo.settings import Settings


def payload():
    return {"OCRExitCode": 1, "IsErroredOnProcessing": False, "ParsedResults": [{
        "FileParseExitCode": 1, "ParsedText": "Số hóa đơn: SYN-001",
        "TextOverlay": {"HasOverlay": True, "Lines": [{"Words": [
            {"WordText": "Số hóa đơn:", "Left": 10, "Top": 20, "Width": 110, "Height": 22},
            {"WordText": "SYN-001", "Left": 130, "Top": 20, "Width": 90, "Height": 22, "Confidence": 99}]}]}}]}


def test_overlay_maps_to_real_tokens_without_fabricating_confidence():
    response = payload()
    response["OCRExitCode"] = "1"
    response["ParsedResults"][0]["FileParseExitCode"] = "1"
    tokens = ocrspace.parse_response(response)
    assert [token.text for token in tokens] == ["Số hóa đơn:", "SYN-001"]
    assert tokens[1].box == (130, 20, 220, 42)
    assert all(token.confidence is None for token in tokens)
    assert all(token.line == (1, 1, 1) for token in tokens)


@pytest.mark.parametrize("change", ["partial", "page_failed", "missing_overlay", "multiple_pages", "bad_geometry", "nonfinite", "nonobject"])
def test_partial_and_invalid_cloud_responses_are_not_accepted(change):
    response = payload()
    page = response["ParsedResults"][0]
    if change == "partial": response["OCRExitCode"] = 2
    if change == "page_failed": page["FileParseExitCode"] = -20
    if change == "missing_overlay": page["TextOverlay"] = None
    if change == "multiple_pages": response["ParsedResults"].append(page.copy())
    if change == "bad_geometry": page["TextOverlay"]["Lines"][0]["Words"][0]["Width"] = -1
    if change == "nonfinite": page["TextOverlay"]["Lines"][0]["Words"][0]["Top"] = float("nan")
    if change == "nonobject": response = []
    with pytest.raises(DocumentError):
        ocrspace.parse_response(response)


def test_empty_document_is_distinct_from_missing_overlay():
    response = payload()
    response["ParsedResults"][0].update(ParsedText="", TextOverlay={"HasOverlay": True, "Lines": []})
    assert ocrspace.parse_response(response) == []


@pytest.mark.parametrize("message,code", [("Invalid API key fake-key", "ocrspace_auth"), ("Rate limit fake-key", "ocrspace_quota")])
def test_provider_error_text_cannot_echo_credentials(message, code):
    with pytest.raises(DocumentError) as caught:
        ocrspace.parse_response({"IsErroredOnProcessing": True, "OCRExitCode": 4, "ErrorMessage": [message]})
    assert caught.value.code == code
    assert "fake-key" not in str(caught.value)


def test_key_stays_in_header_and_never_in_payload_settings_or_metadata(monkeypatch):
    monkeypatch.setenv("SOLO_OCRSPACE_API_KEY", "fake-ocrspace-key")
    seen = []
    class Opener:
        def open(self, request, timeout):
            seen.append(request)
            return BytesIO(json.dumps(payload()).encode())
    monkeypatch.setattr("ai02_solo.ocrspace.urllib.request.build_opener", lambda handler: Opener())
    tokens, metadata = ocrspace.recognize(b"synthetic-png", Settings())
    request = seen[0]
    assert request.full_url == "https://api.ocr.space/parse/image"
    assert request.get_header("Apikey") == "fake-ocrspace-key"
    assert b"fake-ocrspace-key" not in request.data
    assert b'synthetic-png' in request.data
    assert metadata["parameters"]["language"] == "auto"
    assert metadata["parameters"]["OCREngine"] == "2"
    assert metadata["model_revision"] is None
    assert "fake-ocrspace-key" not in json.dumps({**metadata, **asdict(Settings())})
    assert tokens and all(token.confidence is None for token in tokens)


def test_missing_key_and_oversize_fail_before_network(monkeypatch, tmp_path):
    monkeypatch.delenv("SOLO_OCRSPACE_API_KEY", raising=False)
    settings = Settings(ocrspace_key_file=str(tmp_path / "absent.key"))
    def must_not_call(*args):
        pytest.fail("Network called before configuration/size checks")
    monkeypatch.setattr("ai02_solo.ocrspace.post_image", must_not_call)
    assert ocrspace.readiness(settings)["ready"] is False
    with pytest.raises(DocumentError) as error:
        ocrspace.recognize(b"image", settings)
    assert error.value.code == "ocrspace_not_configured"
    monkeypatch.setenv("SOLO_OCRSPACE_API_KEY", "fake-key")
    with pytest.raises(DocumentError) as error:
        ocrspace.recognize(b"x" * (ocrspace.MAX_FILE_BYTES + 1), settings)
    assert error.value.status == 413


@pytest.mark.parametrize("status,expected", [(429, "ocrspace_quota"), (403, "ocrspace_auth"), (500, "ocrspace_unavailable"), (302, "ocrspace_unavailable")])
def test_http_failures_are_safe_and_redirects_not_followed(monkeypatch, status, expected):
    class Opener:
        def open(self, request, timeout):
            raise HTTPError(request.full_url, status, "fake-secret", {}, None)
    monkeypatch.setattr("ai02_solo.ocrspace.urllib.request.build_opener", lambda handler: Opener())
    with pytest.raises(DocumentError) as caught:
        ocrspace.post_image(b"image", "fake-secret", {})
    assert caught.value.code == expected
    assert "fake-secret" not in str(caught.value)
    assert ocrspace.NoRedirect().redirect_request(None, None, 302, "", {}, "https://other.example") is None


def test_cloud_selection_never_runs_tesseract(monkeypatch):
    def local(*args): pytest.fail("Tesseract fallback must not run")
    monkeypatch.setattr("ai02_solo.ocr_backends.ocr.recognize", local)
    monkeypatch.setattr("ai02_solo.ocr_backends.ocrspace.recognize", lambda png, settings: ([], {"provider": "ocrspace"}))
    assert ocr_backends.recognize(b"image", Settings(ocr_provider="ocrspace"))[1]["provider"] == "ocrspace"
