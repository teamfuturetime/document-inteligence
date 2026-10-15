from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models import Base
from app.repositories.documents import DocumentRepository


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
