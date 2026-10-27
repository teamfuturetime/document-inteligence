"""Regression tests for coordinate-based reading order and table preservation."""

from ai_service.ocr.engine import OCRWord
from ai_service.ocr.layout import build_page_structure, render_page_text


def word(text, x, y, *, block, line=1, number=1, confidence=90):
    return OCRWord(
        text=text,
        confidence=confidence,
        bbox=(x, y, max(len(text) * 8, 20), 20),
        block_number=block,
        paragraph_number=1,
        line_number=line,
        word_number=number,
    )


def test_two_columns_keep_independent_reading_streams():
    words = [
        word("TIÊU ĐỀ", 50, 20, block=1),
        word("Trái một", 80, 120, block=2),
        word("Trái hai", 80, 220, block=3),
        word("Phải một", 650, 130, block=4),
        word("Phải hai", 650, 230, block=5),
    ]
    # Make the heading a spanning block.
    words[0].bbox = (50, 20, 800, 30)

    page = build_page_structure(words, page_number=1, width=1000, height=1400)

    assert [block["text"] for block in page["blocks"]] == [
        "TIÊU ĐỀ",
        "Trái một",
        "Trái hai",
        "Phải một",
        "Phải hai",
    ]
    assert render_page_text(page).index("Trái hai") < render_page_text(page).index("Phải một")


def test_table_is_created_only_from_repeated_aligned_cells():
    words = [
        word("Hạng mục", 50, 100, block=1, line=1),
        word("SL", 350, 100, block=1, line=1, number=2),
        word("Thành tiền", 550, 100, block=1, line=1, number=3),
        word("Dịch vụ", 50, 150, block=1, line=2),
        word("2", 350, 150, block=1, line=2, number=2),
        word("1.000.000", 550, 150, block=1, line=2, number=3),
    ]

    page = build_page_structure(words, page_number=1, width=900, height=1200)
    block = page["blocks"][0]

    assert block["type"] == "table"
    assert [[cell["text"] for cell in row] for row in block["rows"]] == [
        ["Hạng mục", "SL", "Thành tiền"],
        ["Dịch vụ", "2", "1.000.000"],
    ]


def test_table_rows_split_by_tesseract_blocks_are_merged_at_page_level():
    words = [
        word("Hạng mục", 50, 100, block=1), word("SL", 350, 100, block=1, number=2), word("Tiền", 550, 100, block=1, number=3),
        word("Dịch vụ", 50, 150, block=2), word("2", 350, 150, block=2, number=2), word("1.000.000", 550, 150, block=2, number=3),
    ]
    page = build_page_structure(words, page_number=1, width=900, height=1200)
    assert len(page["blocks"]) == 1
    assert page["blocks"][0]["type"] == "table"


def test_table_with_a_missing_recognized_cell_is_flagged_for_review():
    words = [
        word("Hạng mục", 50, 100, block=1), word("SL", 350, 100, block=1, number=2), word("Giá", 550, 100, block=1, number=3), word("Tiền", 750, 100, block=1, number=4),
        word("Dịch vụ", 50, 150, block=2), word("500.000", 550, 150, block=2, number=2), word("1.000.000", 750, 150, block=2, number=3),
    ]
    page = build_page_structure(words, page_number=1, width=1000, height=1200)
    assert page["blocks"][0]["type"] == "table"
    assert page["blocks"][0]["needs_review"] is True


def test_two_columns_combined_into_horizontal_lines_are_split():
    words = [
        word("Trái một", 50, 100, block=1), word("Phải một", 650, 100, block=1, number=2),
        word("Trái hai", 50, 150, block=2), word("Phải hai", 650, 150, block=2, number=2),
    ]
    page = build_page_structure(words, page_number=1, width=1000, height=1200)
    assert [block["text"] for block in page["blocks"]] == [
        "Trái một", "Trái hai", "Phải một", "Phải hai"
    ]


def test_low_confidence_is_reported_not_corrected():
    page = build_page_structure(
        [word("MST", 20, 20, block=1, confidence=35), word("01012O4567", 100, 20, block=1, number=2, confidence=30)],
        page_number=1,
        width=800,
        height=1000,
    )

    assert page["blocks"][0]["needs_review"] is True
    assert "01012O4567" in page["blocks"][0]["text"]
