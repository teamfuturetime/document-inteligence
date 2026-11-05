from dataclasses import dataclass

import numpy as np

from ai_service.classification import Classification, classify_document
from ai_service.extraction import ExtractionResult, extract_fields
from ai_service.ocr import OcrService
from ai_service.extraction.layout import invoice_fields


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
        if classification.document_type == "invoice":
            extraction.fields = invoice_fields(ocr_pages)
            extraction.warnings = [f"Không tìm thấy trường: {name}" for name, field in extraction.fields.items() if field.value is None]
        else:
            for field in extraction.fields.values():
                matches = [line.confidence for page in ocr_pages for line in page.lines
                           if field.source_text and field.source_text.strip() in line.text]
                field.confidence = min(matches) if matches else 0
        extraction.raw_text = text
        extraction.model_version = "layout-rules-v2"
        extraction.pages = [{"page_number": page.page_number, "width": page.width, "height": page.height,
                             "lines": [{"text": line.text, "confidence": line.confidence, "box": line.box}
                                       for line in page.lines]} for page in ocr_pages]
        if classification.document_type == "unknown" and text.strip():
            extraction.warnings.append("Chưa hỗ trợ trích xuất loại tài liệu này. Bạn có thể xem văn bản OCR bên dưới.")
        if not text.strip():
            extraction.warnings.append("OCR không trả về văn bản; cần kiểm tra thủ công")
        return DocumentAnalysis(classification, extraction, ocr_pages)
