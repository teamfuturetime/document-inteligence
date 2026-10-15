from dataclasses import dataclass
from typing import Protocol

import numpy as np


@dataclass(frozen=True)
class RawOcrLine:
    text: str
    confidence: float
    polygon: list[list[float]]


class OcrEngine(Protocol):
    def recognize(self, image: np.ndarray) -> list[RawOcrLine]: ...


class PaddleOcrEngine:
    """Lazy PaddleOCR adapter so the base API can run without model weights."""

    def __init__(self) -> None:
        try:
            from paddleocr import PaddleOCR
        except ImportError as error:
            raise RuntimeError("Cài paddleocr và paddlepaddle để dùng OCR production") from error
        self._ocr = PaddleOCR(use_angle_cls=True, lang="vi", show_log=False)

    def recognize(self, image: np.ndarray) -> list[RawOcrLine]:
        result = self._ocr.ocr(image, cls=True)
        lines: list[RawOcrLine] = []
        for page in result or []:
            for polygon, (text, confidence) in page or []:
                lines.append(RawOcrLine(text, float(confidence), polygon))
        return lines


class EmptyOcrEngine:
    """Deterministic fallback for development; it never invents document text."""

    def recognize(self, image: np.ndarray) -> list[RawOcrLine]:
        return []
