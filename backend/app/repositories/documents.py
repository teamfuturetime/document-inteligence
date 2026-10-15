from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_, select
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

    def search(
        self,
        *,
        query: str | None = None,
        status: str | None = None,
        document_type: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Document], int]:
        filters = []
        if query:
            escaped = query.replace("%", r"\%").replace("_", r"\_")
            filters.append(or_(Document.original_name.ilike(f"%{escaped}%", escape="\\"), Document.id == query))
        if status:
            filters.append(Document.status == status)
        if document_type:
            filters.append(Document.document_type == document_type)

        total = self.session.scalar(select(func.count()).select_from(Document).where(*filters)) or 0
        statement = (
            select(Document)
            .where(*filters)
            .order_by(Document.created_at.desc())
            .offset(max(offset, 0))
            .limit(min(max(limit, 1), 100))
        )
        return list(self.session.scalars(statement)), total
