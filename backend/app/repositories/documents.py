from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import Document


class DocumentRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(
        self, *, original_name: str, stored_name: str, mime_type: str, size_bytes: int
    ) -> Document:
        document = Document(
            original_name=original_name,
            stored_name=stored_name,
            mime_type=mime_type,
            size_bytes=size_bytes,
            expires_at=datetime.now(timezone.utc) + timedelta(days=41),
        )
        self.session.add(document)
        self.session.commit()
        self.session.refresh(document)
        return document

    def get(self, document_id: str) -> Document | None:
        return self.session.get(Document, document_id)

    def update_status(self, document: Document, status: str) -> Document:
        document.status = status
        self.session.commit()
        self.session.refresh(document)
        return document
