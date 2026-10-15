"""Unit tests cho DocumentRepository."""
from app.models import Document, Extraction
from app.repositories.documents import DocumentRepository
from app.schemas.documents import DocumentCreate


def _make_doc(db, filename="file.pdf", status="uploaded"):
    repo = DocumentRepository(db)
    return repo.create(
        DocumentCreate(
            filename=filename,
            content_type="application/pdf",
            file_size=1024,
            file_path=f"/storage/uploads/{filename}",
        )
    )


def test_create_document(db_session):
    repo = DocumentRepository(db_session)
    doc = _make_doc(db_session, "hoa-don.pdf")
    assert doc.id is not None
    assert doc.status == "uploaded"
    assert doc.expires_at is not None


def test_get_by_id(db_session):
    doc = _make_doc(db_session, "tim-kiem.pdf")
    repo = DocumentRepository(db_session)
    found = repo.get_by_id(doc.id)
    assert found is not None
    assert found.filename == "tim-kiem.pdf"
    assert repo.get_by_id("not-exist") is None


def test_update_status(db_session):
    doc = _make_doc(db_session)
    repo = DocumentRepository(db_session)
    updated = repo.update_status(doc.id, "processing")
    assert updated is not None
    assert updated.status == "processing"
    assert repo.update_status("not-exist", "x") is None


def test_save_ocr_result(db_session):
    doc = _make_doc(db_session)
    repo = DocumentRepository(db_session)
    boxes = [{"text": "Họ và tên", "box": [0, 0, 100, 20]}]
    updated = repo.save_ocr_result(doc.id, "Họ và tên: Nguyễn Văn A", boxes)
    assert updated.ocr_text == "Họ và tên: Nguyễn Văn A"
    assert updated.ocr_boxes == boxes


def test_save_extraction_creates_and_updates(db_session):
    doc = _make_doc(db_session)
    repo = DocumentRepository(db_session)

    ext = repo.save_extraction(doc.id, "invoice", {"so_tien": 100000}, 0.9)
    assert ext.document_type == "invoice"
    assert ext.status == "pending_review"

    # Cập nhật lần 2
    ext2 = repo.save_extraction(doc.id, "invoice", {"so_tien": 120000}, 0.95)
    assert ext2.id == ext.id
    assert ext2.data == {"so_tien": 120000}
    assert ext2.confidence == 0.95


def test_list_documents_pagination(db_session):
    for i in range(5):
        _make_doc(db_session, f"doc-{i}.pdf")
    repo = DocumentRepository(db_session)
    items, total = repo.list_documents(page=1, page_size=2)
    assert total == 5
    assert len(items) == 2


def test_list_documents_filter_by_status(db_session):
    _make_doc(db_session, "a.pdf")
    repo = DocumentRepository(db_session)
    repo.update_status(repo.list_documents(page_size=50)[0][0].id, "confirmed")

    items, total = repo.list_documents(status="confirmed")
    assert total == 1
    items2, total2 = repo.list_documents(status="uploaded")
    assert total2 == 0


def test_list_documents_search(db_session):
    _make_doc(db_session, "hoa-don-dien-tu.pdf")
    _make_doc(db_session, "hop-dong-lao-dong.pdf")
    repo = DocumentRepository(db_session)

    items, total = repo.list_documents(search="hoa-don")
    assert total == 1
    assert items[0].filename == "hoa-don-dien-tu.pdf"


def test_delete_expired(db_session):
    from datetime import datetime, timedelta, timezone

    old = Document(
        filename="old.pdf",
        content_type="application/pdf",
        file_size=10,
        file_path="/storage/uploads/old.pdf",
        created_at=datetime.now(timezone.utc) - timedelta(days=60),
    )
    db_session.add(old)
    db_session.commit()

    repo = DocumentRepository(db_session)
    deleted = repo.delete_expired(retention_days=41)
    assert deleted == 1
    assert repo.get_by_id(old.id) is None
