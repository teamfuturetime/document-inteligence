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


def test_login_rotates_previous_session_and_logout_revokes_server_state(auth):
    old, first = auth.login(credentials())
    fresh, second = auth.login(credentials(), previous_token=old)
    assert fresh != old and second.csrf_token != first.csrf_token
    assert auth.session(old) is None and auth.session(fresh) is not None
    auth.logout(fresh)
    assert auth.session(fresh) is None


def test_password_reset_revokes_every_existing_session(auth):
    one, principal = auth.login(credentials())
    two, _ = auth.login(credentials())
    auth.identities.reset_password(principal.user.id, hash_password("new-synthetic-password-456"))
    assert auth.session(one) is None and auth.session(two) is None
    with pytest.raises(ProductError):
        auth.login(credentials())
    assert (
        auth.login(credentials(password="new-synthetic-password-456"))[1].user.id
        == principal.user.id
    )


def test_login_budget_is_global_bounded_and_resets_after_window(auth):
    auth.clock = lambda: 100.0
    auth.settings.max_login_attempts = 2
    for username in ("missing", "another"):
        with pytest.raises(ProductError) as rejected:
            auth.login(credentials(username))
        assert rejected.value.status == 401
    with pytest.raises(ProductError) as throttled:
        auth.login(credentials())
    assert throttled.value.status == 429
    with auth.identities.repository.transaction() as connection:
        assert connection.execute("SELECT count(*) FROM login_budget").fetchone()[0] == 1
        assert connection.execute("SELECT attempts FROM login_budget").fetchone()[0] == 2
    auth.clock = lambda: 160.0
    assert auth.login(credentials())[1].user.username == "alpha"


def test_absolute_expiry_and_disabled_user_are_checked_on_every_request(auth):
    auth.clock = lambda: 100.0
    raw, principal = auth.login(credentials())
    auth.clock = lambda: principal.expires_at
    assert auth.session(raw) is None
    auth.clock = lambda: 101.0
    with auth.identities.repository.transaction(write=True) as connection:
        connection.execute("UPDATE users SET is_active=0 WHERE user_id=?", (principal.user.id,))
    assert auth.session(raw) is None


def test_session_cap_keeps_latest_session_when_timestamps_tie(auth):
    auth.clock = lambda: 100.0
    issued = [auth.login(credentials())[0] for _ in range(6)]
    assert auth.session(issued[0]) is None
    assert auth.session(issued[-1]) is not None
    with auth.identities.repository.transaction() as connection:
        assert connection.execute("SELECT count(*) FROM sessions").fetchone()[0] == 5


def test_user_disabled_during_login_cannot_create_a_session(auth, monkeypatch):
    original = auth.identities.create_session

    def race(*args, **kwargs):
        auth.identities.disable(args[1])
        return original(*args, **kwargs)

    monkeypatch.setattr(auth.identities, "create_session", race)
    with pytest.raises(ProductError) as denied:
        auth.login(credentials())
    assert denied.value.status == 401


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
