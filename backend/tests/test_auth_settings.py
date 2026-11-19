import pytest
from pydantic import ValidationError

from docintel.api.app import create_app
from docintel.config import Settings


@pytest.mark.parametrize(
    "origin",
    [
        "*",
        "https://*.example.com",
        "https://example.com/path",
        "https://user:password@example.com",
        "null",
        "https://example.com?query=1",
    ],
)
def test_session_origins_are_exact_not_wildcards_or_urls_with_paths(origin):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, auth_mode="session", cors_origins=[origin])


def test_session_cookie_transport_exception_is_loopback_only():
    assert (
        Settings(_env_file=None, auth_mode="session", session_cookie_secure=False).auth_mode
        == "session"
    )
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            auth_mode="session",
            session_cookie_secure=False,
            cors_origins=["https://example.com"],
        )


def test_default_mode_remains_explicitly_unauthenticated_local():
    assert Settings(_env_file=None).auth_mode == "local"


def test_session_integration_never_exposes_anonymous_product_endpoints(tmp_path):
    from fastapi.testclient import TestClient

    settings = Settings(_env_file=None, auth_mode="session", runtime_dir=tmp_path)
    with TestClient(create_app(settings, start_worker=False)) as api:
        assert api.get("/api/v1/documents").status_code == 401
