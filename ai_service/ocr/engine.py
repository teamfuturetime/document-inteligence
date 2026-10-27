"""OCR tiếng Việt; Tesseract mặc định, fallback chỉ khi được bật rõ ràng."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Sequence

import numpy as np

from ai_service.ocr.layout import build_page_structure, render_page_text

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


def available_tesseract_languages() -> List[str]:
    """Return installed language packs without making health checks fail."""

    if not _HAS_TESSERACT:
        return []
    try:
        return sorted(pytesseract.get_languages(config=""))
    except Exception:
        return []


@dataclass
class OCRWord:
    """Một từ nhận dạng được kèm tọa độ và độ tin cậy."""

    text: str
    confidence: float
    bbox: tuple = field(default_factory=tuple)  # (x, y, w, h)
    page_number: int = 1
    block_number: int = 1
    paragraph_number: int = 1
    line_number: int = 1
    word_number: int = 1


@dataclass
class OCRResult:
    """Kết quả OCR của một trang."""

    text: str
    words: List[OCRWord] = field(default_factory=list)
    language: str = "vie"
    engine: str = "tesseract"
    pages: list[dict] = field(default_factory=list)
    config: str = ""

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
    def recognize(self, image: np.ndarray, *, page_number: int = 1, psm: int = 3) -> OCRResult:
        """Nhận dạng văn bản tiếng Việt từ ảnh."""
        if self.prefer == "paddle":
            if _HAS_PADDLE:
                return self._recognize_paddle(image, page_number=page_number)
            if self.allow_fallback and _HAS_TESSERACT:
                return self._recognize_tesseract(image, page_number=page_number, psm=psm)
        elif self.prefer == "tesseract":
            if _HAS_TESSERACT:
                return self._recognize_tesseract(image, page_number=page_number, psm=psm)
            if self.allow_fallback and _HAS_PADDLE:
                return self._recognize_paddle(image, page_number=page_number)
        else:
            raise OCRError(f"OCR engine không được hỗ trợ: {self.prefer}")
        raise OCRError(
            f"OCR engine '{self.prefer}' không khả dụng trong runtime."
        )

    def recognize_candidates(
        self,
        images: Sequence[np.ndarray],
        *,
        page_number: int = 1,
        psm_modes: Sequence[int] = (3, 4, 6, 11),
        max_attempts: int = 3,
    ) -> OCRResult:
        """Try bounded OCR variants only while measurable quality remains weak."""

        if not images:
            raise OCRError("Không có ảnh tiền xử lý để OCR")
        attempts: list[OCRResult] = []
        limit = min(max_attempts, max(len(images), 1), max(len(psm_modes), 1))
        for index in range(limit):
            image = images[min(index, len(images) - 1)]
            psm = psm_modes[min(index, len(psm_modes) - 1)]
            result = self.recognize(image, page_number=page_number, psm=psm)
            attempts.append(result)
            valid_words = [word for word in result.words if any(char.isalnum() for char in word.text)]
            low_ratio = (
                sum(word.confidence < 50 for word in valid_words) / len(valid_words)
                if valid_words
                else 1.0
            )
            if result.mean_confidence >= 80 and low_ratio <= 0.1 and len(valid_words) >= 5:
                break
        return max(attempts, key=self._quality_score)

    @staticmethod
    def _quality_score(result: OCRResult) -> float:
        valid_words = [word for word in result.words if any(char.isalnum() for char in word.text)]
        if not valid_words:
            return -100.0
        low_ratio = sum(word.confidence < 50 for word in valid_words) / len(valid_words)
        coverage = min(sum(len(word.text) for word in valid_words), 500) / 100
        return result.mean_confidence - low_ratio * 20 + coverage

    # ------------------------------------------------------------------
    # Tesseract
    # ------------------------------------------------------------------
    def _recognize_tesseract(
        self, image: np.ndarray, *, page_number: int = 1, psm: int = 3
    ) -> OCRResult:
        try:
            data = pytesseract.image_to_data(
                image,
                lang=self.tesseract_lang,
                output_type=pytesseract.Output.DICT,
                config=f"--oem 3 --psm {psm}",
            )
        except pytesseract.TesseractError as exc:
            raise OCRError(f"Tesseract lỗi: {exc}") from exc

        words: List[OCRWord] = []
        for i, text in enumerate(data["text"]):
            conf = float(data["conf"][i])
            word = str(text).strip()
            if not word:
                continue
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
                    page_number=page_number,
                    block_number=int(data["block_num"][i]),
                    paragraph_number=int(data["par_num"][i]),
                    line_number=int(data["line_num"][i]),
                    word_number=int(data["word_num"][i]),
                )
            )
        height, width = image.shape[:2]
        page = build_page_structure(words, page_number=page_number, width=width, height=height)
        return OCRResult(
            text=render_page_text(page),
            words=words,
            engine="tesseract",
            pages=[page],
            config=f"--oem 3 --psm {psm}",
        )

    # ------------------------------------------------------------------
    # PaddleOCR
    # ------------------------------------------------------------------
    def _get_paddle(self) -> "PaddleOCR":
        if self._paddle_engine is None:
            self._paddle_engine = PaddleOCR(
                lang=self.paddle_lang, use_angle_cls=True, show_log=False
            )
        return self._paddle_engine

    def _recognize_paddle(self, image: np.ndarray, *, page_number: int = 1) -> OCRResult:
        engine = self._get_paddle()
        result = engine.ocr(image, cls=True)
        if not result or not result[0]:
            return OCRResult(text="", engine="paddle")

        words: List[OCRWord] = []
        lines: List[str] = []
        for index, item in enumerate(result[0], start=1):
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
                    page_number=page_number,
                    block_number=index,
                    paragraph_number=1,
                    line_number=1,
                    word_number=1,
                )
            )
            lines.append(str(text).strip())
        height, width = image.shape[:2]
        page = build_page_structure(words, page_number=page_number, width=width, height=height)
        return OCRResult(
            text="\n".join(lines), words=words, engine="paddle", pages=[page]
        )
