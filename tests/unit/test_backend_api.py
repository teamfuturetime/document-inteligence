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


@pytest.mark.parametrize("extension,mime,pages", [
    ("webp", "image/webp", 1), ("bmp", "image/bmp", 1),
    ("tif", "image/tiff", 1), ("tiff", "image/tiff", 2),
    ("png", "image/png", 1), ("jpg", "image/jpeg", 1), ("jpeg", "image/jpeg", 1),
    ("tif", "application/octet-stream", 1),
])
def test_upload_preview_preserves_original(api_client, image_bytes, extension, mime, pages):
    from io import BytesIO
    from PIL import Image

    client, storage = api_client
    data = image_bytes(extension, pages=pages, colors=["red", "blue"])
    upload = client.post("/api/v1/documents", files={"file": ("Bản gốc." + extension, data, mime)})
    assert upload.status_code == 201
    doc = upload.json()
    assert doc["filename"] == "Bản gốc." + extension
    assert doc["file_size"] == len(data)
    assert doc["content_type"] != "application/octet-stream"
    path = next(storage.base_path.iterdir())
    assert path.read_bytes() == data
    preview_url = f"/api/v1/documents/{doc['id']}/preview"
    preview = client.get(preview_url)
    assert preview.status_code == 200
    assert preview.headers["cache-control"] == "private, no-store"
    if extension in {"bmp", "tif", "tiff"}:
        assert preview.headers["content-type"] == "image/png"
        assert int(preview.headers["x-page-count"]) == pages
        assert Image.open(BytesIO(preview.content)).getpixel((0, 0)) == (255, 0, 0)
        assert client.get(preview_url + "?page=0").status_code == 422
        assert client.get(preview_url + f"?page={pages + 1}").status_code == 404
        if pages > 1:
            page2 = client.get(preview_url + "?page=2")
            assert Image.open(BytesIO(page2.content)).getpixel((0, 0)) == (0, 0, 255)
    else:
        assert preview.content == data
    assert path.read_bytes() == data
    assert client.delete(f"/api/v1/documents/{doc['id']}").status_code == 200
    assert list(storage.base_path.iterdir()) == []


@pytest.mark.parametrize("case", ["unsupported", "mime", "mismatch", "corrupt", "empty", "oversize", "pixels", "pages", "later_corrupt"])
def test_invalid_images_leave_no_file_or_record(api_client, image_bytes, monkeypatch, case):
    from app.services.file_validation import settings

    client, storage = api_client
    filename, mime, data = "scan.tiff", "image/tiff", image_bytes("tiff", pages=2)
    if case == "unsupported":
        filename = "scan.gif"
    if case == "mime":
        mime = "text/html"
    if case == "mismatch":
        data = image_bytes("webp")
    if case == "corrupt":
        data = b"II*\x00broken"
    if case == "empty":
        data = b""
    if case == "oversize":
        data += b"0" * (10 * 1024 * 1024)
    if case == "pixels":
        monkeypatch.setattr(settings, "MAX_IMAGE_PIXELS", 100)
    if case == "pages":
        monkeypatch.setattr(settings, "MAX_IMAGE_PAGES", 1)
    if case == "later_corrupt":
        data = data[:-100]
    response = client.post("/api/v1/documents", files={"file": (filename, data, mime)})
    assert response.status_code == (413 if case == "oversize" else 400)
    assert list(storage.base_path.iterdir()) == []
    assert client.get("/api/v1/documents").json()["total"] == 0
