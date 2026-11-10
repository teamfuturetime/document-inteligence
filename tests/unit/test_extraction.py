"""Unit tests cho trích xuất trường dữ liệu từ văn bản OCR."""
import pytest

from ai_service.extraction.confidence import (
    assess_extraction,
    validate_field,
)
from ai_service.extraction.engine import (
    ExtractedField,
    ExtractionEngine,
    ExtractionResult,
    FieldPattern,
)
from ai_service.extraction.rules import (
    build_vietnamese_form_engine,
    extract_dates,
)
from ai_service.ocr.engine import OCRResult


# ----------------------------------------------------------------------
# Engine
# ----------------------------------------------------------------------
class TestExtractionEngine:
    def test_extract_simple_pattern(self):
        import re

        engine = ExtractionEngine(
            [FieldPattern("name", re.compile(r"Họ tên:\s*(\w+)"))]
        )
        result = engine.extract("Họ tên: Nguyễn")
        assert result.get("name").value == "Nguyễn"

    def test_extract_no_match(self):
        import re

        engine = ExtractionEngine([FieldPattern("name", re.compile(r"Họ tên:\s*(\w+)"))])
        result = engine.extract("Không có thông tin")
        assert result.get("name") is None
        assert result.to_dict() == {}

    def test_extract_from_ocr(self):
        import re

        engine = ExtractionEngine(
            [FieldPattern("cccd", re.compile(r"Số:\s*([0-9]{12})"))]
        )
        ocr = OCRResult(text="Số: 079201012345")
        result = engine.extract_from_ocr(ocr)
        assert result.get("cccd").value == "079201012345"

    def test_add_pattern(self):
        import re

        engine = ExtractionEngine()
        engine.add_pattern(FieldPattern("id", re.compile(r"ID:\s*(\d+)")))
        result = engine.extract("ID: 42")
        assert result.get("id").value == "42"

    def test_to_dict(self):
        import re

        engine = ExtractionEngine(
            [
                FieldPattern("a", re.compile(r"A=(\d+)")),
                FieldPattern("b", re.compile(r"B=(\d+)")),
            ]
        )
        result = engine.extract("A=1 B=2")
        assert result.to_dict() == {"a": "1", "b": "2"}


# ----------------------------------------------------------------------
# Vietnamese form rules
# ----------------------------------------------------------------------
class TestVietnameseRules:
    @pytest.fixture()
    def engine(self):
        return build_vietnamese_form_engine()

    @pytest.fixture()
    def sample_text(self):
        return """Số: 079201012345
Họ và tên: Nguyễn Văn Nam
Ngày sinh: 15/08/1990
Giới tính: Nam
Quê quán: Hà Nội
Địa chỉ: Số 12, Đường Lê Lợi, Quận 1, TP. Hồ Chí Minh
SĐT: 0912345678
Email: nam.nguyen@example.com
"""

    def test_extract_cccd(self, engine, sample_text):
        field = engine.extract(sample_text).get("cccd")
        assert field is not None
        assert field.value == "079201012345"
        assert field.confidence_type == "not_estimated"
        assert field.source == "rule"
        assert field.matched_pattern == "so/no"

    def test_extract_birth_date(self, engine, sample_text):
        field = engine.extract(sample_text).get("birth_date")
        assert field.value == "15/08/1990"

    def test_extract_full_name(self, engine, sample_text):
        field = engine.extract(sample_text).get("full_name")
        assert "Nguyễn Văn Nam" in field.value

    def test_extract_phone(self, engine, sample_text):
        field = engine.extract(sample_text).get("phone")
        assert field.value == "0912345678"

    def test_extract_email(self, engine, sample_text):
        field = engine.extract(sample_text).get("email")
        assert field.value == "nam.nguyen@example.com"

    def test_extract_dates(self):
        dates = extract_dates("Sinh 15/08/1990, cấp 10-02-2020")
        assert dates == ["15/08/1990", "10-02-2020"]


# ----------------------------------------------------------------------
# Confidence
# ----------------------------------------------------------------------
class TestExtractionConfidence:
    def test_validate_field_valid_cccd(self):
        report = validate_field(ExtractedField("cccd", "079201012345", confidence=95))
        assert report.is_ok

    def test_validate_field_invalid_cccd(self):
        report = validate_field(ExtractedField("cccd", "123", confidence=95))
        assert not report.is_ok
        assert report.validity == "invalid"

    def test_validate_field_valid_birth_date(self):
        report = validate_field(ExtractedField("birth_date", "15/08/1990", confidence=90))
        assert report.is_ok

    def test_validate_field_invalid_date(self):
        report = validate_field(ExtractedField("birth_date", "32/13/2500", confidence=90))
        assert not report.is_ok
        assert report.reason is not None

    def test_validate_field_valid_phone(self):
        report = validate_field(ExtractedField("phone", "0912345678", confidence=90))
        assert report.is_ok

    def test_validate_field_invalid_phone(self):
        report = validate_field(ExtractedField("phone", "123456", confidence=90))
        assert not report.is_ok

    def test_validate_unknown_field_is_valid(self):
        report = validate_field(ExtractedField("note", "bất kỳ", confidence=70))
        assert report.is_ok

    def test_assess_extraction_high(self):
        result = ExtractionResult(
            fields=[
                ExtractedField("cccd", "079201012345", confidence=95),
                ExtractedField("phone", "0912345678", confidence=90),
            ]
        )
        assessment = assess_extraction(result)
        assert assessment["quality"] == "high"
        assert assessment["valid_count"] == 2

    def test_assess_extraction_empty(self):
        assessment = assess_extraction(ExtractionResult())
        assert assessment["quality"] == "low"
        assert assessment["overall_confidence"] == 0.0
