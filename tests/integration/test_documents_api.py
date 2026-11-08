import importlib
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, inspect, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.core.database import get_db
from app.main import app
from app.models import Document, Extraction
from app.services.processing import ProcessingConflict, process_document
from app.services.storage import LocalStorage


@pytest.fixture
def api_engine():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def client(tmp_path: Path, api_engine, monkeypatch):
    def test_db():
        with Session(api_engine) as session:
            yield session

    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = test_db
    settings = get_settings()
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    monkeypatch.setattr(settings, "max_upload_mb", 1)
    monkeypatch.setattr(settings, "api_key", "")
    monkeypatch.setattr(settings, "ocr_engine", "mock")
    monkeypatch.setattr(importlib.import_module("app.main"), "engine", api_engine)
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)


def assert_no_documents(api_engine, tmp_path: Path) -> None:
    with Session(api_engine) as session:
        assert session.scalar(select(func.count()).select_from(Document)) == 0
    assert list(tmp_path.iterdir()) == []


def test_startup_initializes_database_and_health_endpoint(client, api_engine) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert {"documents", "extractions"} <= set(inspect(api_engine).get_table_names())


@pytest.mark.parametrize(
    ("filename", "kind", "mime_type"),
    [
        ("Đơn đề nghị.pdf", "pdf", "application/pdf"),
        ("scan.PNG", "png", "image/png"),
        ("scan.jpg", "jpg", "image/jpeg"),
        ("scan.JPEG", "jpg", "image/jpeg"),
    ],
)
def test_upload_persists_file_metadata_and_supports_readback(
    client, api_engine, tmp_path, document_contents, filename, kind, mime_type
) -> None:
    content = document_contents[kind]
    response = client.post(
        "/api/v1/documents", files={"file": (filename, content, mime_type)}
    )

    assert response.status_code == 201
    metadata = response.json()
    assert metadata["original_name"] == filename
    assert metadata["mime_type"] == mime_type
    assert metadata["size_bytes"] == len(content)
    assert metadata["status"] == "uploaded"
    assert metadata["document_type"] is None
    assert (
        datetime.fromisoformat(metadata["expires_at"])
        - datetime.fromisoformat(metadata["created_at"])
    ).days == 41
    document_id = metadata["id"]
    with Session(api_engine) as session:
        document = session.get(Document, document_id)
        assert document is not None
        assert document.stored_name != filename
        assert (tmp_path / document.stored_name).read_bytes() == content
    assert client.get(f"/api/v1/documents/{document_id}").json() == metadata
    assert client.get("/api/v1/documents").json() == {"items": [metadata], "total": 1}
    download = client.get(f"/api/v1/documents/{document_id}/content")
    assert download.status_code == 200
    assert download.content == content
    assert download.headers["content-type"] == mime_type
    assert len(list(tmp_path.iterdir())) == 1


@pytest.mark.parametrize("filename", ["../outside/scan.png", r"C:\outside\scan.png"])
def test_upload_normalizes_filename_paths(client, document_contents, filename) -> None:
    response = client.post(
        "/api/v1/documents",
        files={"file": (filename, document_contents["png"], "image/png")},
    )

    assert response.status_code == 201
    assert response.json()["original_name"] == "scan.png"


@pytest.mark.parametrize(
    ("filename", "content", "mime_type"),
    [
        ("empty.pdf", b"", "application/pdf"),
        ("fake.pdf", b"not pdf", "application/pdf"),
        ("broken.pdf", b"%PDF-1.7\ngarbage\n%%EOF", "application/pdf"),
        ("broken.png", b"\x89PNG\r\n\x1a\ncontent", "image/png"),
        ("oversized.pdf", b"%PDF-" + b"x" * (1024 * 1024), "application/pdf"),
    ],
)
def test_upload_rejects_invalid_files_without_side_effects(
    client, api_engine, tmp_path, filename, content, mime_type
) -> None:
    response = client.post(
        "/api/v1/documents", files={"file": (filename, content, mime_type)}
    )

    assert response.status_code == 422
    assert "detail" in response.json()
    assert_no_documents(api_engine, tmp_path)


@pytest.mark.parametrize("filename", ["", "   ", "a" * 252 + ".png"])
def test_upload_rejects_invalid_filename_metadata(
    client, api_engine, tmp_path, document_contents, filename
) -> None:
    response = client.post(
        "/api/v1/documents",
        files={"file": (filename, document_contents["png"], "image/png")},
    )

    assert response.status_code == 422
    assert_no_documents(api_engine, tmp_path)


def test_upload_detects_mime_for_generic_binary_upload(client, document_contents) -> None:
    response = client.post(
        "/api/v1/documents",
        files={"file": ("scan.png", document_contents["png"], "application/octet-stream")},
    )

    assert response.status_code == 201
    assert response.json()["mime_type"] == "image/png"


@pytest.mark.parametrize(
    ("filename", "mime_type"),
    [("mismatch.pdf", "image/png"), ("scan.png", "application/pdf")],
)
def test_upload_rejects_extension_or_mime_spoofing(
    client, api_engine, tmp_path, document_contents, filename, mime_type
) -> None:
    response = client.post(
        "/api/v1/documents",
        files={"file": (filename, document_contents["png"], mime_type)},
    )

    assert response.status_code == 422
    assert_no_documents(api_engine, tmp_path)


def test_upload_requires_multipart_file(client, api_engine, tmp_path) -> None:
    response = client.post("/api/v1/documents", json={"filename": "scan.pdf"})

    assert response.status_code == 422
    assert_no_documents(api_engine, tmp_path)


def test_database_failure_rolls_back_metadata_and_removes_file(
    client, api_engine, tmp_path, document_contents, monkeypatch
) -> None:
    def fail_commit(*args, **kwargs):
        raise SQLAlchemyError("database unavailable")

    monkeypatch.setattr(Session, "commit", fail_commit)
    response = client.post(
        "/api/v1/documents",
        files={"file": ("scan.png", document_contents["png"], "image/png")},
    )

    assert response.status_code == 503
    assert "database unavailable" not in response.text
    assert_no_documents(api_engine, tmp_path)


def test_storage_failure_does_not_create_metadata(
    client, api_engine, tmp_path, document_contents, monkeypatch
) -> None:
    def fail_save(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(LocalStorage, "save", fail_save)
    response = client.post(
        "/api/v1/documents",
        files={"file": ("scan.png", document_contents["png"], "image/png")},
    )

    assert response.status_code == 500
    assert "disk full" not in response.text
    assert_no_documents(api_engine, tmp_path)


def test_list_rejects_invalid_pagination(client) -> None:
    assert client.get("/api/v1/documents", params={"offset": -1}).status_code == 422
    assert client.get("/api/v1/documents", params={"limit": 0}).status_code == 422
    assert client.get("/api/v1/documents", params={"limit": 101}).status_code == 422


def upload_png(client, document_contents) -> str:
    response = client.post(
        "/api/v1/documents",
        files={"file": ("scan.png", document_contents["png"], "image/png")},
    )
    assert response.status_code == 201
    return response.json()["id"]


@pytest.mark.parametrize("document_status", ["processing", "confirmed"])
def test_processing_rejects_unavailable_documents(
    client, api_engine, document_contents, document_status
) -> None:
    document_id = upload_png(client, document_contents)
    with Session(api_engine) as db:
        db.get(Document, document_id).status = document_status
        db.commit()

    assert client.post(f"/api/v1/documents/{document_id}/process").status_code == 409
    with Session(api_engine) as db:
        assert db.scalar(select(func.count()).select_from(Extraction)) == 0


def test_processing_claim_rejects_a_stale_session(
    client, api_engine, document_contents, monkeypatch
) -> None:
    from ai_service.main import DocumentIntelligence

    document_id = upload_png(client, document_contents)
    analyze = DocumentIntelligence.analyze
    with Session(api_engine, expire_on_commit=False) as competing_db:
        stale_document = competing_db.get(Document, document_id)
        assert stale_document.status == "uploaded"

        def analyze_with_competing_request(pipeline, pages):
            with pytest.raises(ProcessingConflict):
                process_document(competing_db, stale_document)
            return analyze(pipeline, pages)

        monkeypatch.setattr(DocumentIntelligence, "analyze", analyze_with_competing_request)
        assert client.post(f"/api/v1/documents/{document_id}/process").status_code == 202

    with Session(api_engine) as db:
        assert db.get(Document, document_id).status == "review"
        assert db.scalar(select(func.count()).select_from(Extraction)) == 1


def test_failed_extraction_transaction_rolls_back_and_can_be_retried(
    client, api_engine, document_contents
) -> None:
    document_id = upload_png(client, document_contents)

    def reject_extraction(mapper, connection, target):
        raise IntegrityError("insert extraction", {}, Exception("private database detail"))

    event.listen(Extraction, "before_insert", reject_extraction)
    try:
        response = client.post(f"/api/v1/documents/{document_id}/process")
    finally:
        event.remove(Extraction, "before_insert", reject_extraction)

    assert response.status_code == 503
    assert "private database detail" not in response.text
    with Session(api_engine) as db:
        document = db.get(Document, document_id)
        assert document.status == "failed"
        assert document.document_type is None
        assert db.scalar(select(func.count()).select_from(Extraction)) == 0

    assert client.post(f"/api/v1/documents/{document_id}/process").status_code == 202
    assert client.get(f"/api/v1/documents/{document_id}").json()["status"] == "review"


@pytest.fixture
def review_document(client, api_engine, document_contents):
    document_id = upload_png(client, document_contents)
    assert client.post(f"/api/v1/documents/{document_id}/process").status_code == 202
    with Session(api_engine) as db:
        extraction = db.scalar(select(Extraction).where(Extraction.document_id == document_id))
        extraction.document.document_type = "invoice"
        extraction.warnings = ["Cần đối chiếu bản gốc", "Không tìm thấy trường: total_amount"]
        extraction.data = {
            "document_type": "invoice", "raw_text": "Khách hàng: An\nTổng cộng:",
            "pages": [{"width": 100, "height": 200, "lines": []}],
            "model_version": "rules-v1", "warnings": extraction.warnings,
            "fields": {
                "customer": {"value": "An", "confidence": 0.8, "source_text": "Khách hàng: An"},
                "total_amount": {"value": None, "confidence": 0.0, "source_text": None},
            },
        }
        db.commit()
    return document_id


def test_review_edits_values_and_preserves_ocr_evidence(client, review_document) -> None:
    endpoint = f"/api/v1/documents/{review_document}/extraction"
    original = client.get(endpoint).json()
    response = client.patch(endpoint, json={
        "data": {
            "raw_text": "forged text", "pages": [], "document_type": "identity_card",
            "model_version": "forged-version",
            "fields": {"total_amount": {"value": "100.000", "confidence": 1, "source_text": "forged"}},
        },
        "warnings": [],
    })

    assert response.status_code == 200
    result = response.json()
    for key in ("raw_text", "pages", "document_type", "model_version"):
        assert result["data"][key] == original["data"][key]
    assert result["data"]["fields"]["customer"] == original["data"]["fields"]["customer"]
    assert result["data"]["fields"]["total_amount"] == {
        "value": "100.000", "confidence": 0.0, "source_text": None, "reviewed": True,
    }
    assert result["warnings"] == result["data"]["warnings"] == ["Cần đối chiếu bản gốc"]

    cleared = client.patch(endpoint, json={"data": {"fields": {
        "customer": {"value": "", "confidence": 0.8},
    }}}).json()
    assert cleared["warnings"] == ["Cần đối chiếu bản gốc", "Không tìm thấy trường: customer"]
    assert cleared["data"]["fields"]["total_amount"]["value"] == "100.000"


@pytest.mark.parametrize("data", [
    {}, {"fields": []}, {"fields": {"customer": {"value": "A", "confidence": 2}}},
    {"fields": {"invented_field": {"value": "A", "confidence": 0.8}}},
])
def test_review_rejects_invalid_updates_without_changes(client, review_document, data) -> None:
    endpoint = f"/api/v1/documents/{review_document}/extraction"
    original = client.get(endpoint).json()

    assert client.patch(endpoint, json={"data": data}).status_code == 422
    assert client.get(endpoint).json() == original


@pytest.mark.parametrize("document_status", ["processing", "failed", "uploaded"])
def test_review_mutations_reject_documents_outside_review(
    client, api_engine, review_document, document_status
) -> None:
    with Session(api_engine) as db:
        db.get(Document, review_document).status = document_status
        db.commit()

    base = f"/api/v1/documents/{review_document}"
    assert client.patch(f"{base}/extraction", json={"data": {"fields": {}}}).status_code == 409
    assert client.post(f"{base}/confirm").status_code == 409
    assert not client.get(f"{base}/extraction").json()["confirmed"]


def test_confirmation_is_repeatable_and_prevents_further_edits(client, review_document) -> None:
    base = f"/api/v1/documents/{review_document}"
    confirmed = client.post(f"{base}/confirm")
    assert confirmed.status_code == 200
    assert confirmed.json()["confirmed"]
    assert client.post(f"{base}/confirm").json() == confirmed.json()
    assert client.get(base).json()["status"] == "confirmed"
    assert client.patch(f"{base}/extraction", json={"data": {"fields": {}}}).status_code == 409
    assert client.post(f"{base}/process").status_code == 409
