import pytest

from docintel.config import Settings
from docintel.domain.auth import Credentials
from docintel.repositories.sqlite import DocumentRepository
from docintel.security import hash_password, token_digest
from docintel.services.auth import AuthService
from docintel.services.documents import ProductError


@pytest.fixture
def auth(tmp_path):
    repository = DocumentRepository(tmp_path / "users.sqlite3")
    repository.initialize()
    service = AuthService(Settings(_env_file=None, auth_mode="session"), repository)
    service.identities.create_user("alpha", hash_password("synthetic-password-123"))
    return service


def credentials(username="alpha", password="synthetic-password-123"):
    return Credentials(username=username, password=password)


def test_login_issues_real_session_with_only_digest_persisted(auth):
    raw, principal = auth.login(credentials())
    assert principal.user.username == "alpha"
    assert auth.session(raw).user == principal.user
    assert "csrf_token" not in repr(principal)
    assert principal.csrf_token not in repr(principal)
    assert auth.session("malformed") is None
    with auth.identities.repository.transaction() as connection:
        row = connection.execute("SELECT * FROM sessions").fetchone()
        assert row["token_hash"] == token_digest(raw) and raw not in tuple(row)


@pytest.mark.parametrize(
    ("username", "password"),
    [("missing", "synthetic-password-123"), ("alpha", "synthetic-wrong-password")],
)
def test_invalid_login_has_generic_status_and_no_session(auth, username, password):
    with pytest.raises(ProductError) as error:
        auth.login(credentials(username, password))
    assert (error.value.status, error.value.code) == (401, "INVALID_CREDENTIALS")
    with auth.identities.repository.transaction() as connection:
        assert connection.execute("SELECT count(*) FROM sessions").fetchone()[0] == 0
