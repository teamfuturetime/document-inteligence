"""Dịch vụ upload tài liệu: lưu file và tạo bản ghi metadata."""
from fastapi import UploadFile

from app.core.config import get_settings
from app.core.logging import get_logger
from app.repositories.documents import DocumentRepository
from app.schemas.documents import DocumentCreate
from app.services.file_validation import FileValidationError, validate_upload
from app.services.storage import StorageService

settings = get_settings()
logger = get_logger(__name__)


class DocumentUploadService:
    """Xử lý upload tài liệu: validate → lưu file → tạo metadata."""

    def __init__(self, repository: DocumentRepository, storage: StorageService):
        self.repository = repository
        self.storage = storage

    async def upload(self, file: UploadFile) -> dict:
        """Upload một tài liệu, trả về thông tin tài liệu đã tạo."""
        # 1. Validate loại file, kích thước, nội dung thực tế
        content = await file.read()
        validate_upload(
            filename=file.filename or "unknown",
            content=content,
            content_type=file.content_type or "",
        )

        # 2. Lưu file vào storage
        file_path = self.storage.save(file.filename or "unknown", content)

        # 3. Tạo bản ghi metadata
        doc = self.repository.create(
            DocumentCreate(
                filename=file.filename or "unknown",
                content_type=file.content_type or "application/octet-stream",
                file_size=len(content),
                file_path=file_path,
            )
        )
        logger.info(
            "Document uploaded",
            extra={"document_id": doc.id, "filename": doc.filename},
        )
        return {
            "id": doc.id,
            "filename": doc.filename,
            "content_type": doc.content_type,
            "file_size": doc.file_size,
            "status": doc.status,
            "created_at": doc.created_at.isoformat(),
        }
