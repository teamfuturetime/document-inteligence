import pytest
from pydantic import ValidationError

from docintel.domain.auth import Credentials, SessionState


def test_credentials_hide_password_and_do_not_accept_owner_claims():
    credentials = Credentials(username="alpha", password="synthetic-password-123")
    assert "synthetic-password" not in repr(credentials)
    with pytest.raises(ValidationError):
        Credentials(username="alpha", password="synthetic-password-123", owner_id="forged")


@pytest.mark.parametrize(
    "username", ["ab", "Alpha", "__local__", "a" * 33, "user@example.com", "../user"]
)
def test_usernames_have_one_canonical_ascii_namespace(username):
    with pytest.raises(ValidationError):
        Credentials(username=username, password="synthetic-password-123")


def test_local_status_does_not_invent_an_authenticated_identity():
    assert SessionState(mode="local").model_dump() == {
        "mode": "local",
        "user": None,
        "csrf_token": None,
    }
