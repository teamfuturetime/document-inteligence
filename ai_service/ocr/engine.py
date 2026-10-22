"""OCR tiếng Việt; Tesseract mặc định, fallback chỉ khi được bật rõ ràng."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import numpy as np

try:
    import pytesseract

    _HAS_TESSERACT = True
except ImportError:  # pragma: no cover
    _HAS_TESSERACT = False

try:
    from paddleocr import PaddleOCR

    _HAS_PADDLE = True
except ImportError:  # pragma: no cover
    _HAS_PADDLE = False


class OCRError(Exception):
    """Lỗi khi nhận dạng văn bản thất bại."""


def available_engines() -> List[str]:
    """Danh sách engine có cả thư viện Python lẫn runtime khả dụng."""
    engines: List[str] = []
    if _HAS_TESSERACT:
        try:
            pytesseract.get_tesseract_version()
            engines.append("tesseract")
        except Exception:
            pass
    if _HAS_PADDLE:
        engines.append("paddle")
    return engines


@dataclass
class OCRWord:
    """Một từ nhận dạng được kèm tọa độ và độ tin cậy."""

    text: str
    confidence: float
    bbox: tuple = field(default_factory=tuple)  # (x, y, w, h)


@dataclass
class OCRResult:
    """Kết quả OCR của một trang."""

    text: str
    words: List[OCRWord] = field(default_factory=list)
    language: str = "vie"
    engine: str = "tesseract"

    @property
    def mean_confidence(self) -> float:
        """Độ tin cậy trung bình của các từ (0-100)."""
        if not self.words:
            return 0.0
        return sum(w.confidence for w in self.words) / len(self.words)


class VietnameseOCREngine:
    """Engine OCR tiếng Việt với fallback tùy chọn."""

    def __init__(
        self,
        *,
        prefer: str = "tesseract",
        tesseract_lang: str = "vie",
        paddle_lang: str = "vi",
        allow_fallback: bool = False,
    ) -> None:
        self.tesseract_lang = tesseract_lang
        self.paddle_lang = paddle_lang
        self._paddle_engine = None
        self.prefer = prefer
        self.allow_fallback = allow_fallback

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def recognize(self, image: np.ndarray) -> OCRResult:
        """Nhận dạng văn bản tiếng Việt từ ảnh."""
        if self.prefer == "paddle":
            if _HAS_PADDLE:
                return self._recognize_paddle(image)
            if self.allow_fallback and _HAS_TESSERACT:
                return self._recognize_tesseract(image)
        elif self.prefer == "tesseract":
            if _HAS_TESSERACT:
                return self._recognize_tesseract(image)
            if self.allow_fallback and _HAS_PADDLE:
                return self._recognize_paddle(image)
        else:
            raise OCRError(f"OCR engine không được hỗ trợ: {self.prefer}")
        raise OCRError(
            f"OCR engine '{self.prefer}' không khả dụng trong runtime."
        )

    # ------------------------------------------------------------------
    # Tesseract
    # ------------------------------------------------------------------
    def _recognize_tesseract(self, image: np.ndarray) -> OCRResult:
        try:
            data = pytesseract.image_to_data(
                image,
                lang=self.tesseract_lang,
                output_type=pytesseract.Output.DICT,
                config="--oem 3 --psm 6",
            )
        except pytesseract.TesseractError as exc:
            raise OCRError(f"Tesseract lỗi: {exc}") from exc

        words: List[OCRWord] = []
        lines: List[str] = []
        current_line = ""
        prev_line_num = -1

        for i, text in enumerate(data["text"]):
            conf = float(data["conf"][i])
            line_num = int(data["line_num"][i])
            word = str(text).strip()
            if not word:
                continue
            if line_num != prev_line_num and current_line:
                lines.append(current_line.strip())
                current_line = ""
            current_line += f" {word}"
            prev_line_num = line_num
            words.append(
                OCRWord(
                    text=word,
                    confidence=conf,
                    bbox=(
                        int(data["left"][i]),
                        int(data["top"][i]),
                        int(data["width"][i]),
                        int(data["height"][i]),
                    ),
                )
            )
        if current_line:
            lines.append(current_line.strip())

        return OCRResult(text="\n".join(lines), words=words, engine="tesseract")

    # ------------------------------------------------------------------
    # PaddleOCR
    # ------------------------------------------------------------------
    def _get_paddle(self) -> "PaddleOCR":
        if self._paddle_engine is None:
            self._paddle_engine = PaddleOCR(
                lang=self.paddle_lang, use_angle_cls=True, show_log=False
            )
        return self._paddle_engine

    def _recognize_paddle(self, image: np.ndarray) -> OCRResult:
        engine = self._get_paddle()
        result = engine.ocr(image, cls=True)
        if not result or not result[0]:
            return OCRResult(text="", engine="paddle")

        words: List[OCRWord] = []
        lines: List[str] = []
        for item in result[0]:
            bbox, (text, conf) = item
            words.append(
                OCRWord(
                    text=str(text).strip(),
                    confidence=float(conf) * 100.0,
                    bbox=(
                        int(bbox[0][0]),
                        int(bbox[0][1]),
                        int(bbox[2][0] - bbox[0][0]),
                        int(bbox[2][1] - bbox[0][1]),
                    ),
                )
            )
            lines.append(str(text).strip())

        return OCRResult(text="\n".join(lines), words=words, engine="paddle")
