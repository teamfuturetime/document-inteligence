import base64

import pytest

from docintel.security import hash_password, verify_password


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


def test_password_verification_preserves_unicode_and_rejects_wrong_secret():
    password = "mật-khẩu-synthetic-123"
    encoded = hash_password(password)
    assert verify_password(password, encoded)
    assert not verify_password(password.upper(), encoded)


@pytest.mark.parametrize(
    "encoded",
    [
        "",
        "scrypt$1$x$y",
        "pbkdf2_sha256$999999999999$x$y",
        "pbkdf2_sha256$600000$!!!$bad",
        "x" * 161,
    ],
)
def test_malformed_hash_cannot_select_algorithm_or_cost(encoded):
    assert not verify_password("synthetic-password-123", encoded)
