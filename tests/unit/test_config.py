import pytest
from pydantic import ValidationError

from app.core.config import Settings


@pytest.mark.parametrize("max_upload_mb", [0, -1])
def test_upload_limit_must_be_positive(max_upload_mb: int) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, max_upload_mb=max_upload_mb)


def test_reads_environment_configuration(monkeypatch) -> None:
    monkeypatch.setenv("MAX_UPLOAD_MB", "2")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test-documents.db")
    monkeypatch.setenv("STORAGE_DIR", "./test-uploads")

    settings = Settings(_env_file=None)

    assert settings.max_upload_mb == 2
    assert settings.database_url == "sqlite:///./test-documents.db"
    assert settings.storage_dir == "./test-uploads"
