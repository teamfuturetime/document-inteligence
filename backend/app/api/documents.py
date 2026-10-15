from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.repositories.documents import DocumentRepository
from app.schemas.documents import DocumentList, DocumentRead
from app.services.file_validation import InvalidDocument, validate_document
from app.services.storage import LocalStorage

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    settings = get_settings()
    content = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    try:
        validated = validate_document(file.filename or "document", content, settings.max_upload_mb * 1024 * 1024)
    except InvalidDocument as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    stored = LocalStorage(settings.storage_dir).save(file.filename or "document", content)
    return DocumentRepository(db).create(
        original_name=stored.original_name,
        stored_name=stored.stored_name,
        mime_type=validated.mime_type,
        size_bytes=stored.size_bytes,
    )


@router.get("", response_model=DocumentList)
def list_documents(
    q: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    document_type: str | None = None,
    offset: int = 0,
    limit: int = 20,
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
