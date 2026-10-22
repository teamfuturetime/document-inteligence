# ruff: noqa: E402
import pytest

pytest.importorskip("fastapi", reason="FastAPI chưa được cài trong môi trường test")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_storage
from app.core.database import Base, get_db
from app.main import app
from app.services.storage import StorageService


@pytest.fixture()
def api_client(tmp_path):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    storage = StorageService(str(tmp_path / "uploads"))

    def override_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_storage] = lambda: storage
    with TestClient(app) as client:
        auth = client.post(
            "/api/v1/auth/register",
            json={"email": "unit@example.test", "username": "unit_user", "password": "Unit-password-123"},
        )
        client.headers.update({"X-CSRF-Token": auth.json()["csrf_token"]})
        yield client, storage
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_upload_list_get_delete_lifecycle(api_client):
    client, storage = api_client
    upload = client.post(
        "/api/v1/documents",
        files={"file": ("sample.pdf", b"%PDF-1.4\n%%EOF", "application/pdf")},
    )
    assert upload.status_code == 201
    document = upload.json()
    assert document["filename"] == "sample.pdf"
    assert "X-Request-ID" in upload.headers
    assert len(list(storage.base_path.iterdir())) == 1

    listing = client.get("/api/v1/documents?page=1&page_size=10")
    assert listing.status_code == 200
    assert listing.json()["total"] == 1

    detail = client.get(f"/api/v1/documents/{document['id']}")
    assert detail.status_code == 200

    deleted = client.delete(f"/api/v1/documents/{document['id']}")
    assert deleted.status_code == 200
    assert list(storage.base_path.iterdir()) == []


def test_upload_rejects_spoofed_content_and_cleans_file(api_client):
    client, storage = api_client
    response = client.post(
        "/api/v1/documents",
        files={"file": ("fake.pdf", b"\x89PNG\r\n\x1a\n", "application/pdf")},
    )
    assert response.status_code == 400
    assert list(storage.base_path.iterdir()) == []


def test_missing_document_returns_404(api_client):
    client, _ = api_client
    assert client.get("/api/v1/documents/missing").status_code == 404
