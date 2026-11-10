import json
from pathlib import Path
import unicodedata

import pytest

from ai_service.classification.engine import (
    build_vietnamese_classifier,
    fold_diacritics,
)
from ai_service.classification.rules import DocumentTypeDetector
from ai_service.extraction.confidence import assess_extraction
from ai_service.extraction.rules import build_vietnamese_form_engine

CASES = json.loads(
    (Path(__file__).parents[1] / "fixtures/extraction/cases.json").read_text(
        encoding="utf-8"
    )
)


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["name"])
@pytest.mark.parametrize("variant", ["original", "no_accents", "nfd", "spacing"])
def test_profiles_extract_only_expected_evidence(case, variant):
    text = case["text"]
    expected = case["fields"]
    if variant == "no_accents":
        text = fold_diacritics(text)
        expected = {key: fold_diacritics(value) for key, value in expected.items()}
    elif variant == "nfd":
        text = unicodedata.normalize("NFD", text)
    elif variant == "spacing":
        text = text.replace(" ", "\u00a0  ").replace("\n", "\r\n")
    classification = build_vietnamese_classifier().classify(text)
    assert classification.document_type == case["type"]
    assert classification.confidence_type == "heuristic"
    assert 0 < classification.confidence < 100
    assert classification.matched_rules
    result = build_vietnamese_form_engine().extract(text, classification.document_type)
    assert result.to_dict() == expected
    assert all(
        field.confidence_type == "not_estimated" and field.matched_pattern
        for field in result.fields
    )
    assert assess_extraction(result)["confidence_type"] == "not_estimated"


@pytest.mark.parametrize(
    "text,kind,expected",
    [
        ("HÓA ĐƠN\nSố hóa đơn: 0000042", "hoa_don", {"invoice_number": "0000042"}),
        (
            "H0A D0N\nS0 hoa d0n: HD-17\nNgay lap: O6/11/2026\nTong cong: 1.OOO.OOO dong",
            "hoa_don",
            {
                "invoice_number": "HD-17",
                "issue_date": "06/11/2026",
                "total_amount": "1.000.000",
            },
        ),
        (
            "CAN CUOC CONG DAN\nSo dinh danh: 07920I012345\nHo ten: LE THI MAU",
            "cccd",
            {"cccd": "079201012345", "full_name": "LE THI MAU"},
        ),
        (
            "CĂN CƯỚC CÔNG DÂN\nHọ và tên:\nNgày sinh:\nGiới tính:\nQuốc tịch:\nNơi thường trú:",
            "cccd",
            {},
        ),
        (
            "CĂN CƯỚC CÔNG DÂN\nNgày sinh: 31/02/2000\nSố định danh: 12345678901\nQuốc tịch: N/A",
            "cccd",
            {},
        ),
        (
            "HÓA ĐƠN\nSố hóa đơn: ...\nTổng cộng: chưa có\nVAT: không có\nĐịa chỉ:\nNgười bán ký tên",
            "hoa_don",
            {},
        ),
        (
            "HÓA ĐƠN\nNgười mua: CÔNG TY A\nĐịa chỉ: 15 Phố Người Mua\nTổng cộng: 25.000",
            "hoa_don",
            {"total_amount": "25.000"},
        ),
        (
            "HÓA ĐƠN\nSố hóa đơn:\f999999\nTổng cộng: 5.000",
            "hoa_don",
            {"total_amount": "5.000"},
        ),
        (
            "HÓA ĐƠN\nSố hóa đơn: 001\nTổng cộng: 5.000\fHÓA ĐƠN\nSố hóa đơn: 002\nTổng cộng: 8.000",
            "hoa_don",
            {},
        ),
        (
            "HÓA ĐƠN\nSố hóa đơn: 001\fHÓA ĐƠN\nTổng cộng: 5.000\nVAT: 500",
            "hoa_don",
            {"invoice_number": "001", "total_amount": "5.000", "vat": "500"},
        ),
        ("Báo cáo thời tiết ngày mai có mưa. 079201012345 1.000.000", "unknown", {}),
        (
            "Họ tên: Nguyễn Văn A\nEmail: seller@example.test",
            "unknown",
            {"full_name": "Nguyễn Văn A", "email": "seller@example.test"},
        ),
    ],
)
def test_missing_ambiguous_ocr_noise_and_unknown(text, kind, expected):
    assert build_vietnamese_form_engine().extract(text, kind).to_dict() == expected


def test_identity_labels_on_one_line_do_not_capture_next_fields():
    text = "Số: 079201012345 Họ và tên: NGUYỄN VĂN A Ngày sinh: 02/03/1999 Giới tính: Nam Quốc tịch: Việt Nam"
    result = build_vietnamese_form_engine().extract(text, "cccd").to_dict()
    assert result == {
        "cccd": "079201012345",
        "full_name": "NGUYỄN VĂN A",
        "birth_date": "02/03/1999",
        "gender": "Nam",
        "nationality": "Việt Nam",
    }


def test_tesseract_separator_between_identity_columns_is_not_part_of_gender():
    text = "Giới tính / Sex: Nữ _ Quốc tịch / Nationality: Việt Nam"
    assert build_vietnamese_form_engine().extract(text, "cccd").to_dict() == {"gender": "Nữ", "nationality": "Việt Nam"}


def test_ocr_blank_between_address_lines_is_bounded_and_stops_at_next_field_or_page():
    engine = build_vietnamese_form_engine()
    text = "CĂN CƯỚC CÔNG DÂN\nHọ tên:\n\nNGUYỄN VĂN A\nĐịa chỉ: 12 Đường Mẫu\n\nQuận Minh Họa, TP. Hà Nội\nNgày cấp: 01/01/2026"
    assert engine.extract(text, "cccd").to_dict() == {"full_name": "NGUYỄN VĂN A", "address": "12 Đường Mẫu Quận Minh Họa, TP. Hà Nội"}
    assert engine.extract("Địa chỉ: Hà Nội\n\f\nQuận Khác", "cccd").to_dict() == {"address": "Hà Nội"}
    assert engine.extract("Địa chỉ: Hà Nội\n\nGhi chú: Không ghép vào địa chỉ", "cccd").to_dict() == {"address": "Hà Nội"}


def test_classifier_does_not_treat_nine_digit_prefix_as_cmnd():
    result = build_vietnamese_classifier().classify("Số: 079201012345")
    assert result.document_type == "cccd"
    assert result.scores["cmnd"] == 0


@pytest.mark.parametrize(
    "text",
    [
        "Thông báo thanh toán vào ngày mai",
        "Địa chỉ giao hàng: Hà Nội",
        "Tổng cộng 100 sản phẩm. Chuyển khoản.",
    ],
)
def test_generic_payment_words_do_not_force_invoice(text):
    assert build_vietnamese_classifier().classify(text).document_type == "unknown"


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["name"])
def test_detector_and_classifier_support_same_new_types(case):
    assert DocumentTypeDetector().detect(case["text"]).document_type == case["type"]


def test_existing_anonymized_synthetic_documents_use_new_profiles():
    manifest = json.loads(
        (Path(__file__).parents[1] / "fixtures/vietnamese/manifest.json").read_text(
            encoding="utf-8"
        )
    )
    for case in manifest:
        if case["category"] not in {
            "invoice_table",
            "administrative_form",
            "vietnamese_text",
        }:
            continue
        classification = build_vietnamese_classifier().classify(case["ground_truth"])
        fields = (
            build_vietnamese_form_engine()
            .extract(case["ground_truth"], classification.document_type)
            .to_dict()
        )
        if case["category"] == "invoice_table":
            assert classification.document_type == "hoa_don"
            assert fields == {"tax_code": "0101234567", "total_amount": "1.000.000"}
        elif case["category"] == "administrative_form":
            assert classification.document_type == "application_form"
            assert fields["form_name"] == "BIỂU MẪU HÀNH CHÍNH TỔNG HỢP"
        elif classification.document_type == "don_xin_viec":
            assert fields["full_name"] == "NGUYỄN VĂN DEMO"
