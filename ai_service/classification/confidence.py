"""Đánh giá độ tin cậy của kết quả phân loại tài liệu."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ai_service.classification.engine import ClassificationResult

# Ngưỡng chất lượng
HIGH_CONFIDENCE = 80.0
LOW_CONFIDENCE = 50.0


@dataclass
class ClassificationReport:
    """Báo cáo chất lượng phân loại."""

    document_type: str
    confidence: float
    quality: str  # "high" | "medium" | "low"
    is_ambiguous: bool
    note: Optional[str] = None

    @property
    def needs_review(self) -> bool:
        """Cần rà soát thủ công nếu không chắc chắn."""
        return self.quality == "low" or self.is_ambiguous


def assess_classification(result: ClassificationResult) -> ClassificationReport:
    """Đánh giá độ tin cậy của kết quả phân loại."""
    # Phát hiện mơ hồ: hai loại có điểm gần nhau
    sorted_scores = sorted(result.scores.items(), key=lambda kv: kv[1], reverse=True)
    is_ambiguous = False
    note = None

    if len(sorted_scores) >= 2:
        top, second = sorted_scores[0], sorted_scores[1]
        if top[1] > 0 and second[1] > 0:
            gap_ratio = (top[1] - second[1]) / max(top[1], 1e-9)
            if gap_ratio < 0.3:
                is_ambiguous = True
                note = f"Tài liệu giống {top[0]} và {second[0]}"

    if result.document_type == "unknown":
        quality = "low"
        note = "Không xác định được loại tài liệu"
    elif result.confidence >= HIGH_CONFIDENCE and not is_ambiguous:
        quality = "high"
    elif result.confidence >= LOW_CONFIDENCE:
        quality = "medium"
    else:
        quality = "low"

    return ClassificationReport(
        document_type=result.document_type,
        confidence=result.confidence,
        quality=quality,
        is_ambiguous=is_ambiguous,
        note=note,
    )


def is_classified(result: ClassificationResult) -> bool:
    """Kiểm tra tài liệu đã được phân loại thành công chưa."""
    return result.document_type != "unknown" and result.confidence >= LOW_CONFIDENCE