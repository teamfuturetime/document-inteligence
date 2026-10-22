"""Dọn dữ liệu hết hạn, có thể gọi lặp lại an toàn."""
from dataclasses import dataclass

from app.core.logging import get_logger
from app.repositories.documents import DocumentRepository
from app.services.storage import StorageService

logger = get_logger(__name__)


@dataclass
class CleanupResult:
    deleted_records: int = 0
    deleted_files: int = 0
    file_errors: int = 0


class RetentionService:
    def __init__(self, repository: DocumentRepository, storage: StorageService):
        self.repository = repository
        self.storage = storage

    def cleanup(self) -> CleanupResult:
        result = CleanupResult()
        for document in self.repository.expired():
            key = document.file_path
            try:
                if self.storage.delete(key):
                    result.deleted_files += 1
            except (OSError, ValueError):
                result.file_errors += 1
                self.repository.rollback()
                continue
            self.repository.delete(document)
            self.repository.commit()
            result.deleted_records += 1
        logger.info(
            "Retention cleanup completed",
            extra={
                "deleted_records": result.deleted_records,
                "deleted_files": result.deleted_files,
                "file_errors": result.file_errors,
            },
        )
        return result
