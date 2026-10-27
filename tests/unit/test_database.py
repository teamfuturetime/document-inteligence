from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import create_database_engine
from app.models import Base, Document, Extraction
from app.repositories.documents import DocumentRepository


@pytest.mark.parametrize("database_url", ["sqlite://", "sqlite:///:memory:"])
def test_memory_database_is_shared_across_request_threads(database_url: str) -> None:
    engine = create_database_engine(database_url)
    try:
        Base.metadata.create_all(engine)

        def create_document() -> str:
            with Session(engine) as session:
                document = DocumentRepository(session).create(
                    original_name="scan.png",
                    stored_name="unique.png",
                    mime_type="image/png",
                    size_bytes=64,
                )
                return document.id

        with ThreadPoolExecutor(max_workers=1) as executor:
            document_id = executor.submit(create_document).result(timeout=5)

        with Session(engine) as session:
            assert session.get(Document, document_id).original_name == "scan.png"
    finally:
        engine.dispose()


def test_sqlite_rejects_extraction_without_parent_document() -> None:
    engine = create_database_engine("sqlite://")
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as session:
            session.add(Extraction(document_id="missing-document"))
            with pytest.raises(IntegrityError):
                session.commit()
            session.rollback()
    finally:
        engine.dispose()
