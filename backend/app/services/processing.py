import logging

from sqlalchemy import update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ai_service.main import DocumentIntelligence
from ai_service.ocr.engines import EmptyOcrEngine, PaddleOcrEngine, TesseractOcrEngine
from ai_service.ocr.service import OcrService
from ai_service.preprocessing import load_pages
from app.core.config import get_settings
from app.models import Document, Extraction
from app.services.storage import LocalStorage

logger = logging.getLogger(__name__)


class ProcessingConflict(RuntimeError):
    """The document cannot be claimed for processing in its current state."""


def process_document(db: Session, document: Document) -> Extraction:
    settings = get_settings()
    document_id = document.id
    # A conditional UPDATE claims the document across workers, including SQLite
    # where SELECT FOR UPDATE does not lock rows. Commit before running OCR.
    claimed = db.execute(
        update(Document)
        .where(Document.id == document_id, Document.status.in_(["uploaded", "review", "failed"]))
        .values(status="processing")
        .execution_options(synchronize_session=False)
    )
    if claimed.rowcount != 1:
        db.rollback()
        raise ProcessingConflict("Tài liệu đang xử lý hoặc đã xác nhận")
    db.commit()
    try:
        db.refresh(document)
        path = LocalStorage(settings.storage_dir).resolve(document.stored_name)
        pages = load_pages(path.read_bytes(), document.original_name)
        engines = {
            "mock": EmptyOcrEngine,
            "paddle": PaddleOcrEngine,
            "tesseract": TesseractOcrEngine,
        }
        try:
            engine = engines[settings.ocr_engine]()
        except KeyError as error:
            raise ValueError(f"OCR engine không được hỗ trợ: {settings.ocr_engine}") from error
        analysis = DocumentIntelligence(OcrService(engine)).analyze(pages)
        document.document_type = analysis.classification.document_type
        document.status = "review"
        extraction = Extraction(
            document=document,
            data=analysis.extraction.model_dump(mode="json"),
            warnings=analysis.extraction.warnings,
            model_version=analysis.extraction.model_version,
        )
        db.add(extraction)
        db.flush()
        db.refresh(extraction)
        db.commit()
        return extraction
    except Exception:
        # Discard pending extraction/type changes and recover an inactive session
        # before persisting the failure state in a separate transaction.
        db.rollback()
        try:
            db.execute(
                update(Document)
                .where(Document.id == document_id, Document.status == "processing")
                .values(status="failed")
            )
            db.commit()
        except SQLAlchemyError:
            db.rollback()
            logger.exception("document_failure_status_unavailable")
        raise
