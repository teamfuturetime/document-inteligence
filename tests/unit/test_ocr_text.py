"""Tests for conservative OCR readability post-processing."""

import unicodedata
from datetime import datetime, timezone

from app.schemas.documents import DocumentOut
from app.services.ocr_text import clean_ocr_text


def test_normalizes_unicode_spacing_and_line_breaks():
    decomposed = unicodedata.normalize("NFD", "Cộng hòa")
    raw = f"  {decomposed}   Việt Nam\r\nSố:   123  \r\n"

    assert clean_ocr_text(raw) == "Cộng hòa Việt Nam\nSố: 123"


def test_repairs_common_vietnamese_mojibake():
    assert clean_ocr_text("VÄƒn báº£n tiáº¿ng Viá»‡t") == "Văn bản tiếng Việt"


def test_repairs_mojibake_inside_other_correct_vietnamese_text():
    assert clean_ocr_text("Đã đúng\nVÄƒn báº£n") == "Đã đúng Văn bản"


def test_removes_noise_and_joins_soft_wrapped_prose():
    raw = "Nội dung bị ngắt giữa\nhai dòng không cần thiết\n||||\n---\n\nĐoạn mới."

    assert clean_ocr_text(raw) == "Nội dung bị ngắt giữa hai dòng không cần thiết\n\nĐoạn mới."


def test_preserves_meaningful_document_structure():
    raw = (
        "THÔNG TIN HÓA ĐƠN\n"
        "Họ và tên: Nguyễn Văn A\n"
        "Ngày 20/10/2026\n"
        "Điện thoại: 0901 234 567\n"
        "TỔNG CỘNG: 1.000.000 đ"
    )

    assert clean_ocr_text(raw) == raw


def test_empty_input_returns_none():
    assert clean_ocr_text(None) is None
    assert clean_ocr_text(" \n --- \n") is None


def test_reduces_long_all_caps_prose_but_keeps_short_heading():
    raw = "THÔNG BÁO\nĐÂY LÀ MỘT ĐOẠN VĂN BẢN DÀI BỊ OCR NHẬN THÀNH TOÀN CHỮ HOA"

    assert clean_ocr_text(raw) == (
        "THÔNG BÁO\nĐây là một đoạn văn bản dài bị ocr nhận thành toàn chữ hoa"
    )


def test_document_response_exposes_raw_cleaned_and_legacy_fields():
    now = datetime.now(timezone.utc)
    response = DocumentOut(
        id="doc-1",
        filename="sample.pdf",
        content_type="application/pdf",
        file_size=100,
        status="processed",
        ocr_text="VÄƒn  báº£n",
        created_at=now,
        updated_at=now,
    ).model_dump()

    assert response["ocr_text"] == "VÄƒn  báº£n"
    assert response["ocr_text_raw"] == "VÄƒn  báº£n"
    assert response["ocr_text_cleaned"] == "Văn bản"
