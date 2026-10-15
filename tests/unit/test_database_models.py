"""Unit tests cho SQLAlchemy models."""
from datetime import timedelta

from app.core.config import get_settings
from app.models import Document, Extraction


def test_document_creation(db_session):
    """Tạo Document với đầy đủ trường."""
    doc = Document(
        filename="hoa-don.pdf",
        content_type="application/pdf",
        file_size=1024,
        file_path="/storage/uploads/abc.pdf",
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    assert doc.id is not None
    assert doc.filename == "hoa-don.pdf"
    assert doc.status == "uploaded"
    assert doc.created_at is not None
    assert doc.updated_at is not None


def test_document_retention_expiry(db_session):
    """Ràng buộc RE-044: expires_at = created_at + 41 ngày."""
    settings = get_settings()
    doc = Document(
        filename="test.png",
        content_type="image/png",
        file_size=512,
        file_path="/storage/uploads/test.png",
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    assert doc.expires_at is not None
    expected = doc.created_at + timedelta(days=settings.DATA_RETENTION_DAYS)
    assert abs((doc.expires_at - expected).total_seconds()) < 5


def test_extraction_relationship(db_session):
    """Quan hệ 1-1 giữa Document và Extraction."""
    doc = Document(
        filename="don-xin-viec.pdf",
        content_type="application/pdf",
        file_size=2048,
        file_path="/storage/uploads/don.pdf",
    )
    db_session.add(doc)
    db_session.flush()

    extraction = Extraction(
        document_id=doc.id,
        document_type="application_form",
        data={"ho_ten": "Nguyễn Văn A", "ngay_sinh": "1990-01-01"},
        confidence=0.92,
    )
    db_session.add(extraction)
    db_session.commit()
    db_session.refresh(doc)
    db_session.refresh(extraction)

    assert doc.extraction is not None
    assert doc.extraction.document_type == "application_form"
    assert extraction.document.filename == "don-xin-viec.pdf"
    assert extraction.status == "pending_review"


def test_extraction_unique_document(db_session):
    """Một tài liệu chỉ có một extraction (UNIQUE constraint)."""
    doc = Document(
        filename="a.pdf",
        content_type="application/pdf",
        file_size=100,
        file_path="/storage/uploads/a.pdf",
    )
    db_session.add(doc)
    db_session.flush()

    db_session.add(
        Extraction(
            document_id=doc.id,
            document_type="invoice",
            data={"so_tien": 100000},
            confidence=0.9,
        )
    )
    db_session.commit()

    # Thêm extraction thứ 2 cho cùng document phải lỗi
    import pytest
    from sqlalchemy.exc import IntegrityError

    db_session.add(
        Extraction(
            document_id=doc.id,
            document_type="invoice",
            data={"so_tien": 200000},
            confidence=0.8,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_document_cascade_delete(db_session):
    """Xóa Document sẽ xóa luôn Extraction (cascade)."""
    doc = Document(
        filename="b.pdf",
        content_type="application/pdf",
        file_size=100,
        file_path="/storage/uploads/b.pdf",
    )
    db_session.add(doc)
    db_session.flush()
    db_session.add(
        Extraction(
            document_id=doc.id,
            document_type="invoice",
            data={"so_tien": 50000},
            confidence=0.85,
        )
    )
    db_session.commit()

    db_session.delete(doc)
    db_session.commit()

    remaining = db_session.query(Extraction).filter_by(document_id=doc.id).count()
    assert remaining == 0
