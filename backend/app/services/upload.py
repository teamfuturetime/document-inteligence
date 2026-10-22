"""Use case upload: validate stream, lưu file, rồi ghi metadata trong transaction."""
from fastapi import UploadFile

from app.core.config import get_settings
from app.core.logging import get_logger
from app.repositories.documents import DocumentRepository
from app.schemas.documents import DocumentCreate
from app.services.file_validation import (
    FileValidationError,
    validate_upload_metadata,
    validate_upload_signature,
)
from app.services.storage import StorageService

settings = get_settings()
logger = get_logger(__name__)


class DocumentUploadService:
    def __init__(self, repository: DocumentRepository, storage: StorageService):
        self.repository = repository
        self.storage = storage

    async def upload(self, file: UploadFile):
        filename = file.filename or "unknown"
        content_type = file.content_type or "application/octet-stream"
        validate_upload_metadata(filename, content_type)
        key: str | None = None
        try:
            try:
                key, size, header = await self.storage.save_upload(
                    file, filename, settings.max_upload_size_bytes
                )
            except ValueError as exc:
                status_code = 413 if "vượt quá" in str(exc) else 400
                raise FileValidationError(str(exc), status_code=status_code) from exc
            validate_upload_signature(filename, header)
            document = self.repository.create(
                DocumentCreate(
                    filename=filename,
                    content_type=content_type,
                    file_size=size,
                    file_path=key,
                )
            )
            self.repository.commit()
            self.repository.refresh(document)
        except Exception:
            self.repository.rollback()
            if key:
                self.storage.delete(key)
            raise
        logger.info("Document uploaded", extra={"document_id": document.id})
        return document
