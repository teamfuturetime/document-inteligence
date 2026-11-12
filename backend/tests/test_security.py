import base64

import pytest

from docintel.security import hash_password, new_token, token_digest, verify_password


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


def test_opaque_tokens_are_independent_and_only_digests_need_persistence():
    first, second = new_token(), new_token()
    assert len(first) == 43 and first != second
    assert len(token_digest(first)) == 64
    assert token_digest(first) != token_digest(second)
    assert token_digest(first) != first


@pytest.mark.parametrize("token", ["", "a" * 42, "a" * 44, "a" * 42 + "!", "ü" * 43, "x" * 10000])
def test_malformed_cookies_are_rejected_before_database_lookup(token):
    assert token_digest(token) is None
