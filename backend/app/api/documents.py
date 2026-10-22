"""HTTP adapter cho document use cases; không chứa truy vấn DB trực tiếp."""
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from app.api.dependencies import get_document_service, get_repository, get_storage
from app.repositories.documents import DocumentRepository
from app.schemas.documents import DocumentList, DocumentOut, ExtractionOut, ExtractionUpdate, MessageOut
from app.services.documents import DocumentNotFoundError, DocumentService, ExtractionNotFoundError, ProcessingError
from app.services.file_validation import FileValidationError
from app.services.storage import StorageService
from app.services.upload import DocumentUploadService

router = APIRouter(prefix="/documents", tags=["documents"])


def _not_found(exc: LookupError) -> HTTPException:
    noun = "Kết quả trích xuất" if isinstance(exc, ExtractionNotFoundError) else "Tài liệu"
    return HTTPException(status_code=404, detail=f"{noun} không tồn tại")


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: Annotated[UploadFile, File(...)],
    repository: DocumentRepository = Depends(get_repository),
    storage: StorageService = Depends(get_storage),
):
    try:
        return await DocumentUploadService(repository, storage).upload(file)
    except FileValidationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("", response_model=DocumentList)
def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    search: str | None = None,
    document_type: str | None = None,
    repository: DocumentRepository = Depends(get_repository),
):
    items, total = repository.list_documents(page=page, page_size=page_size, status=status_filter, search=search, document_type=document_type)
    return DocumentList(items=items, total=total, page=page, page_size=page_size)


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: str, service: DocumentService = Depends(get_document_service)):
    try:
        return service.get(document_id)
    except DocumentNotFoundError as exc:
        raise _not_found(exc) from exc


@router.post("/{document_id}/process", response_model=ExtractionOut)
async def process_document(document_id: str, service: DocumentService = Depends(get_document_service)):
    try:
        return await service.process(document_id)
    except (DocumentNotFoundError, ExtractionNotFoundError) as exc:
        raise _not_found(exc) from exc
    except ProcessingError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/{document_id}/extraction", response_model=ExtractionOut)
def get_extraction(document_id: str, repository: DocumentRepository = Depends(get_repository)):
    if repository.get_by_id(document_id) is None:
        raise HTTPException(status_code=404, detail="Tài liệu không tồn tại")
    extraction = repository.get_extraction(document_id)
    if extraction is None:
        raise HTTPException(status_code=404, detail="Kết quả trích xuất không tồn tại")
    return extraction


@router.patch("/{document_id}/extraction", response_model=ExtractionOut)
def review_extraction(document_id: str, update: ExtractionUpdate, service: DocumentService = Depends(get_document_service)):
    try:
        return service.review(document_id, update)
    except (DocumentNotFoundError, ExtractionNotFoundError) as exc:
        raise _not_found(exc) from exc


@router.post("/{document_id}/confirm", response_model=ExtractionOut)
def confirm_document(document_id: str, service: DocumentService = Depends(get_document_service)):
    try:
        return service.confirm(document_id)
    except (DocumentNotFoundError, ExtractionNotFoundError) as exc:
        raise _not_found(exc) from exc


@router.delete("/{document_id}", response_model=MessageOut)
def delete_document(document_id: str, service: DocumentService = Depends(get_document_service)):
    try:
        service.delete(document_id)
    except DocumentNotFoundError as exc:
        raise _not_found(exc) from exc
    return MessageOut(message="Đã xóa tài liệu")
