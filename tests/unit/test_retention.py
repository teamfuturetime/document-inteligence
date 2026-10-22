from datetime import datetime, timedelta, timezone

from app.models import Document
from app.repositories.documents import DocumentRepository
from app.services.retention import RetentionService
from app.services.storage import StorageService


def test_retention_deletes_expired_record_and_file(db_session, tmp_path):
    storage = StorageService(str(tmp_path))
    key = storage.save("old.pdf", b"old")
    document = Document(
        filename="old.pdf",
        content_type="application/pdf",
        file_size=3,
        file_path=key,
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )
    db_session.add(document)
    db_session.commit()
    document_id = document.id

    result = RetentionService(DocumentRepository(db_session), storage).cleanup()
    assert result.deleted_records == 1
    assert result.deleted_files == 1
    assert db_session.get(Document, document_id) is None
    assert list(tmp_path.iterdir()) == []


def test_retention_is_idempotent(db_session, tmp_path):
    service = RetentionService(DocumentRepository(db_session), StorageService(str(tmp_path)))
    assert service.cleanup().deleted_records == 0
    assert service.cleanup().deleted_records == 0
