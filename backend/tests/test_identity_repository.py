import sqlite3

import pytest

from docintel.repositories.identity import IdentityRepository
from docintel.repositories.sqlite import DocumentRepository
from docintel.security import hash_password, new_token, token_digest


@pytest.fixture
def identities(tmp_path):
    repository = DocumentRepository(tmp_path / "users.sqlite3")
    repository.initialize()
    return IdentityRepository(repository)


def test_identity_storage_never_contains_raw_session_token(identities):
    owner = identities.create_user("alpha", hash_password("synthetic-password-123"))
    raw, csrf = new_token(), new_token()
    identities.create_session(token_digest(raw), owner, csrf, 100, 200)
    with identities.repository.transaction() as connection:
        row = connection.execute("SELECT * FROM sessions").fetchone()
        assert raw not in tuple(row)
    assert identities.active_session(token_digest(raw), 150)["user_id"] == owner
    assert identities.active_session(token_digest(raw), 200) is None
    identities.disable(owner)
    assert identities.active_session(token_digest(raw), 150) is None


def test_reserved_local_identity_cannot_be_registered(identities):
    with pytest.raises(ValueError):
        identities.create_user("__local__", "disabled")


def test_duplicate_username_does_not_create_second_identity(identities):
    identities.create_user("alpha", "test-hash")
    with pytest.raises(sqlite3.IntegrityError):
        identities.create_user("alpha", "test-hash")
