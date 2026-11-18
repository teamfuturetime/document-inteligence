"""Disposable native browser test runtime; synthetic test identities, never app seed users."""

import tempfile
from pathlib import Path

import uvicorn
from docintel.api.app import create_app
from docintel.config import Settings
from docintel.repositories.identity import IdentityRepository
from docintel.security import hash_password
from docintel.services.documents import DocumentService


def main():
    with tempfile.TemporaryDirectory(prefix="docintel-auth-browser-") as directory:
        settings = Settings(
            _env_file=None,
            provider_mode="tesseract",
            auth_mode="session",
            session_cookie_secure=False,  # Explicit HTTP loopback-only test profile.
            runtime_dir=Path(directory),
            cors_origins=["http://127.0.0.1:15174"],
            max_login_attempts=100,
        )
        identities = IdentityRepository(DocumentService(settings).repository)
        for username in (
            "alpha",
            "beta",
            "gamma",
            "delta",
            "epsilon",
            "zeta",
            "eta",
            "theta",
        ):
            identities.create_user(
                username, hash_password("synthetic-browser-password-123")
            )
        uvicorn.run(
            create_app(settings), host="127.0.0.1", port=18812, log_level="warning"
        )


if __name__ == "__main__":
    main()
