import asyncio
import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfWriter
from starlette.datastructures import UploadFile

from document_backend.api.extract import MAX_REQUEST_BYTES, bounded_body
from document_backend.errors import DocumentError
from document_backend.main import create_app
from document_backend.services.documents import MAX_FILE_BYTES, validate_document
from document_contracts.models import APIErrorResponse, ExtractionResponse

SAMPLES = Path(__file__).resolve().parents[2] / "data/samples"


@pytest.fixture
def client():
    with TestClient(create_app()) as instance:
        yield instance


@pytest.mark.parametrize("extension", ["png", "jpg", "pdf"])
def test_supported_file_returns_explicit_fixed_mock(client, extension):
    data = (SAMPLES / f"synthetic-001.{extension}").read_bytes()
    response = client.post("/api/v1/extract", files={"file": (f"sample.{extension}", data)})
    assert response.status_code == 200
    result = ExtractionResponse.model_validate(response.json())
    assert result.mode == "mock"
    assert result.ocr_version == "mock-not-run"
    assert "not_derived_from_upload" in result.warnings
    assert result.fields.invoice_number.value == "SYN-0001"
    assert all(field.confidence is None for field in [result.fields.invoice_number, result.fields.total_amount])


def test_mock_does_not_claim_to_extract_missing_document(client):
    data = (SAMPLES / "synthetic-002-missing.png").read_bytes()
    responses = [client.post("/api/v1/extract", files={"file": ("sample.png", data)}).json() for _ in range(2)]
    assert responses[0]["fields"]["invoice_number"]["value"] == "SYN-0001"
    assert responses[0]["document_id"] != responses[1]["document_id"]
    assert "not_derived_from_upload" in responses[0]["warnings"]


def test_content_validation_does_not_trust_filename_or_mime(client):
    data = (SAMPLES / "synthetic-001.png").read_bytes()
    response = client.post("/api/v1/extract", files={"file": ("../../unsafe.exe", data, "text/plain")})
    assert response.status_code == 200


@pytest.mark.parametrize("data,status,code", [
    (b"", 422, "invalid_document"),
    (b"pretend PNG", 415, "unsupported_media_type"),
    (b"\x89PNG\r\n\x1a\nbroken", 422, "invalid_document"),
    (b"%PDF-broken", 422, "invalid_document"),
    (b"x" * (MAX_FILE_BYTES + 1), 413, "file_too_large"),
])
def test_invalid_files_use_error_contract(client, data, status, code):
    response = client.post("/api/v1/extract", files={"file": ("sample.png", data, "image/png")})
    assert response.status_code == status
    assert APIErrorResponse.model_validate(response.json()).error.code == code


def test_multi_page_pdf_rejected(client):
    with PdfWriter() as document, io.BytesIO() as stream:
        document.add_blank_page(width=300, height=400)
        document.add_blank_page(width=300, height=400)
        document.write(stream)
        data = stream.getvalue()
    response = client.post("/api/v1/extract", files={"file": ("sample.pdf", data)})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "multiple_pages"


def test_encrypted_pdf_rejected(client):
    with PdfWriter() as document, io.BytesIO() as stream:
        document.add_blank_page(width=300, height=400)
        document.encrypt("synthetic")
        document.write(stream)
        data = stream.getvalue()
    response = client.post("/api/v1/extract", files={"file": ("sample.pdf", data)})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_document"


def test_oversized_decoded_image_rejected_before_load():
    stream = io.BytesIO()
    Image.new("1", (5001, 5000)).save(stream, format="PNG")
    with pytest.raises(DocumentError) as error:
        validate_document(stream.getvalue())
    assert error.value.code == "image_too_large"


@pytest.mark.parametrize("files", [
    {"other": ("sample.png", b"data")},
    [("file", ("one.png", b"data")), ("file", ("two.png", b"data"))],
])
def test_wrong_or_duplicate_file_parts_rejected(client, files):
    response = client.post("/api/v1/extract", files=files)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


def test_missing_file_extra_fields_and_missing_boundary_rejected(client):
    requests = [
        {"json": {}},
        {"files": {"file": ("sample.png", b"data")}, "data": {"extra": "value"}},
        {"content": b"invalid", "headers": {"content-type": "multipart/form-data"}},
    ]
    for arguments in requests:
        response = client.post("/api/v1/extract", **arguments)
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "invalid_request"


def test_body_limit_counts_stream_bytes_without_content_length(client):
    def chunks():
        yield b"a" * (MAX_REQUEST_BYTES // 2)
        yield b"b" * (MAX_REQUEST_BYTES // 2 + 1)
    response = client.post("/api/v1/extract", content=chunks(), headers={"content-type": "multipart/form-data; boundary=x"})
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "file_too_large"


def test_bounded_stream_stops_reading_as_soon_as_limit_exceeded():
    consumed = []
    async def chunks():
        for index in range(3):
            consumed.append(index)
            yield b"x" * MAX_REQUEST_BYTES
    with pytest.raises(DocumentError):
        asyncio.run(bounded_body(chunks()))
    assert consumed == [0, 1]


@pytest.mark.parametrize("data", [b"invalid", (SAMPLES / "synthetic-001.png").read_bytes()])
def test_upload_handle_is_closed_on_success_and_validation_error(client, monkeypatch, data):
    closed = []
    original = UploadFile.close
    async def close(upload):
        await original(upload)
        closed.append(upload.file.closed)
    monkeypatch.setattr(UploadFile, "close", close)
    client.post("/api/v1/extract", files={"file": ("sample.png", data)})
    assert closed == [True]
