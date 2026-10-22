"""Quy tắc phát hiện loại tài liệu kết hợp keyword + pattern đặc thù."""
from __future__ import annotations

import re
from typing import Dict, List, Tuple

from ai_service.classification.engine import (
    ClassificationResult,
    DocumentClassifier,
    build_vietnamese_classifier,
)


# Regex đặc thù từng loại tài liệu (độ ưu tiên cao)
_SPECIFIC_PATTERNS: Dict[str, List[str]] = {
    "cccd": [
        r"Số\n?[:\s]*\d{12}",
        r"Căn cước công dân gắn chip",
        r"Quốc hiệu",
        r"Ngày sinh",
        r"Quê quán",
        r"Nơi thường trú",
        r"Có giá trị đến",
    ],
    "cmnd": [
        r"Chứng minh nhân dân",
        r"Số\n?[:\s]*\d{9}",
        r"Dân tộc",
        r"Tôn giáo",
        r"Đặc điểm nhận dạng",
    ],
    "hop_dong_lao_dong": [
        r"Bên A",
        r"Bên B",
        r"hợp đồng lao động",
        r"Thời hạn hợp đồng",
        r"Tiền lương",
        r"Điều \d+",
    ],
    "don_xin_viec": [
        r"Kính gửi",
        r"Tôi tên là",
        r"Tôi viết đơn này",
        r"Xin được vào làm",
        r"Người làm đơn",
    ],
    "ho_khau": [
        r"Sổ hộ khẩu",
        r"Chủ hộ",
        r"Quan hệ với chủ hộ",
        r"Thành viên trong hộ",
    ],
}


class DocumentTypeDetector:
    """Detector kết hợp classifier từ khóa và pattern đặc thù để chốt loại tài liệu."""

    def __init__(
        self,
        classifier: DocumentClassifier | None = None,
        *,
        min_confidence: float = 50.0,
    ) -> None:
        self.classifier = classifier or build_vietnamese_classifier()
        self.min_confidence = min_confidence

    def detect(self, text: str) -> ClassificationResult:
        """Phát hiện loại tài liệu từ văn bản."""
        keyword_result = self.classifier.classify(text)

        # Đếm pattern đặc thù cho từng loại
        pattern_scores: Dict[str, float] = {}
        for doc_type, patterns in _SPECIFIC_PATTERNS.items():
            score = 0.0
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    score += 1.0
            pattern_scores[doc_type] = score

        # Kết hợp điểm: pattern đặc thù có trọng số cao hơn
        combined: Dict[str, float] = {k: v for k, v in pattern_scores.items()}
        for doc_type, score in keyword_result.scores.items():
            combined[doc_type] = combined.get(doc_type, 0.0) + score * 0.5

        if not combined or max(combined.values()) <= 0:
            return ClassificationResult(
                document_type="unknown", confidence=0.0, scores=combined
            )

        ranked = sorted(combined.items(), key=lambda item: item[1], reverse=True)
        best_type, best_score = ranked[0]
        second_score = ranked[1][1] if len(ranked) > 1 else 0.0
        margin = (best_score - second_score) / max(best_score, 1e-9)
        confidence = round(
            min(95.0, 35.0 + min(best_score, 4.0) * 12.0 + margin * 12.0), 2
        )
        ambiguous = second_score > 0 and margin < 0.30

        # Ghi đè bằng keyword nếu pattern rỗng nhưng input rõ ràng
        if best_score <= 0 and keyword_result.document_type != "unknown":
            return keyword_result

        return ClassificationResult(
            document_type=(
                best_type
                if confidence >= self.min_confidence and not ambiguous
                else "unknown"
            ),
            confidence=confidence,
            scores=combined,
            source="rule",
            raw_score=best_score,
            matched_rules=[
                f"pattern:{pattern}"
                for pattern in _SPECIFIC_PATTERNS[best_type]
                if re.search(pattern, text, re.IGNORECASE)
            ],
            needs_review=ambiguous or confidence < 70.0,
        )


def detect_document_groups(text: str) -> Tuple[str, List[str], float]:
    """Tiện ích: trả về (loại tài liệu, nhãn trùng khớp, độ tin cậy)."""
    result = DocumentTypeDetector().detect(text)
    matched = [
        doc_type
        for doc_type, score in result.scores.items()
        if score > 0
    ]
    return result.document_type, matched, result.confidence


def detect_from_ocr(ocr_text: str) -> ClassificationResult:
    """Detect loại tài liệu từ văn bản OCR (alias rút gọn)."""
    return DocumentTypeDetector().detect(ocr_text)
