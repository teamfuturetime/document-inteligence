import unicodedata

from ai_service.evaluation import character_error_rate, word_error_rate
from ai_service.ocr.engines import RawOcrLine, _group_tesseract_lines
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


def test_groups_tesseract_words_into_lines() -> None:
    data = {
        "text": ["HÓA", "ĐƠN", ""],
        "conf": ["90", "80", "-1"],
        "block_num": [1, 1, 1], "par_num": [1, 1, 1], "line_num": [1, 1, 2],
        "left": [10, 50, 0], "top": [20, 20, 0],
        "width": [30, 35, 0], "height": [15, 15, 0],
    }

    lines = _group_tesseract_lines(data)

    assert lines == [RawOcrLine("HÓA ĐƠN", 0.85, [[10, 20], [85, 20], [85, 35], [10, 35]])]
