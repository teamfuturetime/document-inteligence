"""Phân loại loại tài liệu tiếng Việt dựa trên nội dung văn bản."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ai_service.ocr.engine import OCRResult


@dataclass
class ClassificationResult:
    """Kết quả phân loại tài liệu."""

    document_type: str
    confidence: float
    scores: Dict[str, float] = field(default_factory=dict)
    source: str = "keyword"  # "keyword" | "ml"

    @property
    def is_confident(self) -> bool:
        return self.confidence >= 70.0


@dataclass
class DocumentClass:
    """Định nghĩa một loại tài liệu với các từ khóa đặc trưng."""

    name: str
    keywords: List[str] = field(default_factory=list)
    patterns: List[str] = field(default_factory=list)
    weight: float = 1.0


class DocumentClassifier:
    """Phân loại tài liệu dựa trên từ khóa và pattern."""

    def __init__(self, classes: Optional[List[DocumentClass]] = None) -> None:
        self.classes: List[DocumentClass] = classes or []
        self._compiled: Dict[str, List[re.Pattern]] = {}

    def register(self, doc_class: DocumentClass) -> None:
        """Thêm một loại tài liệu vào bộ phân loại."""
        self.classes.append(doc_class)
        self._compiled[doc_class.name] = [
            re.compile(p, re.IGNORECASE) for p in doc_class.patterns
        ]

    def _normalize(self, text: str) -> str:
        """Chuẩn hóa văn bản để khớp từ khóa (bỏ dấu, hạ thường)."""
        import unicodedata

        normalized = unicodedata.normalize("NFD", text)
        stripped = "".join(c for c in normalized if not unicodedata.combining(c))
        return stripped.lower()

    def classify(self, text: str) -> ClassificationResult:
        """Phân loại tài liệu từ văn bản."""
        normalized = self._normalize(text)
        scores: Dict[str, float] = {}

        for doc_class in self.classes:
            score = 0.0
            for keyword in doc_class.keywords:
                keyword_norm = self._normalize(keyword)
                if keyword_norm in normalized:
                    score += doc_class.weight
            for pattern in self._compiled.get(doc_class.name, []):
                if pattern.search(text):
                    score += doc_class.weight * 1.5
            scores[doc_class.name] = score

        if not scores or max(scores.values()) <= 0:
            return ClassificationResult(
                document_type="unknown",
                confidence=0.0,
                scores=scores,
            )

        best_type = max(scores, key=scores.get)
        best_score = scores[best_type]
        total = sum(scores.values()) or 1.0
        confidence = (best_score / total) * 100.0
        return ClassificationResult(
            document_type=best_type,
            confidence=round(min(confidence, 99.0), 2),
            scores=scores,
        )

    def classify_from_ocr(self, ocr_result: OCRResult) -> ClassificationResult:
        """Phân loại từ kết quả OCR."""
        return self.classify(ocr_result.text)


def build_vietnamese_classifier() -> DocumentClassifier:
    """Tạo bộ phân loại cho các loại tài liệu tiếng Việt phổ biến."""
    classifier = DocumentClassifier()
    classifier.register(
        DocumentClass(
            name="cccd",
            keywords=["can cuoc", "căn cước", "cccd", "chip", "quoc gia", "quốc gia"],
            patterns=[r"Số[:\s]*[0-9]{12}", r"Ngày cấp", r"Nơi cấp"],
        )
    )
    classifier.register(
        DocumentClass(
            name="cmnd",
            keywords=["chung minh nhan dan", "chứng minh nhân dân", "cmnd"],
            patterns=[r"Số[:\s]*[0-9]{9}"],
        )
    )
    classifier.register(
        DocumentClass(
            name="hop_dong_lao_dong",
            keywords=["hop dong lao dong", "hợp đồng lao động", "hđld"],
            patterns=[r"Hợp đồng lao động", r"Nghĩa vụ", r"Quyền lợi"],
        )
    )
    classifier.register(
        DocumentClass(
            name="don_xin_viec",
            keywords=["doc don", "đơn xin việc", "kinh gui", "kính gửi"],
            patterns=[r"Đơn xin việc", r"Kính gửi"],
        )
    )
    classifier.register(
        DocumentClass(
            name="ho_khau",
            keywords=["ho khau", "hộ khẩu", "so ho khau", "sổ hộ khẩu"],
            patterns=[r"Sổ hộ khẩu", r"Chủ hộ"],
        )
    )
    return classifier