import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request
from test_product import image_bytes, inference

from docintel.api.app import create_app
from docintel.api.identity import COOKIE_NAME, check_csrf
from docintel.config import Settings
from docintel.security import hash_password
from docintel.services.documents import DocumentService, ProductError

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


def test_cookie_is_http_only_secure_scoped_and_not_readable_from_status(session_api):
    api, _ = session_api
    response = api.post(
        "/api/v1/auth/login",
        json={"username": "alpha", "password": PASSWORD},
        headers={"Origin": ORIGIN, "X-Requested-With": "docintel"},
    )
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "secure" in cookie and "samesite=lax" in cookie
    assert "path=/api/v1" in cookie and "domain=" not in cookie
    assert api.cookies.get(COOKIE_NAME) not in response.text


@pytest.mark.parametrize("csrf", ["", "wrong", "a" * 44])
def test_missing_or_wrong_csrf_cannot_create_document(session_api, csrf):
    api, _ = session_api
    login(api)
    response = upload(api, csrf)
    assert response.status_code == 403
    assert api.get("/api/v1/documents").json()["total"] == 0


def test_nonascii_csrf_is_safe_rejection_not_an_internal_error(session_api):
    api, _ = session_api
    login(api)
    principal = api.app.state.auth.session(api.cookies.get(COOKIE_NAME))
    request = Request(
        {"type": "http", "app": api.app, "headers": [(b"x-csrf-token", b"\xff" * 43)]}
    )
    with pytest.raises(ProductError) as denied:
        check_csrf(request, principal)
    assert denied.value.status == 403


def test_logout_requires_csrf_and_revokes_cookie_with_matching_path(session_api):
    api, _ = session_api
    state = login(api)
    assert api.post("/api/v1/auth/logout").status_code == 403
    assert api.get("/api/v1/documents").status_code == 200
    response = api.post("/api/v1/auth/logout", headers={"X-CSRF-Token": state["csrf_token"]})
    assert response.status_code == 204
    assert "Max-Age=0" in response.headers["set-cookie"]
    assert "Path=/api/v1" in response.headers["set-cookie"]
    assert api.get("/api/v1/documents").status_code == 401


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
