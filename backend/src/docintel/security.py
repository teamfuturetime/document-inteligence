"""Pinned password format and opaque tokens; no credentials belong in logs."""

import base64
import binascii
import hashlib
import hmac
import re
import secrets

PASSWORD_ROUNDS = 600_000


def hash_password(password: str) -> str:
    if not 12 <= len(password) <= 128:
        raise ValueError("Password must contain 12 to 128 characters")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PASSWORD_ROUNDS)
    return (
        "pbkdf2_sha256$600000$"
        + base64.b64encode(salt).decode()
        + "$"
        + base64.b64encode(digest).decode()
    )


def verify_password(password: str, encoded: str) -> bool:
    if not 12 <= len(password) <= 128 or len(encoded) > 160:
        return False
    try:
        algorithm, rounds, salt_text, digest_text = encoded.split("$")
        if algorithm != "pbkdf2_sha256" or rounds != "600000":
            return False
        salt = base64.b64decode(salt_text, validate=True)
        expected = base64.b64decode(digest_text, validate=True)
        if len(salt) != 16 or len(expected) != 32:
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PASSWORD_ROUNDS)
        return hmac.compare_digest(actual, expected)
    except ValueError, binascii.Error:
        return False


def new_token() -> str:
    return secrets.token_urlsafe(32)


def token_digest(token: str) -> str | None:
    if not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        return None
    return hashlib.sha256(token.encode("ascii")).hexdigest()
