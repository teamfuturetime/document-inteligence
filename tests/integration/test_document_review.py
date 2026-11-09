"""Integration coverage for persisted human document review."""
import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_storage
from app.core.database import Base, get_db
from app.main import app
from app.models import Document
from app.services.storage import StorageService


@pytest.fixture()
def review_client(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)

    def override_db():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_storage] = lambda: StorageService(str(tmp_path / "uploads"))
    with TestClient(app) as client:
        auth = client.post("/api/v1/auth/register", json={"email": "review@example.test", "username": "reviewer", "password": "Review-password-123"})
        csrf = auth.json()["csrf_token"]
        client.headers.update({"X-CSRF-Token": csrf})
        yield client, factory, csrf
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


def make_processed(client, factory):
    uploaded = client.post("/api/v1/documents", files={"file": ("review.pdf", b"%PDF-1.4\n%%EOF", "application/pdf")})
    assert uploaded.status_code == 201
    document_id = uploaded.json()["id"]
    with factory() as db:
        document = db.get(Document, document_id)
        document.status = "processed"
        document.ocr_text = "HO VA TEN: NGUYEN VAN A\nMST: 0101234567"
        db.commit()
    return document_id


def test_ocr_correction_persists_without_modifying_raw(review_client):
    client, factory, _ = review_client
    document_id = make_processed(client, factory)
    corrected = "Họ và tên: Nguyễn Văn A\nMST: 0101234567"
    response = client.patch(f"/api/v1/documents/{document_id}/ocr-correction", json={"text": corrected, "expected_revision": 0})
    assert response.status_code == 200
    assert response.json()["ocr_text_cleaned"] == corrected
    assert response.json()["ocr_text_raw"] == "HO VA TEN: NGUYEN VAN A\nMST: 0101234567"
    assert response.json()["ocr_is_corrected"] is True
    reloaded = client.get(f"/api/v1/documents/{document_id}").json()
    assert reloaded["ocr_text_cleaned"] == corrected
    with factory() as db:
        stored = db.get(Document, document_id)
        assert stored.ocr_text == "HO VA TEN: NGUYEN VAN A\nMST: 0101234567"
        assert stored.ocr_text_corrected == corrected


def test_manual_unknown_extraction_can_be_created_edited_and_deleted(review_client):
    client, factory, _ = review_client
    document_id = make_processed(client, factory)
    created = client.patch(f"/api/v1/documents/{document_id}/extraction", json={"document_type": "unknown", "data": {"Họ và tên": "Nguyễn Văn A", "Ghi chú": "Kiểm tra"}})
    assert created.status_code == 200
    assert created.json()["ai_document_type"] == "unknown"
    assert created.json()["reviewed_document_type"] == "unknown"
    assert created.json()["data"]["Ghi chú"] == "Kiểm tra"
    edited = client.patch(f"/api/v1/documents/{document_id}/extraction", json={"document_type": "other", "data": {"Họ và tên": "Nguyễn Văn B"}})
    assert edited.status_code == 200
    assert edited.json()["data"] == {"Họ và tên": "Nguyễn Văn B"}
    assert edited.json()["document_type"] == "other"
    assert edited.json()["reviewed_document_type"] == "other"
    assert client.patch(f"/api/v1/documents/{document_id}/extraction", json={"document_type": "unknown", "data": {" Tên ": "A", "tên": "B"}}).status_code == 422
    assert client.patch(f"/api/v1/documents/{document_id}/extraction", json={"document_type": "unknown", "data": {" ": "A"}}).status_code == 422


def test_review_requires_csrf_and_ownership(review_client):
    client, factory, csrf = review_client
    document_id = make_processed(client, factory)
    client.headers.pop("X-CSRF-Token")
    assert client.patch(f"/api/v1/documents/{document_id}/ocr-correction", json={"text": "Sửa", "expected_revision": 0}).status_code == 403
    client.headers.update({"X-CSRF-Token": csrf})
    auth_b = client.post("/api/v1/auth/register", json={"email": "other@example.test", "username": "other", "password": "Other-password-123"})
    client.headers.update({"X-CSRF-Token": auth_b.json()["csrf_token"]})
    assert client.patch(f"/api/v1/documents/{document_id}/ocr-correction", json={"text": "Sửa", "expected_revision": 0}).status_code == 404
    assert client.patch(f"/api/v1/documents/{document_id}/extraction", json={"document_type": "unknown", "data": {}}).status_code == 404


def test_confirm_locks_review_reopen_and_export_reviewed_values(review_client):
    client, factory, _ = review_client
    document_id = make_processed(client, factory)
    corrected = "Nội dung đã được người dùng hiệu chỉnh"
    assert client.patch(f"/api/v1/documents/{document_id}/ocr-correction", json={"text": corrected, "expected_revision": 0}).status_code == 200
    assert client.patch(f"/api/v1/documents/{document_id}/extraction", json={"document_type": "other", "data": {"Trường mới": "Giá trị mới"}}).status_code == 200
    confirmed = client.post(f"/api/v1/documents/{document_id}/confirm")
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "confirmed"
    assert client.patch(f"/api/v1/documents/{document_id}/ocr-correction", json={"text": "Không được lưu", "expected_revision": 1}).status_code == 409
    assert client.patch(f"/api/v1/documents/{document_id}/extraction", json={"document_type": "unknown", "data": {}}).status_code == 409
    exported = client.get(f"/api/v1/documents/{document_id}/export")
    assert exported.status_code == 200
    assert exported.json()["ocr_text"] == corrected
    assert exported.json()["ocr_text_raw"] == "HO VA TEN: NGUYEN VAN A\nMST: 0101234567"
    assert exported.json()["fields"] == {"Trường mới": "Giá trị mới"}
    assert exported.json()["document_type"] == "other"
    assert exported.json()["ocr_is_corrected"] is True
    reopened = client.post(f"/api/v1/documents/{document_id}/reopen")
    assert reopened.status_code == 200
    assert reopened.json()["status"] == "reviewed"
    assert client.patch(f"/api/v1/documents/{document_id}/ocr-correction", json={"text": "Có thể sửa lại", "expected_revision": 1}).status_code == 200


def test_stale_revision_rejected_without_overwriting_persisted_ocr(review_client):
    client, factory, _ = review_client
    document_id = make_processed(client, factory)
    endpoint = f"/api/v1/documents/{document_id}/ocr-correction"
    saved = client.patch(endpoint, json={"text": "New draft", "expected_revision": 0})
    assert saved.status_code == 200
    stale = client.patch(endpoint, json={"text": "Old draft", "expected_revision": 0})
    assert stale.status_code == 409
    reloaded = client.get(f"/api/v1/documents/{document_id}").json()
    assert saved.json()["ocr_revision"] == reloaded["ocr_revision"] == 1
    assert reloaded["ocr_text_cleaned"] == "New draft"
    with factory() as db:
        document = db.get(Document, document_id)
        assert document.ocr_text_corrected == "New draft"
        assert document.ocr_text == "HO VA TEN: NGUYEN VAN A\nMST: 0101234567"


@pytest.mark.parametrize("revision", [None, -1, 0.5, "0", True, 2_147_483_648, 10**100])
def test_ocr_correction_requires_valid_revision(review_client, revision):
    client, factory, _ = review_client
    document_id = make_processed(client, factory)
    payload = {"text": "Draft"}
    if revision is not None:
        payload["expected_revision"] = revision
    response = client.patch(f"/api/v1/documents/{document_id}/ocr-correction", json=payload)
    assert response.status_code == 422


def test_ocr_correction_rejects_whitespace(review_client):
    client, factory, _ = review_client
    document_id = make_processed(client, factory)
    response = client.patch(f"/api/v1/documents/{document_id}/ocr-correction", json={"text": " \n\t ", "expected_revision": 0})
    assert response.status_code == 422
    with factory() as db:
        assert db.get(Document, document_id).ocr_text_corrected is None


@pytest.mark.parametrize("status,raw", [("uploaded", "OCR"), ("processing", "OCR"), ("failed", "OCR"), ("confirmed", "OCR"), ("processed", None), ("processed", "")])
def test_ocr_correction_rejects_noneditable_state(review_client, status, raw):
    client, factory, _ = review_client
    document_id = make_processed(client, factory)
    with factory() as db:
        document = db.get(Document, document_id)
        document.status = status
        document.ocr_text = raw
        db.commit()
    response = client.patch(f"/api/v1/documents/{document_id}/ocr-correction", json={"text": "Draft", "expected_revision": 0})
    assert response.status_code == 409
    with factory() as db:
        document = db.get(Document, document_id)
        assert document.ocr_text_corrected is None
        assert document.status == status


def test_ocr_correction_commit_failure_does_not_acknowledge_or_persist(review_client, monkeypatch):
    from sqlalchemy.exc import OperationalError
    from app.repositories.documents import DocumentRepository

    client, factory, _ = review_client
    document_id = make_processed(client, factory)

    def fail_commit(self):
        raise OperationalError("COMMIT", {}, RuntimeError("Simulated storage failure"))

    monkeypatch.setattr(DocumentRepository, "commit", fail_commit)
    response = client.patch(f"/api/v1/documents/{document_id}/ocr-correction", json={"text": "Must not persist", "expected_revision": 0})
    assert response.status_code == 500
    assert "detail" in response.json()
    with factory() as db:
        document = db.get(Document, document_id)
        assert document.ocr_text_corrected is None
        assert document.status == "processed"


def test_ocr_correction_requires_authentication(review_client):
    client, factory, _ = review_client
    document_id = make_processed(client, factory)
    client.cookies.clear()
    response = client.patch(f"/api/v1/documents/{document_id}/ocr-correction", json={"text": "Draft", "expected_revision": 0})
    assert response.status_code == 401


def test_ocr_response_acknowledges_exact_write_even_if_later_writer_commits(review_client, monkeypatch):
    from app.repositories.documents import DocumentRepository

    client, factory, _ = review_client
    document_id = make_processed(client, factory)
    original_commit = DocumentRepository.commit

    def commit_then_later_writer(self):
        original_commit(self)
        # Simulate another client committing immediately after the transaction
        # lock is released, before the first response has been serialized.
        with factory() as db:
            later = DocumentRepository(db)
            assert later.save_ocr_correction(document_id, "Later client draft", 1, self.get_by_id(document_id).owner_id) is not None
            db.commit()

    monkeypatch.setattr(DocumentRepository, "commit", commit_then_later_writer)
    response = client.patch(f"/api/v1/documents/{document_id}/ocr-correction", json={"text": "First client draft", "expected_revision": 0})
    assert response.status_code == 200
    assert response.json()["ocr_revision"] == 1
    assert response.json()["ocr_text_cleaned"] == "First client draft"
    reloaded = client.get(f"/api/v1/documents/{document_id}").json()
    assert reloaded["ocr_revision"] == 2
    assert reloaded["ocr_text_cleaned"] == "Later client draft"


@pytest.mark.parametrize("extension,mime,pages", [
    ("webp", "image/webp", 1), ("bmp", "image/bmp", 1),
    ("tif", "image/tiff", 1), ("tiff", "image/tiff", 2),
    ("png", "image/png", 1), ("jpg", "image/jpeg", 1), ("jpeg", "image/jpeg", 1),
])
def test_image_upload_process_review_export_lifecycle(review_client, image_bytes, monkeypatch, extension, mime, pages):
    import httpx
    from ai_service.main import app as ai_app
    from ai_service.ocr.engine import OCRResult, VietnameseOCREngine

    def recognize(self, candidates, *, page_number, **kwargs):
        height, width = candidates[0].shape[:2]
        return OCRResult(text=f"Trang {page_number}: Họ và tên: Nguyễn Văn A", engine="test", pages=[
            {"page_number": page_number, "width": width, "height": height, "blocks": []}
        ])

    monkeypatch.setattr(VietnameseOCREngine, "recognize_candidates", recognize)

    class LocalAIClient:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, url, files):
            return TestClient(ai_app).post("/process", files=files)

    monkeypatch.setattr(httpx, "AsyncClient", LocalAIClient)
    client, _, csrf = review_client
    content = image_bytes(extension, pages=pages)
    uploaded = client.post("/api/v1/documents", files={"file": ("document." + extension, content, mime)})
    assert uploaded.status_code == 201
    base = "/api/v1/documents/" + uploaded.json()["id"]
    assert client.post(base + "/process").status_code == 200
    detail = client.get(base).json()
    assert detail["status"] == "processed"
    assert [page["page_number"] for page in detail["ocr_pages"]] == list(range(1, pages + 1))
    raw = detail["ocr_text_raw"]
    assert "Trang 1" in raw
    if pages > 1:
        assert raw.index("Trang 1") < raw.index("Trang 2")
    assert client.get(base + "/preview").status_code == 200
    assert client.patch(base + "/ocr-correction", json={"text": "Văn bản đã sửa", "expected_revision": 0}).status_code == 200
    assert client.patch(base + "/extraction", json={"document_type": "other", "data": {"Họ tên": "Nguyễn Văn B"}}).status_code == 200
    assert client.post(base + "/confirm").status_code == 200
    exported = client.get(base + "/export").json()
    assert exported["ocr_text_raw"] == raw
    assert exported["ocr_text"] == "Văn bản đã sửa"
    assert exported["fields"] == {"Họ tên": "Nguyễn Văn B"}
    assert client.patch(base + "/ocr-correction", json={"text": "Không được sửa", "expected_revision": 1}).status_code == 409
    assert client.post(base + "/reopen").status_code == 200
    assert client.get(base).json()["ocr_text_cleaned"] == "Văn bản đã sửa"
    # New previews and image workflows retain the same CSRF/auth/owner boundary.
    client.headers.pop("X-CSRF-Token")
    assert client.post("/api/v1/documents", files={"file": ("scan." + extension, content, mime)}).status_code == 403
    client.headers.update({"X-CSRF-Token": csrf})
    client.cookies.clear()
    assert client.get(base + "/preview").status_code == 401
    auth = client.post("/api/v1/auth/register", json={"email": "foreign@example.test", "username": "foreign", "password": "Foreign-password-123"})
    client.headers.update({"X-CSRF-Token": auth.json()["csrf_token"]})
    for endpoint in [base, base + "/preview", base + "/preview?page=2", base + "/export"]:
        assert client.get(endpoint).status_code == 404
    assert client.post(base + "/process").status_code == 404


@pytest.mark.parametrize("previous_correction", [None, "Previously saved OCR"])
def test_reads_never_persist_ocr_and_only_explicit_patch_changes_correction(review_client, previous_correction):
    client, factory, _ = review_client
    document_id = make_processed(client, factory)
    base = f"/api/v1/documents/{document_id}"
    assert client.patch(base + "/extraction", json={"document_type": "other", "data": {"checked": True}}).status_code == 200
    if previous_correction is not None:
        assert client.patch(base + "/ocr-correction", json={"text": previous_correction, "expected_revision": 0}).status_code == 200

    def snapshot():
        with factory() as db:
            doc = db.get(Document, document_id)
            return (doc.ocr_text, doc.ocr_text_corrected, doc.ocr_revision, doc.ocr_corrected_at, doc.status, doc.updated_at)

    before = snapshot()
    for _ in range(3):
        for endpoint in [base, "/api/v1/documents", base + "/preview", base + "/extraction", base + "/export"]:
            assert client.get(endpoint).status_code == 200
    assert snapshot() == before

    response = client.patch(base + "/ocr-correction", json={"text": "Explicitly saved OCR", "expected_revision": before[2]})
    assert response.status_code == 200
    after = snapshot()
    assert after[0] == before[0]
    assert after[1] == "Explicitly saved OCR"
    assert after[2] == before[2] + 1
    assert after[4] == "reviewed"
    assert response.json()["status"] != "confirmed"
