"""Điều phối pipeline; không phụ thuộc model hoặc database của backend."""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import os

from ai_service.config import MAX_IMAGE_PIXELS

os.environ.setdefault("OPENCV_IO_MAX_IMAGE_PIXELS", str(MAX_IMAGE_PIXELS))

import cv2

from ai_service.classification.engine import build_vietnamese_classifier
from ai_service.extraction.confidence import assess_extraction
from ai_service.extraction.rules import build_vietnamese_form_engine
from ai_service.ocr.confidence import assess_confidence
from ai_service.ocr.engine import OCRResult, VietnameseOCREngine
from ai_service.ocr.postprocess import postprocess_text
from ai_service.preprocessing.document import preprocess_document
from ai_service.preprocessing.image import preprocess_image


class PipelineError(RuntimeError):
    pass


class DocumentPipeline:
    def __init__(self, ocr_engine: VietnameseOCREngine | None = None) -> None:
        self.ocr_engine = ocr_engine or VietnameseOCREngine()
        self.classifier = build_vietnamese_classifier()
        self.extractor = build_vietnamese_form_engine()

    def _load_pages(self, path: Path):
        if path.suffix.lower() == ".pdf":
            return preprocess_document(str(path))
        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if image is not None and image.shape[0] * image.shape[1] > MAX_IMAGE_PIXELS:
            raise PipelineError("Ảnh vượt quá giới hạn số điểm ảnh")
        if image is None:
            raise PipelineError("Không thể giải mã ảnh")
        return [image]

    def process(self, path: str | Path) -> dict:
        try:
            pages = [preprocess_image(page) for page in self._load_pages(Path(path))]
            page_results = [self.ocr_engine.recognize(page) for page in pages]
        except PipelineError:
            raise
        except Exception as exc:
            raise PipelineError("Tiền xử lý hoặc OCR thất bại") from exc
        words = [word for result in page_results for word in result.words]
        text = postprocess_text("\n\f\n".join(result.text for result in page_results))
        combined_ocr = OCRResult(
            text=text,
            words=words,
            engine=page_results[0].engine if page_results else self.ocr_engine.prefer,
        )
        classification = self.classifier.classify(text)
        extraction = self.extractor.extract(text)
        extraction.document_type = classification.document_type
        return {
            "ocr": {
                "text": text,
                "engine": combined_ocr.engine,
                "mean_confidence": round(combined_ocr.mean_confidence, 2),
                "quality": assess_confidence(combined_ocr).quality,
                "boxes": [
                    {"text": word.text, "confidence": word.confidence, "bbox": list(word.bbox)}
                    for word in words
                ],
            },
            "classification": asdict(classification),
            "extraction": {
                "data": extraction.to_dict(),
                "assessment": assess_extraction(extraction),
            },
        }
