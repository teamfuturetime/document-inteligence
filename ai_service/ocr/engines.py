from dataclasses import dataclass
from typing import Protocol

import numpy as np
import cv2


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


class TesseractOcrEngine:
    """Local OCR adapter using the Vietnamese and English Tesseract models."""

    uses_preprocessing = False

    def __init__(self, languages: str = "vie+eng") -> None:
        try:
            import pytesseract
        except ImportError as error:
            raise RuntimeError("Cài pytesseract và Tesseract để dùng OCR local") from error
        self._pytesseract = pytesseract
        self._languages = languages

    def recognize(self, image: np.ndarray) -> list[RawOcrLine]:
        scale = min(3.0, max(1.0, 1800 / image.shape[1]))
        prepared = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        data = self._pytesseract.image_to_data(
            prepared,
            lang=self._languages,
            config="--psm 3",
            output_type=self._pytesseract.Output.DICT,
            timeout=45,
        )
        lines = _group_tesseract_lines(data)
        return [RawOcrLine(line.text, line.confidence, [[x / scale, y / scale] for x, y in line.polygon]) for line in lines]


def _group_tesseract_lines(data: dict[str, list]) -> list[RawOcrLine]:
    grouped: dict[tuple[int, int, int], list[tuple[str, float, int, int, int, int]]] = {}
    for index, raw_text in enumerate(data.get("text", [])):
        text = str(raw_text).strip()
        confidence = float(data["conf"][index])
        if not text or confidence < 0:
            continue
        key = (data["block_num"][index], data["par_num"][index], data["line_num"][index])
        grouped.setdefault(key, []).append(
            (
                text,
                confidence / 100,
                int(data["left"][index]),
                int(data["top"][index]),
                int(data["width"][index]),
                int(data["height"][index]),
            )
        )

    lines: list[RawOcrLine] = []
    segments = []
    for words in grouped.values():
        segment = []
        for word in sorted(words, key=lambda item: item[2]):
            if segment and word[2] - (segment[-1][2] + segment[-1][4]) > max(word[5], segment[-1][5]) * 2:
                segments.append(segment)
                segment = []
            segment.append(word)
        if segment:
            segments.append(segment)
    for words in segments:
        left = min(word[2] for word in words)
        top = min(word[3] for word in words)
        right = max(word[2] + word[4] for word in words)
        bottom = max(word[3] + word[5] for word in words)
        confidence = sum(word[1] for word in words) / len(words)
        polygon = [[left, top], [right, top], [right, bottom], [left, bottom]]
        lines.append(RawOcrLine(" ".join(word[0] for word in words), confidence, polygon))
    return lines


class EmptyOcrEngine:
    """Deterministic fallback for development; it never invents document text."""

    def recognize(self, image: np.ndarray) -> list[RawOcrLine]:
        return []
