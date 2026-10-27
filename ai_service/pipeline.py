"""Điều phối pipeline; không phụ thuộc model hoặc database của backend."""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import os

from ai_service.config import MAX_IMAGE_PIXELS, OCR_MAX_ATTEMPTS, OCR_PSM_MODES, PDF_DPI

os.environ.setdefault("OPENCV_IO_MAX_IMAGE_PIXELS", str(MAX_IMAGE_PIXELS))

import cv2

from ai_service.classification.engine import build_vietnamese_classifier
from ai_service.extraction.confidence import assess_extraction
from ai_service.extraction.rules import build_vietnamese_form_engine
from ai_service.ocr.confidence import assess_confidence
from ai_service.ocr.engine import OCRResult, VietnameseOCREngine
from ai_service.ocr.postprocess import postprocess_text
from ai_service.preprocessing.document import deskew, preprocess_document
from ai_service.preprocessing.image import build_preprocessing_candidates


class PipelineError(RuntimeError):
    pass


class DocumentPipeline:
    def __init__(self, ocr_engine: VietnameseOCREngine | None = None) -> None:
        self.ocr_engine = ocr_engine or VietnameseOCREngine()
        self.classifier = build_vietnamese_classifier()
        self.extractor = build_vietnamese_form_engine()

    def _load_pages(self, path: Path):
        if path.suffix.lower() == ".pdf":
            return preprocess_document(str(path), dpi=PDF_DPI, deskew_enabled=False)
        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if image is not None and image.shape[0] * image.shape[1] > MAX_IMAGE_PIXELS:
            raise PipelineError("Ảnh vượt quá giới hạn số điểm ảnh")
        if image is None:
            raise PipelineError("Không thể giải mã ảnh")
        return [image]

    def process(self, path: str | Path) -> dict:
        try:
            source_pages = self._load_pages(Path(path))
            page_results = []
            for page_number, source_page in enumerate(source_pages, start=1):
                corrected = deskew(source_page)
                candidates = build_preprocessing_candidates(corrected)
                page_results.append(
                    self.ocr_engine.recognize_candidates(
                        candidates,
                        page_number=page_number,
                        psm_modes=OCR_PSM_MODES,
                        max_attempts=OCR_MAX_ATTEMPTS,
                    )
                )
        except PipelineError:
            raise
        except Exception as exc:
            raise PipelineError("Tiền xử lý hoặc OCR thất bại") from exc
        words = [word for result in page_results for word in result.words]
        raw_text = "\n\f\n".join(result.text for result in page_results)
        analysis_text = postprocess_text(raw_text, fix_errors=False)
        structured_pages = [page for result in page_results for page in result.pages]
        combined_ocr = OCRResult(
            text=raw_text,
            words=words,
            engine=page_results[0].engine if page_results else self.ocr_engine.prefer,
            pages=structured_pages,
            config=", ".join(result.config for result in page_results if result.config),
        )
        classification = self.classifier.classify(analysis_text)
        extraction = self.extractor.extract(analysis_text)
        extraction.document_type = classification.document_type
        return {
            "ocr": {
                "text": raw_text,
                "engine": combined_ocr.engine,
                "mean_confidence": round(combined_ocr.mean_confidence, 2),
                "quality": assess_confidence(combined_ocr).quality,
                "config": combined_ocr.config,
                "boxes": [
                    {
                        "text": word.text,
                        "confidence": word.confidence,
                        "bbox": list(word.bbox),
                        "page_number": word.page_number,
                        "block_number": word.block_number,
                        "paragraph_number": word.paragraph_number,
                        "line_number": word.line_number,
                        "word_number": word.word_number,
                    }
                    for word in words
                ],
                "pages": structured_pages,
            },
            "classification": asdict(classification),
            "extraction": {
                "data": extraction.to_dict(),
                "assessment": assess_extraction(extraction),
            },
        }
