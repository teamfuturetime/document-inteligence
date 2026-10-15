import unicodedata

from ai_service.evaluation import character_error_rate, word_error_rate
from ai_service.ocr.engines import RawOcrLine
from ai_service.ocr.geometry import to_text_block
from ai_service.ocr.normalization import normalize_vietnamese_text


def test_normalizes_vietnamese_unicode_and_spacing() -> None:
    decomposed = unicodedata.normalize("NFD", "Cộng hòa")
    assert normalize_vietnamese_text(f" {decomposed}  \n") == "Cộng hòa"


def test_normalizes_bounding_box() -> None:
    raw = RawOcrLine("Họ tên", 1.2, [[10, 20], [60, 20], [60, 40], [10, 40]])
    block = to_text_block(raw, width=100, height=100)
    assert block.box == (0.1, 0.2, 0.6, 0.4)
    assert block.confidence == 1.0


def test_cer_and_wer() -> None:
    assert character_error_rate("abc", "adc") == 1 / 3
    assert word_error_rate("xin chào bạn", "xin chào") == 1 / 3
