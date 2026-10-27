import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import Base, Document
from app.repositories.documents import DocumentRepository
from app.schemas.documents import DocumentCreate


def test_create_and_search_document() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        repository = DocumentRepository(session)
        created = repository.create(
            original_name="Đơn đề nghị.pdf",
            stored_name="unique.pdf",
            mime_type="application/pdf",
            size_bytes=128,
        )

        documents, total = repository.search(query="đề nghị")

        assert total == 1
        assert documents[0].id == created.id
        assert created.status == "uploaded"
        assert (created.expires_at - created.created_at).days == 41


def test_search_filters_status() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        repository = DocumentRepository(session)
        document = repository.create(
            original_name="cccd.png",
            stored_name="id.png",
            mime_type="image/png",
            size_bytes=64,
        )
        repository.update_status(document, "review")
        assert repository.search(status="review")[1] == 1
        assert repository.search(status="failed")[1] == 0


@pytest.mark.parametrize(
    "invalid_metadata",
    [
        {"original_name": ""},
        {"original_name": "a" * 256},
        {"stored_name": ""},
        {"stored_name": "a" * 256},
        {"mime_type": "text/plain"},
        {"size_bytes": 0},
        {"size_bytes": -1},
    ],
)
def test_document_create_rejects_invalid_metadata(invalid_metadata) -> None:
    metadata = {
        "original_name": "scan.png",
        "stored_name": "unique.png",
        "mime_type": "image/png",
        "size_bytes": 128,
    }
    metadata.update(invalid_metadata)

    with pytest.raises(ValidationError):
        DocumentCreate(**metadata)


def test_duplicate_storage_name_rolls_back_and_session_remains_usable() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        repository = DocumentRepository(session)
        metadata = {
            "original_name": "scan.png",
            "stored_name": "same.png",
            "mime_type": "image/png",
            "size_bytes": 64,
        }
        repository.create(**metadata)

        with pytest.raises(IntegrityError):
            repository.create(**metadata)

        repository.create(**{**metadata, "stored_name": "different.png"})
        assert session.scalar(select(func.count()).select_from(Document)) == 2
    engine.dispose()


@pytest.mark.parametrize("operation", ["refresh", "commit"])
def test_database_error_does_not_persist_document(monkeypatch, operation: str) -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        def fail_operation(*args, **kwargs):
            raise SQLAlchemyError("database unavailable")

        with monkeypatch.context() as patch:
            patch.setattr(session, operation, fail_operation)
            with pytest.raises(SQLAlchemyError):
                DocumentRepository(session).create(
                    original_name="scan.png",
                    stored_name="unique.png",
                    mime_type="image/png",
                    size_bytes=64,
                )

        assert session.scalar(select(func.count()).select_from(Document)) == 0
    engine.dispose()
