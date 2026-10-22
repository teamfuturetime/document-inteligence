"""Repository: truy vấn và lưu trữ metadata tài liệu."""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import Document, Extraction
from app.schemas.documents import DocumentCreate


class DocumentRepository:
    """Thao tác dữ liệu trên bảng documents và extractions."""

    def __init__(self, db: Session):
        self.db = db

    # ===== Create =====
    def create(self, data: DocumentCreate) -> Document:
        """Tạo bản ghi tài liệu mới."""
        doc = Document(
            filename=data.filename,
            content_type=data.content_type,
            file_size=data.file_size,
            file_path=data.file_path,
        )
        self.db.add(doc)
        self.db.flush()
        return doc

    # ===== Read =====
    def get_by_id(self, document_id: str) -> Optional[Document]:
        """Lấy tài liệu theo id."""
        return self.db.get(Document, document_id)

    def get_extraction(self, document_id: str) -> Optional[Extraction]:
        """Lấy kết quả trích xuất của tài liệu."""
        stmt = select(Extraction).where(Extraction.document_id == document_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_documents(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        search: Optional[str] = None,
        document_type: Optional[str] = None,
    ) -> tuple[list[Document], int]:
        """Liệt kê tài liệu với phân trang, lọc và tìm kiếm."""
        stmt = select(Document)
        count_stmt = select(func.count(Document.id))

        if status:
            stmt = stmt.where(Document.status == status)
            count_stmt = count_stmt.where(Document.status == status)
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                or_(Document.filename.ilike(pattern), Document.ocr_text.ilike(pattern))
            )
            count_stmt = count_stmt.where(
                or_(
                    Document.filename.ilike(pattern),
                    Document.ocr_text.ilike(pattern),
                )
            )
        if document_type:
            stmt = stmt.join(Extraction).where(
                Extraction.document_type == document_type
            )
            count_stmt = count_stmt.join(Extraction).where(
                Extraction.document_type == document_type
            )

        total = self.db.execute(count_stmt).scalar_one()
        stmt = (
            stmt.order_by(Document.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = list(self.db.execute(stmt).scalars().all())
        return items, total

    # ===== Update =====
    def update_status(self, document_id: str, status: str) -> Optional[Document]:
        """Cập nhật trạng thái tài liệu."""
        doc = self.get_by_id(document_id)
        if doc is None:
            return None
        doc.status = status
        self.db.flush()
        return doc

    def save_ocr_result(
        self, document_id: str, ocr_text: str, ocr_boxes: list
    ) -> Optional[Document]:
        """Lưu kết quả OCR vào tài liệu."""
        doc = self.get_by_id(document_id)
        if doc is None:
            return None
        doc.ocr_text = ocr_text
        doc.ocr_boxes = ocr_boxes
        self.db.flush()
        return doc

    def save_extraction(
        self,
        document_id: str,
        document_type: str,
        data: dict,
        confidence: float,
    ) -> Extraction:
        """Tạo hoặc cập nhật kết quả trích xuất."""
        extraction = self.get_extraction(document_id)
        if extraction is None:
            extraction = Extraction(
                document_id=document_id,
                document_type=document_type,
                data=data,
                confidence=confidence,
            )
            self.db.add(extraction)
        else:
            extraction.document_type = document_type
            extraction.data = data
            extraction.confidence = confidence
            extraction.status = "pending_review"
        self.db.flush()
        return extraction

    def review_extraction(
        self, document_id: str, data: dict, document_type: str | None = None
    ) -> Optional[Extraction]:
        extraction = self.get_extraction(document_id)
        if extraction is None:
            return None
        extraction.data = data
        if document_type:
            extraction.document_type = document_type
        extraction.status = "reviewed"
        self.db.flush()
        return extraction

    def confirm_extraction(self, document_id: str) -> Optional[Extraction]:
        extraction = self.get_extraction(document_id)
        if extraction is None:
            return None
        extraction.status = "confirmed"
        extraction.confirmed_at = datetime.now(timezone.utc)
        self.db.flush()
        return extraction

    # ===== Delete / Retention =====
    def expired(self, now: datetime | None = None) -> list[Document]:
        """Lấy tài liệu theo ``expires_at`` là nguồn sự thật duy nhất."""
        cutoff = now or datetime.now(timezone.utc)
        stmt = select(Document).where(Document.expires_at.is_not(None), Document.expires_at <= cutoff)
        return list(self.db.execute(stmt).scalars().all())

    def delete(self, document: Document) -> None:
        self.db.delete(document)
        self.db.flush()

    def delete_expired(self, retention_days: int | None = None) -> int:
        """Tương thích API cũ; ``retention_days`` không thay đổi expires_at."""
        expired = self.expired()
        for doc in expired:
            self.db.delete(doc)
        self.db.flush()
        return len(expired)

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()

    def refresh(self, instance: object) -> None:
        self.db.refresh(instance)
