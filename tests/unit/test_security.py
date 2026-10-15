from pathlib import Path

import pytest
from fastapi import HTTPException

from app.core.config import get_settings
from app.core.security import require_api_key
from app.services.storage import LocalStorage


def test_storage_rejects_path_traversal(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path)
    with pytest.raises(ValueError, match="Invalid storage path"):
        storage.resolve("../private.txt")


def test_api_key_is_enforced_when_configured() -> None:
    settings = get_settings()
    original = settings.api_key
    settings.api_key = "secret-test-key"
    try:
        with pytest.raises(HTTPException) as error:
            require_api_key("wrong")
        assert error.value.status_code == 401
        assert require_api_key("secret-test-key") is None
    finally:
        settings.api_key = original
