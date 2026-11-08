import unicodedata

import pytest

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

    assert len(lines) == 1
    assert lines[0].text == "HÓA ĐƠN"
    assert lines[0].confidence == pytest.approx(0.85)
    assert lines[0].polygon == [[10, 20], [85, 20], [85, 35], [10, 35]]


def test_separates_distant_columns_within_a_tesseract_line() -> None:
    data = {
        "text": ["Tổng", "tiền", "100.000", "đồng"],
        "conf": ["90", "80", "70", "90"],
        "block_num": [1] * 4, "par_num": [1] * 4, "line_num": [1] * 4,
        "left": [10, 50, 220, 290], "top": [20] * 4,
        "width": [30, 30, 60, 40], "height": [15] * 4,
    }

    lines = _group_tesseract_lines(data)

    assert [line.text for line in lines] == ["Tổng tiền", "100.000 đồng"]
    assert [line.confidence for line in lines] == pytest.approx([0.85, 0.8])
    assert lines[0].polygon == [[10, 20], [80, 20], [80, 35], [10, 35]]
    assert lines[1].polygon == [[220, 20], [330, 20], [330, 35], [220, 35]]


def test_tesseract_skips_empty_and_unrecognized_words() -> None:
    data = {
        "text": ["", "   ", "unrecognized", "Tên"],
        "conf": ["-1", "90", "-1", "0"],
        "block_num": [1] * 4, "par_num": [1] * 4, "line_num": [1] * 4,
        "left": [0, 10, 20, 30], "top": [10] * 4,
        "width": [10] * 4, "height": [10] * 4,
    }

    lines = _group_tesseract_lines(data)

    assert lines == [RawOcrLine("Tên", 0.0, [[30, 10], [40, 10], [40, 20], [30, 20]])]
