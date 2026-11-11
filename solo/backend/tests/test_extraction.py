from ai02_solo.contracts import LABELS, Token
from ai02_solo.extract import align_vlm, field, fuse, match_label, rule_extract


def tokens(*content):
    return [Token(text=word, confidence=.9, box=(column * 50, row * 30, column * 50 + 45, row * 30 + 25),
                  line=(1, 1, row + 1)) for row, line in enumerate(content) for column, word in enumerate(line.split())]


def test_colon_optional_value_on_next_line_and_vnd_suffix():
    output = rule_extract("invoice", tokens("Mã hóa đơn HD-101", "Ngày lập: 11/11/2026", "Bên bán:",
                         "Cửa hàng Hoa Mẫu", "Tổng thanh toán: 1.250.000 VND"))
    assert output["invoice_number"].value == "HD-101"
    assert output["seller_name"].value == "Cửa hàng Hoa Mẫu"
    assert output["invoice_date"].value == "2026-11-11"
    assert output["total_amount"].value == 1250000
    assert output["currency"].value == "VND"
    assert output["seller_name"].confidence == .9


def test_conflicting_candidates_are_never_first_wins():
    output = rule_extract("invoice", tokens("Số hóa đơn: A", "Mã hóa đơn: B"))
    assert output["invoice_number"].value is None
    assert output["invoice_number"].source == "conflict"
    assert output["invoice_number"].confidence is None


def test_missing_label_does_not_swallow_following_label():
    output = rule_extract("application", tokens("Họ và tên:", "MSSV: SYN-123", "Kính gửi: Phòng Mẫu"))
    assert output["applicant_name"].value is None
    assert output["student_id"].value == "SYN-123"


def test_vlm_unsubstantiated_value_has_no_fake_confidence():
    values = dict(invoice_number="V-100", invoice_date=None, seller_name="Cửa hàng Mẫu", total_amount=None, currency=None)
    output = align_vlm("invoice", values, tokens("Bên bán: Cửa hàng Mẫu"))
    assert output["invoice_number"].confidence is None
    assert output["invoice_number"].warnings
    assert output["seller_name"].confidence == .9


def test_hybrid_disagreement_and_unsupported_vlm_stay_null():
    rules = {"a": field("A", "rules", ["A"], [.8]), "b": field()}
    vision = {"a": field("B", "vlm", ["B"], [.7]), "b": field("invented", "vlm")}
    result = fuse(rules, vision)
    assert result["a"].value is None and result["a"].source == "conflict"
    assert result["b"].value is None


def test_zero_and_unknown_confidence_are_preserved():
    assert field("A", "rules", ["A"], [0, .8]).confidence == 0
    assert field("A", "rules", ["A"], [None, .8]).confidence is None


def test_linux_ocr_single_label_error_does_not_rewrite_value():
    result = rule_extract("application", tokens("Ma sé sinh vién: SYN-0001", "Ho va tén: Nguoi Mau Alpha"))
    assert result["student_id"].value == "SYN-0001"
    assert result["student_id"].warnings
    assert result["student_id"].evidence == ["Ma sé sinh vién: SYN-0001"]
    assert result["applicant_name"].value == "Nguoi Mau Alpha"


def test_fuzzy_label_requires_long_unique_one_edit_match_and_colon(monkeypatch):
    for content in ["Ma sx sinh viqn: SYN-0001", "Ma sé sinh vién SYN-0001", "Ngayx: 11/11/2026"]:
        result = rule_extract("application", tokens(content))
        assert result["student_id"].value is None
        assert result["submission_date"].value is None
    monkeypatch.setitem(LABELS, "application", {"student_id": ["Ma so sinh vien"], "recipient": ["Ma se sinh vien"]})
    assert match_label(tokens("Ma sa sinh vien: SYN-0001"), "application") is None
