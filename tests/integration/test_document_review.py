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
    response = client.patch(f"/api/v1/documents/{document_id}/ocr-correction", json={"text": corrected})
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
    assert client.patch(f"/api/v1/documents/{document_id}/ocr-correction", json={"text": "Sửa"}).status_code == 403
    client.headers.update({"X-CSRF-Token": csrf})
    auth_b = client.post("/api/v1/auth/register", json={"email": "other@example.test", "username": "other", "password": "Other-password-123"})
    client.headers.update({"X-CSRF-Token": auth_b.json()["csrf_token"]})
    assert client.patch(f"/api/v1/documents/{document_id}/ocr-correction", json={"text": "Sửa"}).status_code == 404
    assert client.patch(f"/api/v1/documents/{document_id}/extraction", json={"document_type": "unknown", "data": {}}).status_code == 404


def test_confirm_locks_review_reopen_and_export_reviewed_values(review_client):
    client, factory, _ = review_client
    document_id = make_processed(client, factory)
    corrected = "Nội dung đã được người dùng hiệu chỉnh"
    assert client.patch(f"/api/v1/documents/{document_id}/ocr-correction", json={"text": corrected}).status_code == 200
    assert client.patch(f"/api/v1/documents/{document_id}/extraction", json={"document_type": "other", "data": {"Trường mới": "Giá trị mới"}}).status_code == 200
    confirmed = client.post(f"/api/v1/documents/{document_id}/confirm")
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "confirmed"
    assert client.patch(f"/api/v1/documents/{document_id}/ocr-correction", json={"text": "Không được lưu"}).status_code == 409
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
    assert client.patch(f"/api/v1/documents/{document_id}/ocr-correction", json={"text": "Có thể sửa lại"}).status_code == 200
