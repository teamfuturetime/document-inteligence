"""Các use case tài liệu; đây là nơi sở hữu transaction của ứng dụng."""
from __future__ import annotations

import httpx
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.core.logging import get_logger
from app.repositories.documents import DocumentRepository
from app.schemas.documents import DocumentDetailOut, ExtractionUpdate, OCRCorrectionUpdate
from app.services.storage import StorageService

settings = get_settings()
logger = get_logger(__name__)


class DocumentNotFoundError(LookupError):
    pass


class ExtractionNotFoundError(LookupError):
    pass


class ProcessingError(RuntimeError):
    pass


class InvalidStateError(RuntimeError):
    pass


class ReviewPersistenceError(RuntimeError):
    pass


class DocumentService:
    def __init__(self, repository: DocumentRepository, storage: StorageService, owner_id: str | None = None):
        self.repository = repository
        self.storage = storage
        self.owner_id = owner_id

    def get(self, document_id: str):
        document = self.repository.get_by_id(document_id, self.owner_id)
        if document is None:
            raise DocumentNotFoundError(document_id)
        return document

    async def process(self, document_id: str):
        document = self.get(document_id)
        if document.status == "processing":
            raise InvalidStateError("Tài liệu đang được xử lý")
        if document.status == "confirmed":
            raise InvalidStateError("Tài liệu đã được xác nhận")
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
            # Keep raw OCR text untouched. Structured pages use the existing JSON
            # column, avoiding a migration and retaining legacy word boxes as fallback.
            structure = ocr.get("pages") or ocr.get("boxes", [])
            self.repository.save_ocr_result(document_id, ocr.get("text", ""), structure)
            saved = self.repository.save_extraction(
                document_id,
                classification["document_type"],
                extraction.get("data", {}),
                float(classification.get("confidence", 0.0)) / 100.0,
                {"confidence_type": classification.get("confidence_type", "heuristic"), "matched_rules": classification.get("matched_rules", []), "needs_review": classification.get("needs_review", True)},
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
        document = self.get(document_id)
        if document.status not in {"processed", "reviewed"}:
            raise InvalidStateError("Chỉ có thể rà soát tài liệu đã xử lý")
        try:
            extraction = self.repository.review_extraction(document_id, update.data, update.document_type)
            self.repository.update_status(document_id, "reviewed")
            self.repository.commit()
            self.repository.refresh(extraction)
            return extraction
        except SQLAlchemyError as exc:
            self.repository.rollback()
            raise ReviewPersistenceError("Không thể lưu dữ liệu rà soát") from exc

    def correct_ocr(self, document_id: str, update: OCRCorrectionUpdate):
        try:
            saved = self.repository.save_ocr_correction(
                document_id, update.text, update.expected_revision, self.owner_id
            )
            if saved is None:
                # A zero-row update may mean stale revision, a changed status,
                # missing OCR, or a missing/foreign document. Preserve ownership
                # semantics without disclosing another user's revision.
                document = self.get(document_id)
                if document.status not in {"processed", "reviewed"}:
                    raise InvalidStateError("Chỉ có thể sửa OCR của tài liệu đang rà soát")
                if not document.ocr_text:
                    raise InvalidStateError("Tài liệu chưa có kết quả OCR để chỉnh sửa")
                raise InvalidStateError("Xung đột phiên bản OCR. Hãy tải lại tài liệu trước khi lưu lại.")
            # Capture exactly this write before releasing the transaction lock.
            # A post-commit refresh could acknowledge a later client's content.
            response = DocumentDetailOut.model_validate(saved)
            self.repository.commit()
            return response
        except SQLAlchemyError as exc:
            self.repository.rollback()
            raise ReviewPersistenceError("Không thể lưu văn bản OCR chỉnh sửa") from exc

    def confirm(self, document_id: str):
        document = self.get(document_id)
        if document.status not in {"processed", "reviewed"}:
            raise InvalidStateError("Chỉ có thể xác nhận tài liệu đã xử lý")
        try:
            extraction = self.repository.confirm_extraction(document_id)
            if extraction is None:
                raise ExtractionNotFoundError(document_id)
            self.repository.update_status(document_id, "confirmed")
            self.repository.commit()
            self.repository.refresh(extraction)
            logger.info("Document confirmed", extra={"document_id": document_id})
            return extraction
        except SQLAlchemyError as exc:
            self.repository.rollback()
            raise ReviewPersistenceError("Không thể xác nhận kết quả rà soát") from exc

    def reopen(self, document_id: str):
        document = self.get(document_id)
        if document.status != "confirmed":
            raise InvalidStateError("Chỉ có thể mở lại tài liệu đã xác nhận")
        try:
            extraction = self.repository.reopen_extraction(document_id)
            if extraction is None:
                raise ExtractionNotFoundError(document_id)
            self.repository.update_status(document_id, "reviewed")
            self.repository.commit()
            self.repository.refresh(extraction)
            return extraction
        except SQLAlchemyError as exc:
            self.repository.rollback()
            raise ReviewPersistenceError("Không thể mở lại phiên rà soát") from exc

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
