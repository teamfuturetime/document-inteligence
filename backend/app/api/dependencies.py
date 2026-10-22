from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.documents import DocumentRepository
from app.services.documents import DocumentService
from app.services.storage import StorageService


def get_repository(db: Session = Depends(get_db)) -> DocumentRepository:
    return DocumentRepository(db)


def get_storage() -> StorageService:
    return StorageService()


def get_document_service(
    repository: DocumentRepository = Depends(get_repository),
    storage: StorageService = Depends(get_storage),
) -> DocumentService:
    return DocumentService(repository, storage)
