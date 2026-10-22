"""SQLite-backed API integration coverage for auth, CSRF, and ownership."""
import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_storage
from app.core.database import Base, get_db
from app.main import app
from app.services.storage import StorageService


@pytest.fixture()
def client(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)
    def override_db():
        with factory() as session: yield session
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_storage] = lambda: StorageService(str(tmp_path / "uploads"))
    with TestClient(app) as value: yield value
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def register(client, name):
    response = client.post("/api/v1/auth/register", json={"email": f"{name}@example.test", "username": name, "password": "Demo-password-123"})
    assert response.status_code == 201
    return response.json()["csrf_token"]


def test_auth_csrf_and_document_ownership(client):
    assert client.get("/api/v1/documents").status_code == 401
    csrf_a = register(client, "user_a")
    assert client.post("/api/v1/documents", files={"file": ("a.pdf", b"%PDF-1.4\n%%EOF", "application/pdf")}).status_code == 403
    uploaded = client.post("/api/v1/documents", headers={"X-CSRF-Token": csrf_a}, files={"file": ("a.pdf", b"%PDF-1.4\n%%EOF", "application/pdf")})
    assert uploaded.status_code == 201
    document_id = uploaded.json()["id"]
    client.cookies.clear()
    register(client, "user_b")
    assert client.get(f"/api/v1/documents/{document_id}").status_code == 404
    assert client.get(f"/api/v1/documents/{document_id}/preview").status_code == 404


def test_login_logout(client):
    csrf = register(client, "login_user")
    assert client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf}).status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 401
    login = client.post("/api/v1/auth/login", json={"login": "login_user", "password": "Demo-password-123"})
    assert login.status_code == 200
    assert login.json()["user"]["email"] == "login_user@example.test"
    assert client.get("/api/v1/auth/me").json()["csrf_token"]
