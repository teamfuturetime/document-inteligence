import pytest

from ai02_solo.contracts import normalize, validate_values


def test_invoice_normalizes_vietnamese_dates_and_grouped_amounts():
    result = validate_values("invoice", dict(invoice_number="  M-01 ", invoice_date="11/11/2026",
        seller_name="Cửa   hàng Mẫu", total_amount="1.250.000 đ", currency="vnđ"))
    assert result["valid"]
    assert result["values"]["invoice_date"] == "2026-11-11"
    assert result["values"]["total_amount"] == 1250000
    assert result["values"]["seller_name"] == "Cửa hàng Mẫu"


@pytest.mark.parametrize("key,value", [("invoice_date", "2026-02-30"), ("invoice_date", "11-12-26"),
    ("total_amount", "1.23"), ("total_amount", "-1"), ("total_amount", 9007199254740992),
    ("currency", "USD"), ("student_id", " "), ("seller_name", None)])
def test_invalid_values(key, value):
    with pytest.raises(ValueError):
        normalize(key, value)


def test_application_has_independent_schema_and_field_errors():
    values = dict(applicant_name="Sinh viên Mẫu A", student_id="SYN-001", recipient="Phòng Mẫu",
                  request="Xin cấp giấy xác nhận tổng hợp", submission_date="31/02/2026")
    result = validate_values("application", values)
    assert result["errors"].keys() == {"submission_date"}
    assert result["values"]["submission_date"] is None
    values["submission_date"] = "2026-11-11"
    assert validate_values("application", values)["valid"]


def test_unknown_or_missing_fields_are_rejected():
    with pytest.raises(ValueError):
        validate_values("application", {"invoice_number": "x"})
