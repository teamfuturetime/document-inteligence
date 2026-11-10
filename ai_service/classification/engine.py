"""Bộ phân loại tài liệu minh bạch dựa trên luật.

``confidence`` nằm trong [0, 100] và chỉ là ước lượng heuristic, không phải
xác suất đã được hiệu chuẩn trên tập dữ liệu gán nhãn.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ai_service.ocr.engine import OCRResult


@dataclass
class ClassificationResult:
    """Hợp đồng ổn định giữa classifier và pipeline."""

    document_type: str
    confidence: float
    scores: Dict[str, float] = field(default_factory=dict)
    source: str = "rule"
    raw_score: float = 0.0
    confidence_type: str = "heuristic"
    matched_rules: List[str] = field(default_factory=list)
    needs_review: bool = False

    @property
    def is_confident(self) -> bool:
        return self.document_type != "unknown" and self.confidence >= 70.0 and not self.needs_review


@dataclass
class DocumentClass:
    name: str
    keywords: List[str] = field(default_factory=list)
    patterns: List[str] = field(default_factory=list)
    weight: float = 1.0


def fold_diacritics(text: str) -> str:
    """Remove Vietnamese marks without removing regex syntax or punctuation."""
    normalized = unicodedata.normalize("NFKD", text or "")
    without_marks = "".join(char for char in normalized if not unicodedata.combining(char))
    return without_marks.replace("đ", "d").replace("Đ", "D")


def normalize_text(text: str) -> str:
    """Chuẩn hóa Unicode, bỏ dấu và nhiễu khoảng trắng của OCR."""
    return re.sub(r"[^a-z0-9]+", " ", fold_diacritics(text).casefold()).strip()


class DocumentClassifier:
    def __init__(self, classes: Optional[List[DocumentClass]] = None) -> None:
        self.classes: List[DocumentClass] = []
        self._compiled: Dict[str, List[re.Pattern[str]]] = {}
        for doc_class in classes or []:
            self.register(doc_class)

    def register(self, doc_class: DocumentClass) -> None:
        self.classes.append(doc_class)
        self._compiled[doc_class.name] = [re.compile(fold_diacritics(pattern), re.IGNORECASE | re.MULTILINE) for pattern in doc_class.patterns]

    def _normalize(self, text: str) -> str:
        return normalize_text(text)

    def classify(self, text: str) -> ClassificationResult:
        normalized = normalize_text(text)
        folded = fold_diacritics(text)
        if not normalized:
            return ClassificationResult("unknown", 0.0)

        scores: Dict[str, float] = {}
        matches: Dict[str, List[str]] = {}
        capacities: Dict[str, float] = {}
        for doc_class in self.classes:
            matched: List[str] = []
            keywords = {normalize_text(keyword) for keyword in doc_class.keywords}
            for keyword in sorted(keywords):
                if keyword and re.search(rf"\b{re.escape(keyword)}\b", normalized):
                    matched.append(f"keyword:{keyword}")
            for index, pattern in enumerate(self._compiled.get(doc_class.name, [])):
                if pattern.search(folded):
                    matched.append(f"pattern:{doc_class.patterns[index]}")
            keyword_score = sum(rule.startswith("keyword:") for rule in matched)
            pattern_score = sum(rule.startswith("pattern:") for rule in matched) * 1.5
            scores[doc_class.name] = (keyword_score + pattern_score) * doc_class.weight
            capacities[doc_class.name] = max((len(keywords) + len(doc_class.patterns) * 1.5) * doc_class.weight, 1.0)
            matches[doc_class.name] = matched

        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        if not ranked or ranked[0][1] <= 0:
            return ClassificationResult("unknown", 0.0, scores=scores)
        best_type, best_score = ranked[0]
        second_score = ranked[1][1] if len(ranked) > 1 else 0.0
        tied = second_score > 0 and abs(best_score - second_score) < 1e-9
        margin = (best_score - second_score) / max(best_score, 1e-9)
        coverage = min(best_score / capacities[best_type], 1.0)
        evidence_volume = min(best_score / 3.0, 1.0)
        confidence = min(95.0, 100.0 * (0.35 * coverage + 0.35 * max(margin, 0.0) + 0.30 * evidence_volume))
        weak = best_score < 1.0 or confidence < 50.0
        ambiguous = tied or (second_score > 0 and margin < 0.30)
        needs_review = weak or ambiguous or confidence < 70.0
        return ClassificationResult(
            document_type="unknown" if weak or tied else best_type,
            confidence=round(confidence, 2),
            scores={name: round(score, 2) for name, score in scores.items()},
            raw_score=round(best_score, 2),
            matched_rules=matches[best_type],
            needs_review=needs_review,
        )

    def classify_from_ocr(self, ocr_result: OCRResult) -> ClassificationResult:
        return self.classify(ocr_result.text)


def build_vietnamese_classifier() -> DocumentClassifier:
    classifier = DocumentClassifier()
    classifier.register(DocumentClass("cccd", ["căn cước công dân", "căn cước", "cccd", "gắn chip"], [r"\bSố(?:\s*/\s*No\.?)?[:\s]*[0-9]{12}(?!\d)", r"Ngày cấp", r"Nơi cấp"]))
    classifier.register(DocumentClass("cmnd", ["chứng minh nhân dân", "cmnd"], [r"\bSố[:\s]*[0-9]{9}(?!\d)"]))
    classifier.register(DocumentClass("hop_dong_lao_dong", ["hợp đồng lao động", "hđld"], [r"Hợp đồng lao động", r"Nghĩa vụ", r"Quyền lợi"]))
    classifier.register(DocumentClass("don_xin_viec", ["đơn xin việc"], [r"Đơn xin việc"]))
    classifier.register(DocumentClass("ho_khau", ["hộ khẩu", "sổ hộ khẩu"], [r"Sổ hộ khẩu", r"Chủ hộ"]))
    classifier.register(DocumentClass("hoa_don", ["hóa đơn giá trị gia tăng", "hóa đơn bán hàng", "hóa đơn dịch vụ", "vat invoice"], [
        r"^\s*(?:h[o0]a\s+d[o0]n|(?:VAT\s+)?invoice)\b",
        r"\b(?:s[o0]\s*(?:h[o0]a\s+d[o0]n|HD)|invoice\s*(?:no\.?|number))\s*:",
    ]))
    classifier.register(DocumentClass("application_form", ["biểu mẫu", "đơn đề nghị", "đơn xin xác nhận", "đơn đăng ký", "phiếu đăng ký", "tờ khai"], [
        r"^\s*(?:đơn\s+(?!xin\s+việc\b)[^\n]{2,80}|biểu\s+mẫu[^\n]{0,80}|tờ\s+khai[^\n]{0,80}|phiếu\s+đăng\s+ký[^\n]{0,80})$",
    ]))
    return classifier
