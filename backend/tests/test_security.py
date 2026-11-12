import base64

import pytest

from docintel.security import hash_password


def test_password_hash_uses_random_salt_and_pinned_work_factor():
    first, second = [hash_password("synthetic-password-123") for _ in range(2)]
    assert first != second
    algorithm, rounds, salt, digest = first.split("$")
    assert (algorithm, rounds) == ("pbkdf2_sha256", "600000")
    assert len(base64.b64decode(salt)) == 16
    assert len(base64.b64decode(digest)) == 32
    assert "synthetic-password" not in first


@pytest.mark.parametrize("password", ["short", "x" * 129])
def test_password_hash_rejects_unbounded_or_short_secrets(password):
    with pytest.raises(ValueError):
        hash_password(password)
