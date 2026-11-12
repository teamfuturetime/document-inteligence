"""Pinned password format and opaque tokens; no credentials belong in logs."""

import base64
import hashlib
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
