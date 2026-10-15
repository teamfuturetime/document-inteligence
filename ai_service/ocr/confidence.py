"""Đánh giá độ tin cậy kết quả OCR để quyết định có cần xử lý lại hay không."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ai_service.ocr.engine import OCRResult, OCRWord
from ai_service.ocr.postprocess import is_valid_word

# Ngưỡng chất lượng
HIGH_CONFIDENCE = 80.0
LOW_CONFIDENCE = 50.0


@dataclass
class ConfidenceReport:
    """Báo cáo độ tin cậy của một kết quả OCR."""

    mean_confidence: float
    low_confidence_ratio: float
    word_count: int
    quality: str  # "high" | "medium" | "low"

    @property
    def needs_review(self) -> bool:
        """Cần con người rà soát nếu chất lượng thấp."""
        return self.quality == "low"


def word_confidence(word: OCRWord) -> float:
    """Độ tin cậy của một từ, giới hạn trong [0, 100]."""
    return max(0.0, min(100.0, word.confidence))


def low_confidence_words(words: List[OCRWord], threshold: float = LOW_CONFIDENCE) -> List[OCRWord]:
    """Các từ có độ tin cậy dưới ngưỡng."""
    return [w for w in words if word_confidence(w) < threshold]


def assess_confidence(result: OCRResult) -> ConfidenceReport:
    """Đánh giá chất lượng tổng thể của kết quả OCR."""
    words = [w for w in result.words if is_valid_word(w.text)]
    if not words:
        return ConfidenceReport(
            mean_confidence=0.0,
            low_confidence_ratio=1.0,
            word_count=0,
            quality="low",
        )

    confidences = [word_confidence(w) for w in words]
    mean = sum(confidences) / len(confidences)
    low_ratio = sum(1 for c in confidences if c < LOW_CONFIDENCE) / len(confidences)

    if mean >= HIGH_CONFIDENCE and low_ratio <= 0.1:
        quality = "high"
    elif mean >= LOW_CONFIDENCE:
        quality = "medium"
    else:
        quality = "low"

    return ConfidenceReport(
        mean_confidence=round(mean, 2),
        low_confidence_ratio=round(low_ratio, 4),
        word_count=len(words),
        quality=quality,
    )


def should_reprocess(result: OCRResult, threshold: float = LOW_CONFIDENCE) -> bool:
    """Quyết định có nên chạy lại OCR với engine khác không."""
    report = assess_confidence(result)
    return report.needs_review or report.mean_confidence < threshold
