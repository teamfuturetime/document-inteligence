"""Dịch vụ tìm kiếm, lọc và truy vấn tài liệu."""
from datetime import datetime
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import Document, Extraction


class DocumentSearchService:
    """Tìm kiếm và truy vấn tài liệu với nhiều tiêu chí."""

    def __init__(self, db: Session):
        self.db = db

    def search(
        self,
        *,
        query: Optional[str] = None,
        status: Optional[str] = None,
        document_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Document], int]:
        """Tìm kiếm tài liệu theo từ khóa, trạng thái, loại và khoảng thời gian."""
        stmt = select(Document)
        count_stmt = select(func.count(Document.id))

        if query:
            pattern = f"%{query.strip()}%"
            condition = or_(
                Document.filename.ilike(pattern),
                Document.ocr_text.ilike(pattern),
            )
            stmt = stmt.where(condition)
            count_stmt = count_stmt.where(condition)

        if status:
            stmt = stmt.where(Document.status == status)
            count_stmt = count_stmt.where(Document.status == status)

        if document_type:
            stmt = stmt.join(Extraction).where(
                Extraction.document_type == document_type
            )
            count_stmt = count_stmt.join(Extraction).where(
                Extraction.document_type == document_type
            )

        if date_from:
            stmt = stmt.where(Document.created_at >= date_from)
            count_stmt = count_stmt.where(Document.created_at >= date_from)
        if date_to:
            stmt = stmt.where(Document.created_at <= date_to)
            count_stmt = count_stmt.where(Document.created_at <= date_to)

        total = self.db.execute(count_stmt).scalar_one()
        stmt = (
            stmt.order_by(Document.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = list(self.db.execute(stmt).scalars().all())
        return items, total

    def count_by_status(self) -> dict[str, int]:
        """Đếm số tài liệu theo trạng thái (cho dashboard)."""
        rows = self.db.execute(
            select(Document.status, func.count(Document.id)).group_by(Document.status)
        ).all()
        return {status: count for status, count in rows}

    def count_by_type(self) -> dict[str, int]:
        """Đếm số tài liệu theo loại biểu mẫu (cho dashboard)."""
        rows = self.db.execute(
            select(Extraction.document_type, func.count(Extraction.id)).group_by(
                Extraction.document_type
            )
        ).all()
        return {doc_type: count for doc_type, count in rows}

    def recent_documents(self, limit: int = 10) -> list[Document]:
        """Lấy các tài liệu mới nhất."""
        stmt = select(Document).order_by(Document.created_at.desc()).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def stats(self) -> dict:
        """Thống kê tổng quan cho dashboard."""
        total = self.db.execute(select(func.count(Document.id))).scalar_one()
        confirmed = self.db.execute(
            select(func.count(Document.id)).where(Document.status == "confirmed")
        ).scalar_one()
        processing = self.db.execute(
            select(func.count(Document.id)).where(Document.status == "processing")
        ).scalar_one()
        return {
            "total_documents": total,
            "confirmed": confirmed,
            "processing": processing,
            "by_status": self.count_by_status(),
            "by_type": self.count_by_type(),
        }
