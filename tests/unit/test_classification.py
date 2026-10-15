"""Unit tests cho phân loại tài liệu tiếng Việt."""
import pytest

from ai_service.classification.confidence import (
    assess_classification,
    is_classified,
)
from ai_service.classification.engine import (
    ClassificationResult,
    DocumentClass,
    DocumentClassifier,
    build_vietnamese_classifier,
)
from ai_service.classification.rules import (
    DocumentTypeDetector,
    detect_document_groups,
    detect_from_ocr,
)
from ai_service.ocr.engine import OCRResult


# ----------------------------------------------------------------------
# Classifier
# ----------------------------------------------------------------------
class TestClassifier:
    def test_register_and_classify(self):
        classifier = DocumentClassifier()
        classifier.register(
            DocumentClass(name="cccd", keywords=["can cuoc", "căn cước"])
        )
        result = classifier.classify("Đây là Căn cước công dân")
        assert result.document_type == "cccd"
        assert result.confidence > 0

    def test_classify_unknown(self):
        classifier = DocumentClassifier()
        classifier.register(DocumentClass(name="cccd", keywords=["can cuoc"]))
        result = classifier.classify("Văn bản không liên quan")
        assert result.document_type == "unknown"

    def test_normalize_ignores_diacritics(self):
        classifier = DocumentClassifier()
        classifier.register(DocumentClass(name="cccd", keywords=["căn cước"]))
        # "CĂN CUỚC" không dấu vẫn khớp nhờ normalize
        result = classifier.classify("CĂN CUỚC")
        assert result.document_type == "cccd"

    def test_scores_returned(self):
        classifier = DocumentClassifier()
        classifier.register(DocumentClass(name="a", keywords=["xin chao"]))
        result = classifier.classify("xin chao")
        assert "a" in result.scores

    def test_classify_from_ocr(self):
        classifier = DocumentClassifier()
        classifier.register(
            DocumentClass(name="cccd", keywords=["can cuoc"], patterns=[r"Số[:\s]*\d{12}"])
        )
        result = classifier.classify_from_ocr(OCRResult(text="Số: 079201012345"))
        assert result.document_type == "cccd"


# ----------------------------------------------------------------------
# Vietnamese classifier rules
# ----------------------------------------------------------------------
class TestVietnameseClassifier:
    @pytest.fixture()
    def classifier(self):
        return build_vietnamese_classifier()

    def test_cccd(self, classifier):
        text = "Căn cước công dân\nSố: 079201012345\nNgày sinh: 15/08/1990"
        result = classifier.classify(text)
        assert result.document_type == "cccd"

    def test_cmnd(self, classifier):
        result = classifier.classify("Chứng minh nhân dân số 012345678")
        assert result.document_type == "cmnd"

    def test_hop_dong(self, classifier):
        text = "Hợp đồng lao động\nBên A: Công ty X\nBên B: Nguyễn Văn Nam"
        result = classifier.classify(text)
        assert result.document_type == "hop_dong_lao_dong"

    def test_don_xin_viec(self, classifier):
        text = "ĐƠN XIN VIỆC\nKính gửi: Ban giám đốc\nTôi viết đơn này..."
        result = classifier.classify(text)
        assert result.document_type == "don_xin_viec"


# ----------------------------------------------------------------------
# Detector (rules)
# ----------------------------------------------------------------------
class TestDetector:
    @pytest.fixture()
    def detector(self):
        return DocumentTypeDetector()

    def test_detect_cccd(self, detector):
        text = (
            "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\r\n"
            "Căn cước công dân\r\nSố: 079201012345\r\n"
            "Họ và tên: Nguyễn Văn Nam\r\nNgày sinh: 15/08/1990"
        )
        result = detector.detect(text)
        assert result.document_type == "cccd"

    def test_detect_unknown(self, detector):
        result = detector.detect("Lorem ipsum dolor sit amet")
        assert result.document_type == "unknown"

    def test_detect_document_groups(self):
        doc_type, matched, confidence = detect_document_groups(
            "Căn cước công dân số 079201012345"
        )
        assert doc_type == "cccd"
        assert "cccd" in matched
        assert confidence > 0

    def test_detect_from_ocr_alias(self):
        result = detect_from_ocr("Chứng minh nhân dân số 012345678")
        assert result.document_type == "cmnd"


# ----------------------------------------------------------------------
# Confidence
# ----------------------------------------------------------------------
class TestClassificationConfidence:
    def test_assess_high(self):
        result = ClassificationResult(
            document_type="cccd", confidence=95.0, scores={"cccd": 3.0, "cmnd": 0.5}
        )
        report = assess_classification(result)
        assert report.quality == "high"
        assert not report.needs_review

    def test_assess_unknown(self):
        result = ClassificationResult(document_type="unknown", confidence=0.0, scores={})
        report = assess_classification(result)
        assert report.quality == "low"
        assert report.needs_review

    def test_assess_ambiguous(self):
        # Hai loại điểm gần nhau (gap < 30%)
        result = ClassificationResult(
            document_type="cccd", confidence=55.0, scores={"cccd": 1.0, "cmnd": 0.9}
        )
        report = assess_classification(result)
        assert report.is_ambiguous
        assert report.needs_review

    def test_is_confident_property(self):
        assert ClassificationResult("cccd", 90.0).is_confident
        assert not ClassificationResult("cccd", 50.0).is_confident

    def test_is_classified(self):
        ok = ClassificationResult("cccd", 60.0)
        no = ClassificationResult("unknown", 0.0)
        assert is_classified(ok)
        assert not is_classified(no)