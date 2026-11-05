from sqlalchemy.orm import Session

from ai_service.main import DocumentIntelligence
from ai_service.ocr.engines import EmptyOcrEngine, PaddleOcrEngine, TesseractOcrEngine
from ai_service.ocr.service import OcrService
from ai_service.preprocessing import load_pages
from app.core.config import get_settings
from app.models import Document, Extraction
from app.services.storage import LocalStorage


def process_document(db: Session, document: Document) -> Extraction:
    settings = get_settings()
    document.status = "processing"
    db.commit()
    try:
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
        db.commit()
        db.refresh(extraction)
        return extraction
    except Exception:
        document.status = "failed"
        db.commit()
        raise
