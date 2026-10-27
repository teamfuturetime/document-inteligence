"""HTTP adapter for authenticated document workflows."""
from typing import Annotated
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse
from app.api.dependencies import get_document_service, get_repository, get_storage
from app.api.security import get_current_user
from app.models import User
from app.repositories.documents import DocumentRepository
from app.schemas.documents import DashboardOut, DocumentDetailOut, DocumentList, DocumentOut, ExtractionOut, ExtractionUpdate, MessageOut, OCRCorrectionUpdate
from app.services.documents import DocumentNotFoundError, DocumentService, ExtractionNotFoundError, InvalidStateError, ProcessingError, ReviewPersistenceError
from app.services.file_validation import FileValidationError
from app.services.ocr_text import clean_ocr_text
from app.services.storage import StorageService
from app.services.upload import DocumentUploadService

router = APIRouter(prefix="/documents", tags=["documents"])

def _not_found(exc: LookupError) -> HTTPException:
    noun = "Kết quả trích xuất" if isinstance(exc, ExtractionNotFoundError) else "Tài liệu"
    return HTTPException(404, f"{noun} không tồn tại")

@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(file: Annotated[UploadFile, File(...)], repository: DocumentRepository = Depends(get_repository), storage: StorageService = Depends(get_storage), user: User = Depends(get_current_user)):
    try:
        return await DocumentUploadService(repository, storage).upload(file, user.id)
    except FileValidationError as exc:
        raise HTTPException(exc.status_code, exc.message) from exc

@router.get("", response_model=DocumentList)
def list_documents(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), status_filter: str | None = Query(None, alias="status"), search: str | None = None, document_type: str | None = None, repository: DocumentRepository = Depends(get_repository), user: User = Depends(get_current_user)):
    items, total = repository.list_documents(page=page, page_size=page_size, status=status_filter, search=search, document_type=document_type, owner_id=user.id)
    return DocumentList(items=items, total=total, page=page, page_size=page_size)

@router.get("/dashboard/summary", response_model=DashboardOut)
def dashboard(repository: DocumentRepository = Depends(get_repository), user: User = Depends(get_current_user)):
    recent, total = repository.list_documents(page=1, page_size=5, owner_id=user.id)
    _, processed = repository.list_documents(status="processed", page_size=1, owner_id=user.id)
    _, reviewed = repository.list_documents(status="reviewed", page_size=1, owner_id=user.id)
    _, confirmed = repository.list_documents(status="confirmed", page_size=1, owner_id=user.id)
    return DashboardOut(total=total, processed=processed + reviewed + confirmed, awaiting_review=processed + reviewed, confirmed=confirmed, recent=recent)

@router.get("/{document_id}", response_model=DocumentDetailOut)
def get_document(document_id: str, service: DocumentService = Depends(get_document_service)):
    try: return service.get(document_id)
    except DocumentNotFoundError as exc: raise _not_found(exc) from exc

@router.post("/{document_id}/process", response_model=ExtractionOut)
async def process_document(document_id: str, service: DocumentService = Depends(get_document_service)):
    try: return await service.process(document_id)
    except (DocumentNotFoundError, ExtractionNotFoundError) as exc: raise _not_found(exc) from exc
    except InvalidStateError as exc: raise HTTPException(409, str(exc)) from exc
    except ProcessingError as exc: raise HTTPException(502, str(exc)) from exc

@router.get("/{document_id}/extraction", response_model=ExtractionOut)
def get_extraction(document_id: str, repository: DocumentRepository = Depends(get_repository), user: User = Depends(get_current_user)):
    if repository.get_by_id(document_id, user.id) is None: raise HTTPException(404, "Tài liệu không tồn tại")
    extraction = repository.get_extraction(document_id, user.id)
    if extraction is None: raise HTTPException(404, "Kết quả trích xuất không tồn tại")
    return extraction

@router.patch("/{document_id}/extraction", response_model=ExtractionOut)
def review_extraction(document_id: str, update: ExtractionUpdate, service: DocumentService = Depends(get_document_service)):
    try: return service.review(document_id, update)
    except (DocumentNotFoundError, ExtractionNotFoundError) as exc: raise _not_found(exc) from exc
    except InvalidStateError as exc: raise HTTPException(409, str(exc)) from exc
    except ReviewPersistenceError as exc: raise HTTPException(500, str(exc)) from exc

@router.patch("/{document_id}/ocr-correction", response_model=DocumentDetailOut)
def correct_ocr(document_id: str, update: OCRCorrectionUpdate, service: DocumentService = Depends(get_document_service)):
    try: return service.correct_ocr(document_id, update)
    except DocumentNotFoundError as exc: raise _not_found(exc) from exc
    except InvalidStateError as exc: raise HTTPException(409, str(exc)) from exc
    except ReviewPersistenceError as exc: raise HTTPException(500, str(exc)) from exc

@router.post("/{document_id}/confirm", response_model=ExtractionOut)
def confirm_document(document_id: str, service: DocumentService = Depends(get_document_service)):
    try: return service.confirm(document_id)
    except (DocumentNotFoundError, ExtractionNotFoundError) as exc: raise _not_found(exc) from exc
    except InvalidStateError as exc: raise HTTPException(409, str(exc)) from exc
    except ReviewPersistenceError as exc: raise HTTPException(500, str(exc)) from exc

@router.post("/{document_id}/reopen", response_model=ExtractionOut)
def reopen_document(document_id: str, service: DocumentService = Depends(get_document_service)):
    try: return service.reopen(document_id)
    except (DocumentNotFoundError, ExtractionNotFoundError) as exc: raise _not_found(exc) from exc
    except InvalidStateError as exc: raise HTTPException(409, str(exc)) from exc
    except ReviewPersistenceError as exc: raise HTTPException(500, str(exc)) from exc

@router.get("/{document_id}/preview")
def preview_document(document_id: str, service: DocumentService = Depends(get_document_service)):
    try:
        document = service.get(document_id)
    except DocumentNotFoundError as exc:
        raise _not_found(exc) from exc
    path = service.storage.path_for(document.file_path)
    if not path.exists(): raise HTTPException(404, "File tài liệu không tồn tại")
    return FileResponse(path, media_type=document.content_type, filename=document.filename, content_disposition_type="inline", headers={"Cache-Control": "private, no-store"})

@router.get("/{document_id}/export")
def export_document(document_id: str, service: DocumentService = Depends(get_document_service)):
    try:
        document = service.get(document_id)
    except DocumentNotFoundError as exc:
        raise _not_found(exc) from exc
    extraction = service.repository.get_extraction(document_id, service.owner_id)
    if extraction is None: raise HTTPException(404, "Kết quả trích xuất không tồn tại")
    payload = {
        "document_id": document.id,
        "filename": document.filename,
        "document_type": extraction.document_type,
        "ai_document_type": extraction.ai_document_type or extraction.document_type,
        "reviewed_document_type": extraction.reviewed_document_type,
        "fields": extraction.data,
        "ocr_text": document.ocr_text_corrected or clean_ocr_text(document.ocr_text),
        "ocr_text_raw": document.ocr_text,
        "ocr_is_corrected": document.ocr_text_corrected is not None,
        "document_status": document.status,
        "review_status": extraction.status,
        "confidence": extraction.confidence,
        "classification": extraction.classification_metadata,
        "created_at": document.created_at.isoformat(),
        "confirmed_at": extraction.confirmed_at.isoformat() if extraction.confirmed_at else None,
    }
    return JSONResponse(payload, headers={"Content-Disposition": f'attachment; filename="document-{document.id}.json"', "Cache-Control": "private, no-store"})

@router.delete("/{document_id}", response_model=MessageOut)
def delete_document(document_id: str, service: DocumentService = Depends(get_document_service)):
    try: service.delete(document_id)
    except DocumentNotFoundError as exc: raise _not_found(exc) from exc
    return MessageOut(message="Đã xóa tài liệu")
