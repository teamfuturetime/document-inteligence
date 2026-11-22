import base64
import gzip
import hashlib
import io

import pytest
from document_pipeline.errors import PipelineError
from fastapi.testclient import TestClient
from PIL import Image

import docintel.services.documents as document_module
from docintel.api.app import create_app
from docintel.config import ROOT, Settings
from docintel.services.documents import DocumentService

FIXTURES = ROOT / "pipeline/tests/fixtures/pdf"


@pytest.fixture
def product(tmp_path, monkeypatch):
    monkeypatch.setattr(DocumentService, "ensure_ready", lambda self: {})
    settings = Settings(_env_file=None, provider_mode="tesseract", runtime_dir=tmp_path)
    with TestClient(create_app(settings, start_worker=False)) as client:
        yield client, settings


def upload(client, data, *, headers=None):
    return client.post(
        "/api/v1/documents",
        params={"document_type": "hoa_don", "data_origin": "synthetic", "filename": "source.bin"},
        headers={"Idempotency-Key": "pdf-key", **(headers or {})},
        content=data,
    )


def test_pdf_retry_preserves_raw_source_and_png_preview(product):
    client, settings = product
    data = (FIXTURES / "hoa_don_007.pdf").read_bytes()
    first = upload(client, data)
    assert first.status_code == 202, first.text
    document = first.json()
    retry = upload(client, data)
    assert retry.status_code == 202
    assert retry.json()["document_id"] == document["document_id"]
    assert retry.json()["run"]["run_id"] == document["run"]["run_id"]
    assert document["input_sha256"] == hashlib.sha256(data).hexdigest()
    stored_source = settings.runtime_dir / "documents" / f"{document['document_id']}.source"
    assert stored_source.read_bytes() == data
    preview = client.get(document["image_url"])
    assert preview.headers["content-type"] == "image/png"
    assert preview.headers["x-content-type-options"] == "nosniff"
    with Image.open(io.BytesIO(preview.content)) as image:
        assert image.size == (document["image_width"], document["image_height"]) == (1200, 1550)
    assert client.get("/api/v1/capabilities").json()["upload_media_types"] == [
        "image/png",
        "image/jpeg",
        "application/pdf",
    ]
    assert client.get("/api/v1/documents").json()["total"] == 1
    assert len(list((settings.runtime_dir / "documents").iterdir())) == 2


@pytest.mark.parametrize(
    ("payload", "encoding", "code"),
    [
        (lambda _: b"%PDF-1.7\ntruncated", None, "INVALID_PDF"),
        (lambda _: b"<html>fake PDF</html>", None, "INVALID_DOCUMENT"),
        (base64.b64encode, None, "INVALID_DOCUMENT"),
        (gzip.compress, "gzip", "UNSUPPORTED_CONTENT_ENCODING"),
        (lambda _: (FIXTURES / "encrypted.pdf").read_bytes(), None, "PDF_ENCRYPTED"),
    ],
)
def test_pdf_rejects_bad_input_without_admission(product, payload, encoding, code):
    client, settings = product
    raw = (FIXTURES / "hoa_don_007.pdf").read_bytes()
    headers = {"Content-Type": "application/pdf"}
    if encoding:
        headers["Content-Encoding"] = encoding
    response = upload(client, payload(raw), headers=headers)
    assert response.status_code == 415, response.text
    assert response.json()["error"]["code"] == code
    assert client.get("/api/v1/documents").json()["total"] == 0
    assert list((settings.runtime_dir / "documents").iterdir()) == []


def test_pdf_preview_timeout_is_retryable_without_admission(product, monkeypatch):
    client, settings = product
    raw = (FIXTURES / "hoa_don_007.pdf").read_bytes()

    def timed_out(*_):
        raise PipelineError("PROCESSING_TIMEOUT", "Tiền xử lý quá thời gian.")

    with monkeypatch.context() as patch:
        patch.setattr(document_module, "prepare_image", timed_out)
        result = upload(client, raw)

    assert result.status_code == 408
    assert result.json()["error"]["code"] == "PROCESSING_TIMEOUT"
    assert client.get("/api/v1/documents").json()["total"] == 0
    assert list((settings.runtime_dir / "documents").iterdir()) == []
    assert upload(client, raw).status_code == 202
