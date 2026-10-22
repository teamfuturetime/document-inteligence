import asyncio
import io

# ruff: noqa: E402
import pytest

pytest.importorskip("fastapi", reason="FastAPI chưa được cài trong môi trường test")

from fastapi import UploadFile

from app.services.storage import StorageService
from app.services.upload import DocumentUploadService


class FailingRepository:
    rolled_back = False

    def create(self, data):
        raise RuntimeError("database unavailable")

    def rollback(self):
        self.rolled_back = True


def test_database_failure_removes_uploaded_file(tmp_path):
    repository = FailingRepository()
    storage = StorageService(str(tmp_path))
    upload = UploadFile(
        filename="valid.pdf",
        file=io.BytesIO(b"%PDF-1.4\n%%EOF"),
        headers={"content-type": "application/pdf"},
    )
    with pytest.raises(RuntimeError):
        asyncio.run(DocumentUploadService(repository, storage).upload(upload))
    assert repository.rolled_back
    assert list(tmp_path.iterdir()) == []
