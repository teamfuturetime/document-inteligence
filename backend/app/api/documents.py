import logging

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import require_api_key
from app.repositories.documents import DocumentRepository
from app.schemas.documents import DocumentList, DocumentRead
from app.schemas.extractions import ExtractionRead, ExtractionUpdate
from app.models import Document, Extraction
from app.services.file_validation import InvalidDocument, validate_document
from app.services.storage import LocalStorage
from app.services.processing import ProcessingConflict, process_document

router = APIRouter(prefix="/documents", tags=["documents"], dependencies=[Depends(require_api_key)])
logger = logging.getLogger(__name__)


@router.post(
    "",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a PDF, PNG or JPEG document",
    responses={
        422: {"description": "File or metadata failed validation"},
        500: {"description": "File storage is unavailable"},
        503: {"description": "Document database is unavailable"},
    },
)
def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    # FastAPI runs synchronous endpoints in a worker thread, including file
    # decoding, disk writes and the synchronous SQLAlchemy transaction.
    settings = get_settings()
    try:
        max_bytes = settings.max_upload_mb * 1024 * 1024
        content = file.file.read(max_bytes + 1)
        try:
            validated = validate_document(
                file.filename or "", content, max_bytes, content_type=file.content_type
            )
        except InvalidDocument as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        try:
            storage = LocalStorage(settings.storage_dir)
            stored = storage.save(file.filename or "", content)
        except OSError as error:
            logger.exception("document_storage_failed")
            raise HTTPException(status_code=500, detail="Không thể lưu tài liệu") from error
        try:
            return DocumentRepository(db).create(
                original_name=stored.original_name,
                stored_name=stored.stored_name,
                mime_type=validated.mime_type,
                size_bytes=stored.size_bytes,
            )
        except Exception as error:
            db.rollback()
            try:
                storage.delete(stored.stored_name)
            except OSError:
                logger.exception("document_cleanup_failed")
            if isinstance(error, SQLAlchemyError):
                logger.exception("document_database_failed")
                raise HTTPException(
                    status_code=503, detail="Không thể lưu metadata tài liệu"
                ) from error
            raise
    finally:
        file.file.close()


@router.get("", response_model=DocumentList)
def list_documents(
    q: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    document_type: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    items, total = DocumentRepository(db).search(
        query=q, status=status_filter, document_type=document_type, offset=offset, limit=limit
    )
    return DocumentList(items=items, total=total)


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(document_id: str, db: Session = Depends(get_db)):
    document = DocumentRepository(db).get(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu")
    return document


@router.get("/{document_id}/content", response_class=FileResponse)
def get_document_content(document_id: str, db: Session = Depends(get_db)):
    document = DocumentRepository(db).get(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu")
    path = LocalStorage(get_settings().storage_dir).resolve(document.stored_name)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Tệp không còn trong lưu trữ")
    return FileResponse(path, media_type=document.mime_type, filename=document.original_name, content_disposition_type="inline")


@router.post("/{document_id}/process", status_code=status.HTTP_202_ACCEPTED)
def run_processing(document_id: str, db: Session = Depends(get_db)):
    document = DocumentRepository(db).get(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu")
    if document.status == "processing":
        raise HTTPException(status_code=409, detail="Tài liệu đang được xử lý")
    if document.status == "confirmed":
        raise HTTPException(status_code=409, detail="Tài liệu đã xác nhận; hãy tải bản mới để xử lý lại")
    try:
        extraction = process_document(db, document)
    except ProcessingConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except Exception as error:
        logger.exception("document_processing_failed")
        raise HTTPException(status_code=503, detail="Không thể xử lý tài liệu") from error
    return {"document_id": document.id, "extraction_id": extraction.id, "status": document.status}


@router.get("/{document_id}/extraction", response_model=ExtractionRead)
def get_latest_extraction(document_id: str, db: Session = Depends(get_db)):
    extraction = db.scalar(
        select(Extraction)
        .where(Extraction.document_id == document_id)
        .order_by(Extraction.updated_at.desc())
        .limit(1)
    )
    if not extraction:
        raise HTTPException(status_code=404, detail="Chưa có kết quả trích xuất")
    return extraction


def _find_extraction(db: Session, document_id: str) -> Extraction:
    extraction = db.scalar(
        select(Extraction)
        .where(Extraction.document_id == document_id)
        .order_by(Extraction.updated_at.desc())
        .limit(1)
    )
    if not extraction:
        raise HTTPException(status_code=404, detail="Chưa có kết quả trích xuất")
    return extraction


@router.patch("/{document_id}/extraction", response_model=ExtractionRead)
def update_extraction(document_id: str, payload: ExtractionUpdate, db: Session = Depends(get_db)):
    extraction = _find_extraction(db, document_id)
    if extraction.confirmed:
        raise HTTPException(status_code=409, detail="Kết quả đã xác nhận")
    extraction.data = payload.data
    extraction.warnings = [warning for warning in extraction.warnings if not warning.startswith("Không tìm thấy trường:")]
    extraction.warnings += [f"Không tìm thấy trường: {name}" for name, field in payload.data.get("fields", {}).items() if field.get("value") in (None, "")]
    db.commit()
    db.refresh(extraction)
    return extraction


@router.post("/{document_id}/confirm", response_model=ExtractionRead)
def confirm_extraction(document_id: str, db: Session = Depends(get_db)):
    extraction = _find_extraction(db, document_id)
    extraction.confirmed = True
    extraction.document.status = "confirmed"
    db.commit()
    db.refresh(extraction)
    return extraction
