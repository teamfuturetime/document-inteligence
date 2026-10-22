"""Các use case tài liệu; đây là nơi sở hữu transaction của ứng dụng."""
from __future__ import annotations

import httpx
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.core.logging import get_logger
from app.repositories.documents import DocumentRepository
from app.schemas.documents import ExtractionUpdate
from app.services.storage import StorageService

settings = get_settings()
logger = get_logger(__name__)


class DocumentNotFoundError(LookupError):
    pass


class ExtractionNotFoundError(LookupError):
    pass


class ProcessingError(RuntimeError):
    pass


class DocumentService:
    def __init__(self, repository: DocumentRepository, storage: StorageService):
        self.repository = repository
        self.storage = storage

    def get(self, document_id: str):
        document = self.repository.get_by_id(document_id)
        if document is None:
            raise DocumentNotFoundError(document_id)
        return document

    async def process(self, document_id: str):
        document = self.get(document_id)
        self.repository.update_status(document_id, "processing")
        self.repository.commit()
        logger.info("Processing started", extra={"document_id": document_id})
        try:
            path = self.storage.path_for(document.file_path)
            async with httpx.AsyncClient(timeout=settings.AI_SERVICE_TIMEOUT_SECONDS) as client:
                with path.open("rb") as stream:
                    response = await client.post(
                        f"{settings.AI_SERVICE_URL.rstrip('/')}/process",
                        files={"file": (document.filename, stream, document.content_type)},
                    )
            response.raise_for_status()
            result = response.json()
            classification = result["classification"]
            extraction = result["extraction"]
            ocr = result["ocr"]
            self.repository.save_ocr_result(document_id, ocr.get("text", ""), ocr.get("boxes", []))
            saved = self.repository.save_extraction(
                document_id,
                classification["document_type"],
                extraction.get("data", {}),
                float(classification.get("confidence", 0.0)) / 100.0,
            )
            self.repository.update_status(document_id, "processed")
            self.repository.commit()
            self.repository.refresh(saved)
            logger.info("Processing completed", extra={"document_id": document_id})
            return saved
        except (httpx.HTTPError, KeyError, ValueError, OSError, SQLAlchemyError) as exc:
            self.repository.rollback()
            self.repository.update_status(document_id, "failed")
            self.repository.commit()
            logger.error("Processing failed", extra={"document_id": document_id}, exc_info=exc)
            raise ProcessingError("AI service không thể xử lý tài liệu") from exc

    def review(self, document_id: str, update: ExtractionUpdate):
        self.get(document_id)
        extraction = self.repository.review_extraction(document_id, update.data, update.document_type)
        if extraction is None:
            raise ExtractionNotFoundError(document_id)
        self.repository.update_status(document_id, "reviewed")
        self.repository.commit()
        self.repository.refresh(extraction)
        return extraction

    def confirm(self, document_id: str):
        self.get(document_id)
        extraction = self.repository.confirm_extraction(document_id)
        if extraction is None:
            raise ExtractionNotFoundError(document_id)
        self.repository.update_status(document_id, "confirmed")
        self.repository.commit()
        self.repository.refresh(extraction)
        logger.info("Document confirmed", extra={"document_id": document_id})
        return extraction

    def delete(self, document_id: str) -> None:
        document = self.get(document_id)
        storage_key = document.file_path
        self.repository.delete(document)
        self.repository.commit()
        try:
            self.storage.delete(storage_key)
        except OSError as exc:
            logger.error("File cleanup failed", extra={"document_id": document_id}, exc_info=exc)
        logger.info("Document deleted", extra={"document_id": document_id})
