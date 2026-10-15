from dataclasses import dataclass

import numpy as np

from ai_service.classification import Classification, classify_document
from ai_service.extraction import ExtractionResult, extract_fields
from ai_service.ocr import OcrService


@dataclass(frozen=True)
class DocumentAnalysis:
    classification: Classification
    extraction: ExtractionResult
    pages: list


class DocumentIntelligence:
    """Coordinates OCR and rule-based understanding behind a replaceable interface."""

    def __init__(self, ocr_service: OcrService):
        self.ocr_service = ocr_service

    def analyze(self, pages: list[np.ndarray]) -> DocumentAnalysis:
        ocr_pages = self.ocr_service.process_pages(pages)
        text = "\n".join(page.text for page in ocr_pages)
        classification = classify_document(text)
        extraction = extract_fields(text, classification.document_type)
        if not text.strip():
            extraction.warnings.append("OCR không trả về văn bản; cần kiểm tra thủ công")
        return DocumentAnalysis(classification, extraction, ocr_pages)
