"""Engine trích xuất trường dữ liệu từ văn bản OCR."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Pattern

from ai_service.ocr.engine import OCRResult


@dataclass
class ExtractedField:
    """Một trường dữ liệu được trích xuất."""

    name: str
    value: str
    confidence: float = 0.0
    source: str = "regex"  # "regex" | "rule" | "llm"
    matched_pattern: Optional[str] = None


@dataclass
class ExtractionResult:
    """Kết quả trích xuất của một tài liệu."""

    fields: List[ExtractedField] = field(default_factory=list)
    document_type: str = "unknown"

    def get(self, name: str) -> Optional[ExtractedField]:
        """Lấy trường theo tên."""
        for f in self.fields:
            if f.name == name:
                return f
        return None

    def to_dict(self) -> Dict[str, str]:
        """Chuyển thành dict name → value."""
        return {f.name: f.value for f in self.fields}


@dataclass
class FieldPattern:
    """Định nghĩa một trường với pattern regex."""

    name: str
    pattern: Pattern
    group: int = 1
    confidence: float = 90.0
    required: bool = False


class ExtractionEngine:
    """Trích xuất trường dữ liệu dựa trên danh sách pattern."""

    def __init__(self, patterns: Optional[List[FieldPattern]] = None) -> None:
        self.patterns: List[FieldPattern] = patterns or []

    def add_pattern(self, pattern: FieldPattern) -> None:
        """Thêm một pattern trích xuất."""
        self.patterns.append(pattern)

    def extract(self, text: str) -> ExtractionResult:
        """Trích xuất tất cả trường khớp pattern từ văn bản."""
        result = ExtractionResult()
        for pattern in self.patterns:
            match = pattern.pattern.search(text)
            if match:
                value = match.group(pattern.group).strip()
                if value:
                    result.fields.append(
                        ExtractedField(
                            name=pattern.name,
                            value=value,
                            confidence=pattern.confidence,
                            matched_pattern=pattern.pattern.pattern,
                        )
                    )
        return result

    def extract_from_ocr(self, ocr_result: OCRResult) -> ExtractionResult:
        """Trích xuất từ kết quả OCR."""
        return self.extract(ocr_result.text)
