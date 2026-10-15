import pytest

from document_evaluation.metrics import FIELDS, field_metrics


def values(**changes):
    return {**dict.fromkeys(FIELDS), **changes}


def test_hand_computed_wrong_value_counts_both_fp_and_fn_and_null_is_not_tp():
    report = field_metrics([
        (values(invoice_number="A"), values(invoice_number="A")),
        (values(invoice_number="B"), values(invoice_number="C")),
        (values(), values(invoice_number="D")),
        (values(invoice_number="E"), values()), (values(), values()),
    ])
    field = report["fields"]["invoice_number"]
    assert (field["tp"], field["fp"], field["fn"], field["correct"], field["null_pairs"]) == (1, 2, 2, 2, 1)
    assert field["precision"] == field["recall"] == field["f1"] == pytest.approx(1 / 3)
    assert field["exact_match"] == .4
    assert report["macro"]["exact_match"] == pytest.approx(.88)
    assert report["micro"]["tp"] == 1


def test_all_null_and_empty_denominators_are_explicit():
    null = field_metrics([(values(), values())])
    assert null["micro"]["exact_match"] == 1
    assert null["micro"]["tp"] == 0
    assert null["micro"]["precision"] is None and null["micro"]["f1"] is None
    empty = field_metrics([])
    assert empty["macro"]["exact_match"] is None and empty["micro"]["recall"] is None


def test_comparison_normalizes_nfc_spaces_but_keeps_case_and_accents():
    normalized = field_metrics([(values(seller_name=" Cu\u031b\u0309a   ha\u0300ng "), values(seller_name="Cửa hàng"))])
    assert normalized["fields"]["seller_name"]["exact_match"] == 1
    wrong = field_metrics([(values(seller_name="Cua hang"), values(seller_name="Cửa hàng"))])
    assert wrong["fields"]["seller_name"]["exact_match"] == 0
