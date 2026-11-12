import pytest
from fastapi.testclient import TestClient
from test_product import image_bytes, inference

from docintel.api.app import create_app
from docintel.config import Settings
from docintel.security import hash_password
from docintel.services.documents import DocumentService

ORIGIN = "http://127.0.0.1:5173"
PASSWORD = "synthetic-password-123"


@pytest.fixture
def session_api(tmp_path, monkeypatch):
    monkeypatch.setattr(DocumentService, "ensure_ready", lambda self: {})
    settings = Settings(
        _env_file=None,
        auth_mode="session",
        runtime_dir=tmp_path,
        provider_mode="tesseract",
        cors_origins=[ORIGIN],
    )
    with TestClient(create_app(settings, start_worker=False), base_url="https://testserver") as api:
        repository = api.app.state.auth.identities
        repository.create_user("alpha", hash_password(PASSWORD))
        repository.create_user("beta", hash_password(PASSWORD))
        monkeypatch.setattr(api.app.state.documents.pipeline, "run", inference)
        yield api, settings


def login(api, username="alpha"):
    response = api.post(
        "/api/v1/auth/login",
        json={"username": username, "password": PASSWORD},
        headers={"Origin": ORIGIN, "X-Requested-With": "docintel"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def upload(api, csrf):
    return api.post(
        "/api/v1/documents?document_type=hoa_don&data_origin=synthetic",
        content=image_bytes(),
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": "same"},
    )


def test_real_login_owner_isolation_and_logout(session_api):
    api, _ = session_api
    assert api.get("/api/v1/documents").status_code == 401
    state = login(api)
    first = upload(api, state["csrf_token"])
    assert first.status_code == 202, first.text
    document = first.json()
    assert api.get("/api/v1/documents").json()["total"] == 1
    logout = api.post("/api/v1/auth/logout", headers={"X-CSRF-Token": state["csrf_token"]})
    assert logout.status_code == 204 and logout.content == b""
    assert api.get("/api/v1/documents").status_code == 401
    state = login(api, "beta")
    assert api.get("/api/v1/documents").json()["total"] == 0
    assert api.get("/api/v1/documents/" + document["document_id"]).status_code == 404
    assert upload(api, state["csrf_token"]).status_code == 202


def test_session_status_has_no_password_or_session_credential(session_api):
    api, _ = session_api
    anonymous = api.get("/api/v1/auth/session")
    assert anonymous.json() == {"mode": "session", "user": None, "csrf_token": None}
    state = login(api)
    response = api.get("/api/v1/auth/session")
    assert response.json() == state
    assert set(state) == {"mode", "user", "csrf_token"}
    assert set(state["user"]) == {"id", "username"}
    assert response.headers["Cache-Control"] == "no-store"
