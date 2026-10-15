"""Unit tests cho OCR tiếng Việt: hậu xử lý, độ tin cậy, engine."""
import pytest

from ai_service.ocr.confidence import (
    ConfidenceReport,
    assess_confidence,
    low_confidence_words,
    should_reprocess,
    word_confidence,
)
from ai_service.ocr.engine import OCRError, OCRResult, OCRWord, VietnameseOCREngine
from ai_service.ocr.postprocess import (
    clean_whitespace,
    fix_common_ocr_errors,
    fix_vietnamese_diacritics,
    is_valid_word,
    normalize_unicode,
    postprocess_text,
)


# ----------------------------------------------------------------------
# Post-processing
# ----------------------------------------------------------------------
class TestPostprocess:
    def test_normalize_unicode_nfc(self):
        # "Hòa" ở dạng NFD (dấu tách rời) → NFC
        nfd = "Ho\u0300a"
        assert normalize_unicode(nfd) == "Hòa"

    def test_fix_common_ocr_errors(self):
        assert fix_common_ocr_errors("cå phê") == "cá phê"
        assert fix_common_ocr_errors("tåi") == "tái"

    def test_clean_whitespace(self):
        assert clean_whitespace("  Xin   chào ,  bạn  ") == "Xin chào, bạn"

    def test_clean_whitespace_keeps_newlines(self):
        assert clean_whitespace("Dòng 1\n\nDòng 2") == "Dòng 1\n\nDòng 2"

    def test_fix_vietnamese_diacritics(self):
        assert fix_vietnamese_diacritics("hoà bình") == "hoà bình"
        assert fix_vietnamese_diacritics("hòa bình") == "hoà bình"

    def test_is_valid_word(self):
        assert is_valid_word("Xin")
        assert is_valid_word("123")
        assert not is_valid_word("")
        assert not is_valid_word("...")

    def test_postprocess_text_pipeline(self):
        raw = "  Xin   chào ,  tåi   là  Nam  "
        result = postprocess_text(raw)
        assert "  " not in result
        assert "tåi" not in result
        assert result.startswith("Xin chào")


# ----------------------------------------------------------------------
# Confidence
# ----------------------------------------------------------------------
class TestConfidence:
    def _make_result(self, confidences):
        words = [OCRWord(text=f"từ{i}", confidence=c) for i, c in enumerate(confidences)]
        return OCRResult(text="\n".join(w.text for w in words), words=words)

    def test_word_confidence_clamped(self):
        assert word_confidence(OCRWord("a", 150.0)) == 100.0
        assert word_confidence(OCRWord("a", -10.0)) == 0.0
        assert word_confidence(OCRWord("a", 75.0)) == 75.0

    def test_low_confidence_words(self):
        result = self._make_result([90.0, 30.0, 60.0])
        low = low_confidence_words(result.words)
        assert len(low) == 1
        assert low[0].text == "từ1"

    def test_assess_confidence_high(self):
        result = self._make_result([95.0, 90.0, 88.0])
        report = assess_confidence(result)
        assert report.quality == "high"
        assert not report.needs_review

    def test_assess_confidence_low(self):
        result = self._make_result([20.0, 30.0, 10.0])
        report = assess_confidence(result)
        assert report.quality == "low"
        assert report.needs_review

    def test_assess_confidence_empty(self):
        report = assess_confidence(OCRResult(text="", words=[]))
        assert report.quality == "low"
        assert report.word_count == 0

    def test_should_reprocess(self):
        good = self._make_result([95.0, 90.0])
        bad = self._make_result([20.0, 30.0])
        assert not should_reprocess(good)
        assert should_reprocess(bad)

    def test_mean_confidence_property(self):
        result = self._make_result([80.0, 100.0])
        assert result.mean_confidence == 90.0


# ----------------------------------------------------------------------
# Engine
# ----------------------------------------------------------------------
class TestEngine:
    def test_ocr_error_when_no_engine(self, monkeypatch):
        monkeypatch.setattr("ai_service.ocr.engine._HAS_TESSERACT", False)
        monkeypatch.setattr("ai_service.ocr.engine._HAS_PADDLE", False)
        engine = VietnameseOCREngine()
        with pytest.raises(OCRError):
            engine.recognize(None)

    def test_ocr_result_defaults(self):
        result = OCRResult(text="Xin chào")
        assert result.words == []
        assert result.language == "vie"
        assert result.engine == "tesseract"
        assert result.mean_confidence == 0.0
