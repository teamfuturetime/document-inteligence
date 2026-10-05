from pathlib import Path
from typing import Protocol

from docintel.domain.models import ExtractionRun, OCRResult


class OCRAdapter(Protocol):
    def recognize(self, image_path: Path) -> OCRResult: ...


class ExtractionAdapter(Protocol):
    def extract(self, document_id: str, ocr: OCRResult) -> ExtractionRun: ...
