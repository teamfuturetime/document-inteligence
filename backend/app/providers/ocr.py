"""Small OCR-only interface; does not implement the extraction provider protocol."""

from typing import Protocol, runtime_checkable

from app.schemas.extraction import DocumentInput, ProviderIdentity
from app.schemas.ocr import OCRResult


@runtime_checkable
class OCRProvider(Protocol):
    @property
    def identity(self) -> ProviderIdentity: ...

    def recognize(self, document: DocumentInput) -> OCRResult:
        """Return observations or raise the existing ProviderError; no invoice fields."""
        ...
