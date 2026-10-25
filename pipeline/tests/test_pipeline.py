import io
import subprocess
from pathlib import Path

import pytest
from PIL import Image

from document_pipeline.config import PipelineConfig
from document_pipeline.errors import PipelineError
from document_pipeline.extraction import extract
from document_pipeline.models import Token
from document_pipeline.normalization import normalize
from document_pipeline.preprocessing import PreparedImage, prepare_image
from document_pipeline.tesseract import TSV_HEADER, execute, parse_tsv, probe, verify_models


def words(lines):
    tokens = []
    for index, line in enumerate(lines):
        for word in line.split():
            tokens.append(
                Token(
                    token_id=str(len(tokens)),
                    line_id=str(index),
                    text=word,
                    confidence=0.8,
                    box=(0.0, 0.0, 1.0, 1.0),
                )
            )
    return tuple(tokens)


def test_extraction_preserves_zeros_multiline_and_conflicting_candidates():
    tokens = words(
        [
            "Biểu mẫu minh họa nội dung và danh tính hư cấu",
            "Họ và tên: Nguyễn An",
            "Mã sinh viên: 0012",
            "Nội dung đề nghị: Xin xác nhận",
            "đang theo học",
            "Ngày làm đơn: 24/10/2026",
        ]
    )
    result = {field.field_id: field for field in extract(tokens, "don_de_nghi")}
    assert result["student_id"].normalized_value == "0012"
    assert result["request_content"].normalized_value == "Xin xác nhận đang theo học"
    assert result["request_content"].evidence_token_ids
    conflict = {
        field.field_id: field
        for field in extract(
            words(
                [
                    "Số hóa đơn: 001",
                    "Số hóa đơn: 002",
                    "Tổng thanh toán: 1.250.000 VND",
                ]
            ),
            "hoa_don",
        )
    }
    assert conflict["invoice_number"].normalized_value is None
    assert conflict["invoice_number"].reason_codes == ("AMBIGUOUS_CANDIDATES",)
    assert conflict["total_amount"].normalized_value == 1250000
    assert conflict["currency"].normalized_value == "VND"


def test_absent_no_fabricated_currency_and_unknown_confidence():
    fields = {field.field_id: field for field in extract(words(["Tổng tiền: 0"]), "hoa_don")}
    assert fields["total_amount"].normalized_value == 0
    assert fields["currency"].normalized_value is None
    assert fields["seller_name"].ocr_score is None
    assert all(field.ocr_score is None for field in extract((), "hoa_don"))


def test_low_score_abstention_keeps_evidence_without_inventing_probability():
    low = tuple(token.model_copy(update={"confidence": 0.2}) for token in words(["Người bán: ee"]))
    field = next(
        field
        for field in extract(low, "hoa_don", minimum_ocr_score=0.5)
        if field.field_id == "seller_name"
    )
    assert field.normalized_value is None and field.raw_value is None
    assert field.observation == "unknown"
    assert field.ocr_score == 0.2 and field.evidence_token_ids
    assert "LOW_OCR_EVIDENCE" in field.reason_codes


def test_label_folding_keeps_original_unicode_value_offsets():
    fields = {
        field.field_id: field
        for field in extract(
            words(
                [
                    "Họ và tên: Straße An Ngày sinh: 12/03/2005",
                ]
            ),
            "don_de_nghi",
        )
    }
    assert fields["full_name"].raw_value == "Straße An"
    assert fields["date_of_birth"].normalized_value == "2005-03-12"


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("invoice_date", "31/02/2026", "31/02/2026"),
        ("invoice_date", "29/02/2024", "2024-02-29"),
        ("total_amount", "1.25", "1.25"),
        ("total_amount", "-100", "-100"),
        ("total_amount", "9007199254740992", "9007199254740992"),
        ("total_amount", "1,250,000", 1250000),
        ("student_id", "00123", "00123"),
    ],
)
def test_normalization(field, value, expected):
    assert normalize(field, value) == expected


def image_data():
    output = io.BytesIO()
    Image.new("RGB", (80, 40), "white").save(output, format="PNG")
    return output.getvalue()


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_preprocessing_rotations_project_to_source(rotation):
    config = PipelineConfig(rotation=rotation, scale=1.5)
    prepared = prepare_image(image_data(), config)
    assert (prepared.width, prepared.height) == (80, 40)
    assert prepared.source_box((0, 0, prepared.processed_width, prepared.processed_height)) == (
        0,
        0,
        80,
        40,
    )
    if rotation == 90:
        # Upper-left processed corner maps to lower-left source corner.
        assert prepared.source_box((0, 0, 15, 15)) == (0, 30, 10, 40)


def test_image_content_limits_and_format():
    for content, config, expected in (
        (b"not an image", PipelineConfig(), "INVALID_DOCUMENT"),
        (image_data(), PipelineConfig(max_upload_bytes=10), "FILE_TOO_LARGE"),
        (image_data(), PipelineConfig(max_image_pixels=100), "IMAGE_TOO_LARGE"),
    ):
        with pytest.raises(PipelineError) as caught:
            prepare_image(content, config)
        assert caught.value.code == expected


def test_tsv_geometry_scores_and_corruption():
    page = PreparedImage(b"", 100, 100, 100, 100, {"rotation": 0})
    header = "\t".join(TSV_HEADER) + "\n"
    row = "5\t1\t1\t1\t1\t1\t10\t20\t30\t10\t80\tHello\n"
    token = parse_tsv((header + row).encode(), page)[0]
    assert token.box == (10, 20, 40, 30)
    assert token.confidence == 0.8
    assert (
        parse_tsv((header + row.replace("\t80\t", "\t-1\t")).encode(), page)[0].confidence is None
    )
    for invalid in (
        b"wrong",
        (header + row.replace("\t80\t", "\tnan\t")).encode(),
        (header + row.replace("\t30\t", "\t300\t")).encode(),
    ):
        with pytest.raises(PipelineError):
            parse_tsv(invalid, page)


def test_engine_failure_timeout_and_v_prefixed_version(tmp_path, monkeypatch):
    with pytest.raises(PipelineError, match="model"):
        verify_models(tmp_path)
    monkeypatch.setattr("document_pipeline.tesseract.verify_models", lambda directory: {})
    monkeypatch.setattr(
        "document_pipeline.tesseract.execute",
        lambda *args: subprocess.CompletedProcess([], 0, b"tesseract v5.4.0.20240606\n", b""),
    )
    assert probe("unused", tmp_path)["engine_version"] == "5.4.0.20240606"

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("native", 1)

    monkeypatch.setattr(subprocess, "run", timeout)
    with pytest.raises(PipelineError) as caught:
        execute(["unused"], 1)
    assert caught.value.code == "PROCESSING_TIMEOUT"


def test_inference_package_never_imports_gold_or_web():
    import document_pipeline

    for path in Path(document_pipeline.__file__).parent.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert "from docintel" not in source
        assert "import fastapi" not in source
        assert "annotation_path" not in source
        assert "gold.json" not in source
