from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.core.database import get_db
from app.main import app
from app.models import Base


def build_client(tmp_path: Path) -> TestClient:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)

    def test_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = test_db
    settings = get_settings()
    settings.storage_dir = str(tmp_path)
    settings.max_upload_mb = 1
    return TestClient(app)


def test_upload_list_and_get_document(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    response = client.post(
        "/api/v1/documents",
        files={"file": ("scan.png", b"\x89PNG\r\n\x1a\ncontent", "image/png")},
    )
    assert response.status_code == 201
    document_id = response.json()["id"]
    assert client.get(f"/api/v1/documents/{document_id}").status_code == 200
    listing = client.get("/api/v1/documents").json()
    assert listing["total"] == 1


def test_upload_rejects_spoofed_file(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    response = client.post(
        "/api/v1/documents",
        files={"file": ("fake.pdf", b"not pdf", "application/pdf")},
    )
    assert response.status_code == 422
