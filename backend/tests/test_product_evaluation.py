import pytest

from docintel.evaluation.product import field_counts


def pair(expected, actual, status="present"):
    return {"status": status, "value": expected}, {"normalized_value": actual}


def test_exact_tuple_metrics_wrong_is_fp_and_fn_and_no_null_tp():
    report = field_counts(
        [pair("a", "a")] * 45
        + [pair("b", "c")] * 3
        + [pair("d", None)] * 2
        + [pair(None, None, "absent")]
        + [pair(None, None, "unreadable")]
    )
    assert (report["tp"], report["fp"], report["fn"]) == (45, 3, 5)
    assert report["precision"] == 45 / 48
    assert report["recall"] == 45 / 50
    assert report["f1"] == 90 / 98
    assert report["present_accuracy"] == 45 / 50
    assert report["unreadable_abstention_rate"] == 1


def test_extra_fill_zero_denominators_types_and_diacritics():
    metrics = field_counts(
        [pair(None, "extra", "absent"), pair("001", 1), pair("Nguyễn", "Nguyen"), pair(0, 0)]
    )
    assert metrics["extra_fill_rate"] == 1
    assert (metrics["tp"], metrics["fp"], metrics["fn"]) == (1, 3, 2)
    empty = field_counts([])
    assert empty["precision"] is None
    assert empty["recall"] is None
    assert empty["present_accuracy"] is None
    with pytest.raises(ValueError):
        field_counts([pair("hidden", None, "unreadable")])
