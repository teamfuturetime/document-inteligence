from ai_service.evaluation.metrics import (
    character_error_rate,
    exact_field_accuracy,
    reading_order_score,
    word_error_rate,
)


def test_cer_and_wer_are_zero_for_unicode_equivalent_text():
    assert character_error_rate("Hòa bình", "Ho\u0300a  bình") == 0
    assert word_error_rate("Hòa bình", "Ho\u0300a  bình") == 0


def test_error_rates_measure_edits_without_inventing_accuracy():
    assert character_error_rate("abc", "adc") == 1 / 3
    assert word_error_rate("một hai ba", "một bốn ba") == 1 / 3


def test_reading_order_uses_labeled_line_sequence():
    expected = ["Cột trái 1", "Cột trái 2", "Cột phải 1"]
    assert reading_order_score(expected, "Cột trái 1\nCột trái 2\nCột phải 1") == 1
    assert reading_order_score(expected, "Cột trái 1\nCột phải 1\nCột trái 2") == 2 / 3


def test_critical_fields_require_exact_match():
    expected = {"mst": "0101234567", "total": "1.000.000"}
    assert exact_field_accuracy(expected, expected) == 1
    assert exact_field_accuracy(expected, {"mst": "O101234567", "total": "1.000.000"}) == 0.5
