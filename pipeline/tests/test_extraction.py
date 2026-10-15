import json
import random
import subprocess
import sys
import unicodedata

import pytest

from document_contracts.models import ExtractionResponse, MAX_SAFE_INTEGER, OCRResult
from document_pipeline.extraction import (
    RULES_SHA256, SourceValueError, extract_invoice, normalize_value,
)


def make_ocr(lines, *, mode="mock", score=.9):
    tokens = []
    for row, line in enumerate(lines):
        left = 20
        for word in line.split():
            width = max(10, 12 * len(word))
            tokens.append({"text": word, "confidence": score,
                           "box": {"x0": left, "y0": 20 + row * 45,
                                   "x1": left + width, "y1": 45 + row * 45}})
            left += width + 10
    return OCRResult(schema_version="1.0.0", mode=mode,
                     ocr_version="mock-not-run" if mode == "mock" else "test-engine-version",
                     language="vie+eng", page={
                         "page": 1, "width": 6000, "height": 3000,
                         "to_original": [1., 0., 0., 0., 1., 0., 0., 0., 1.], "tokens": tokens,
                     })


def invoice_lines():
    return ["Số hóa đơn: SYN-0012", "Ngày: 2026-10-15", "Bên bán: Cửa hàng Mây Việt",
            "Tổng tiền: 125.000", "Tiền tệ: VND"]


def test_five_labelled_fields_and_provenance_without_mutating_ocr():
    ocr = make_ocr(invoice_lines())
    original = ocr.model_dump_json()
    result = extract_invoice(ocr, "unit-invoice")
    assert {key: field.value for key, field in result.fields} == {
        "invoice_number": "SYN-0012", "invoice_date": "2026-10-15",
        "seller_name": "Cửa hàng Mây Việt", "total_amount": 125000, "currency": "VND",
    }
    assert result.mode == "mock" and result.warnings == ["mock_data"]
    assert result.ocr_version == "mock-not-run" and result.document_id == "unit-invoice"
    assert result.config_version.endswith(RULES_SHA256[:12])
    for _, field in result.fields:
        assert field.confidence == .9 and not field.warnings
        assert field.evidence
        for evidence in field.evidence:
            assert any(evidence.text == token.text and evidence.box == token.box for token in ocr.page.tokens)
    assert ocr.model_dump_json() == original
    # The result must not share mutable boxes with the OCR input.
    result.fields.invoice_number.evidence[0].box.x0 = 0
    assert ocr.model_dump_json() == original


@pytest.mark.parametrize("label,field,value", [
    ("MA HOA DON", "invoice_number", "ID-1"),
    ("Ngày lập", "invoice_date", "2026-10-15"),
    ("Ngày hóa đơn", "invoice_date", "2026-10-15"),
    ("Tên bên bán", "seller_name", "Cửa hàng Giả"),
    ("Người bán", "seller_name", "Cửa hàng Giả"),
    ("Tổng cộng", "total_amount", "125000"),
    ("Tổng tiền thanh toán", "total_amount", "125000"),
    ("Đơn vị tiền tệ", "currency", "VND"),
])
def test_label_aliases_case_and_accents(label, field, value):
    result = extract_invoice(make_ocr([f"{label} : {value}"]), "alias")
    assert getattr(result.fields, field).value == normalize_value(field, value)


def test_geometry_restores_rows_from_shuffled_tokens_and_handles_short_punctuation():
    ocr = make_ocr(invoice_lines())
    hyphen = make_ocr(["Bên bán: Cửa hàng - dữ liệu giả"]).page.tokens[-4]
    assert hyphen.text == "-"
    ocr = make_ocr(["Bên bán: Cửa hàng - dữ liệu giả", "Tổng tiền: 1.000"])
    hyphen = next(token for token in ocr.page.tokens if token.text == "-")
    hyphen.box.y0, hyphen.box.y1 = 32, 35
    random.Random(17).shuffle(ocr.page.tokens)
    result = extract_invoice(ocr, "shuffled")
    assert result.fields.seller_name.value == "Cửa hàng - dữ liệu giả"
    assert result.fields.total_amount.value == 1000


def test_missing_fields_and_unlabelled_values_are_not_guessed():
    result = extract_invoice(make_ocr(["SYN-123 2026-10-15 125000 VND", "Ghi chú: Tiền tệ: VND"]), "missing")
    for _, field in result.fields:
        assert field.value is None and field.confidence is None and field.evidence == []
        assert field.warnings == ["missing_field"]


def test_currency_is_not_defaulted_for_vietnamese_invoice():
    result = extract_invoice(make_ocr(invoice_lines()[:-1]), "missing-currency")
    assert result.fields.total_amount.value == 125000
    assert result.fields.currency.value is None
    assert result.fields.currency.warnings == ["missing_field"]


def test_currency_suffix_is_not_taken_from_inside_another_word():
    result = extract_invoice(make_ocr(["Tổng tiền: NOTVND"]), "not-currency")
    assert result.fields.total_amount.value is None
    assert result.fields.currency.value is None
    assert result.fields.currency.warnings == ["missing_field"]


@pytest.mark.parametrize("currency", ["VND", "VNĐ", "đồng", "đ", "₫"])
def test_explicit_currency_suffix_on_total_is_evidence(currency):
    result = extract_invoice(make_ocr([f"Tổng tiền: 125.000 {currency}"]), "suffix")
    assert result.fields.currency.value == "VND"
    assert result.fields.total_amount.value == 125000
    assert any(currency in evidence.text for evidence in result.fields.currency.evidence)


def test_invalid_currency_label_conflicts_with_valid_suffix():
    result = extract_invoice(make_ocr(["Tổng tiền: 125000 VND", "Tiền tệ: USD"]), "conflict")
    assert result.fields.currency.value is None and result.fields.currency.confidence is None
    assert set(result.fields.currency.warnings) == {"invalid_source_value", "ambiguous_field"}


@pytest.mark.parametrize("lines,field", [
    (["Tổng tiền: 1000", "Tổng cộng: 2000"], "total_amount"),
    (["Số hóa đơn: A-1", "Mã hóa đơn: A-2"], "invoice_number"),
    (["Ngày: 2026-10-15", "Ngày lập: sai-ngày"], "invoice_date"),
    (["Bên bán: Cửa hàng A Ngày: 2026-10-15"], "seller_name"),
])
def test_ambiguous_candidates_never_choose_first_or_highest_confidence(lines, field):
    result = extract_invoice(make_ocr(lines), "ambiguous")
    selected = getattr(result.fields, field)
    assert selected.value is None and selected.confidence is None and selected.evidence
    assert "ambiguous_field" in selected.warnings


def test_duplicate_agreeing_candidates_keep_all_evidence():
    result = extract_invoice(make_ocr(["Tổng tiền: 1.000", "Tổng cộng: 1000"]), "duplicate")
    field = result.fields.total_amount
    assert field.value == 1000 and not field.warnings
    assert len(field.evidence) == 6


@pytest.mark.parametrize("score", [0., None])
def test_unknown_or_zero_score_is_not_invented_or_dropped(score):
    ocr = make_ocr(["Tổng tiền: 1000"])
    ocr.page.tokens[-1].confidence = score
    field = extract_invoice(ocr, "score").fields.total_amount
    assert field.value == 1000 and field.confidence == score


def test_lowest_label_or_value_confidence_is_used():
    ocr = make_ocr(["Tổng tiền: 1000"])
    ocr.page.tokens[0].confidence = .4
    assert extract_invoice(ocr, "score").fields.total_amount.confidence == .4


@pytest.mark.parametrize("field,raw,expected", [
    ("invoice_number", " SYN-0001 ", "SYN-0001"),
    ("seller_name", unicodedata.normalize("NFD", " Cửa   hàng Mây Việt "), "Cửa hàng Mây Việt"),
    ("invoice_date", "2024-02-29", "2024-02-29"),
    ("invoice_date", "15/10/2026", "2026-10-15"),
    ("invoice_date", "15-10-2026", "2026-10-15"),
    ("invoice_date", "10/10/2026", "2026-10-10"),
    ("total_amount", "0", 0), ("total_amount", "00125", 125),
    ("total_amount", "1,234,567 VND", 1234567),
    ("total_amount", "1 234 567", 1234567),
    ("total_amount", str(MAX_SAFE_INTEGER), MAX_SAFE_INTEGER),
    ("currency", "vnđ", "VND"),
])
def test_source_normalization(field, raw, expected):
    assert normalize_value(field, raw) == expected


@pytest.mark.parametrize("field,raw", [
    ("invoice_number", "???"), ("invoice_number", "A" * 101),
    ("seller_name", "1234"), ("seller_name", "A" * 201), ("seller_name", "A\x00B"),
    ("invoice_date", "2026-02-29"), ("invoice_date", "31/04/2026"),
    ("invoice_date", "10/15/2026"), ("invoice_date", "2026/10/15"),
    ("total_amount", "-1"), ("total_amount", "1e3"),
    ("total_amount", "125,50"), ("total_amount", "1.234,567"),
    ("total_amount", "1234.567"), ("total_amount", "125000 USD"),
    ("total_amount", str(MAX_SAFE_INTEGER + 1)), ("total_amount", "9" * 5000),
    ("currency", "USD"), ("currency", "D"),
])
def test_invalid_source_is_not_silently_corrected(field, raw):
    with pytest.raises(SourceValueError) as error:
        normalize_value(field, raw)
    assert error.value.warning == "invalid_source_value"


def test_ambiguous_numeric_date_is_not_guessed():
    field = extract_invoice(make_ocr(["Ngày: 03/04/2026"]), "date").fields.invoice_date
    assert field.value is None and field.confidence is None
    assert field.warnings == ["ambiguous_field"] and field.evidence


def test_invalid_or_empty_labelled_values_preserve_raw_evidence():
    result = extract_invoice(make_ocr(["Ngày: 2026-02-30", "Tổng tiền:"]), "invalid")
    assert result.fields.invoice_date.value is None
    assert result.fields.invoice_date.warnings == ["invalid_source_value"]
    assert result.fields.invoice_date.evidence[-1].text == "2026-02-30"
    assert result.fields.total_amount.value is None
    assert result.fields.total_amount.warnings == ["missing_field"]
    assert result.fields.total_amount.evidence


def test_real_mode_and_ocr_version_are_preserved_and_output_is_deterministic():
    ocr = make_ocr(invoice_lines(), mode="real")
    first = extract_invoice(ocr, "real-invoice")
    second = extract_invoice(ocr, "real-invoice")
    assert first == second and first.mode == "real" and "mock_data" not in first.warnings
    assert first.ocr_version == ocr.ocr_version
    ExtractionResponse.model_validate_json(first.model_dump_json())


def test_cli_accepts_ocr_json_and_emits_contract_and_metadata(tmp_path):
    source = tmp_path / "ocr.json"
    source.write_text(make_ocr(invoice_lines()).model_dump_json(), encoding="utf-8")
    output = tmp_path / "result.json"
    run = subprocess.run([sys.executable, "-m", "document_pipeline.extraction", str(source),
                          "--output", str(output)], capture_output=True)
    assert run.returncode == 0, run.stderr.decode()
    result = ExtractionResponse.model_validate_json(output.read_bytes())
    assert result.fields.total_amount.value == 125000 and result.mode == "mock"
    metadata = json.loads(output.with_suffix(".metadata.json").read_text())
    assert metadata["rules_sha256"] == RULES_SHA256


def test_cli_does_not_overwrite_input(tmp_path):
    source = tmp_path / "ocr.json"
    data = make_ocr(invoice_lines()).model_dump_json()
    source.write_text(data)
    run = subprocess.run([sys.executable, "-m", "document_pipeline.extraction", str(source),
                          "--output", str(source)], capture_output=True)
    assert run.returncode == 1
    assert source.read_text() == data
