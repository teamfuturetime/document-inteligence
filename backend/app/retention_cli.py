"""Chạy định kỳ: ``python -m app.retention_cli`` (cron/Task Scheduler)."""
from app.core.database import SessionLocal
from app.repositories.documents import DocumentRepository
from app.services.retention import RetentionService
from app.services.storage import StorageService


def main() -> int:
    with SessionLocal() as session:
        result = RetentionService(DocumentRepository(session), StorageService()).cleanup()
    print(
        f"deleted_records={result.deleted_records} "
        f"deleted_files={result.deleted_files} file_errors={result.file_errors}"
    )
    return 1 if result.file_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
