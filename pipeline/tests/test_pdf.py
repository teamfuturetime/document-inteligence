import io
from pathlib import Path

import pypdfium2 as pdfium
import pytest
from PIL import Image
from pypdfium2 import raw

from document_pipeline.config import PipelineConfig
from document_pipeline.errors import PipelineError
from document_pipeline.preprocessing import prepare_image

FIXTURES = Path(__file__).parent / "fixtures/pdf"


def blank_pdf(*, width=72, height=144, pages=1, rotation=0):
    stream = io.BytesIO()
    with pdfium.PdfDocument.new() as document:
        for _ in range(pages):
            page = document.new_page(width, height)
            raw.FPDFPage_SetRotation(page, rotation // 90)
            page.close()
        document.save(stream)
    return stream.getvalue()


@pytest.mark.parametrize(
    ("filename", "code"),
    [("encrypted.pdf", "PDF_ENCRYPTED"), ("empty-password.pdf", "PDF_ENCRYPTED")],
)
def test_encrypted_pdf_is_rejected(filename, code):
    with pytest.raises(PipelineError) as error:
        prepare_image((FIXTURES / filename).read_bytes(), PipelineConfig())
    assert error.value.code == code


@pytest.mark.parametrize(
    ("make_data", "config", "code"),
    [
        (lambda: b"%PDF-1.7\ntruncated", {}, "INVALID_PDF"),
        (lambda: b"%PDF-1.7\ninvalid\n%%EOF\n", {}, "INVALID_PDF"),
        (lambda: blank_pdf(pages=2), {}, "PDF_PAGE_COUNT"),
        (lambda: blank_pdf(width=3000, height=72), {}, "IMAGE_TOO_LARGE"),
        (blank_pdf, {"max_image_pixels": 79_999}, "IMAGE_TOO_LARGE"),
        (blank_pdf, {"max_upload_bytes": 100}, "FILE_TOO_LARGE"),
        (blank_pdf, {"timeout_seconds": 0.001}, "PROCESSING_TIMEOUT"),
    ],
)
def test_pdf_input_budgets(make_data, config, code):
    with pytest.raises(PipelineError) as error:
        prepare_image(make_data(), PipelineConfig(**config))
    assert error.value.code == code


def test_jpeg_still_uses_the_exif_preview_frame():
    stream = io.BytesIO()
    Image.new("RGB", (80, 40), "white").save(stream, format="JPEG")
    preview = prepare_image(stream.getvalue(), PipelineConfig())
    assert (preview.width, preview.height) == (80, 40)
    assert preview.metadata["source_frame"] == "exif_normalized_pixels_top_left"


def test_pdf_rotation_and_scale_project_to_the_preview_frame():
    data = blank_pdf(rotation=90)
    preview = prepare_image(data, PipelineConfig())
    ocr = prepare_image(data, PipelineConfig(rotation=90, scale=1.5))
    assert (preview.width, preview.height) == (400, 200)
    assert (ocr.width, ocr.height) == (preview.width, preview.height)
    assert (ocr.processed_width, ocr.processed_height) == (300, 600)
    assert ocr.source_box((30, 150, 90, 300)) == (100.0, 140.0, 200.0, 180.0)
    assert preview.metadata["source_frame"] == "pdf_raster_pixels_top_left"
    assert preview.metadata["pdf_dpi"] == 200
    assert preview.metadata["pdfium_version"]
    with Image.open(io.BytesIO(preview.png)) as image:
        assert image.size == (400, 200)
        assert image.getpixel((0, 0)) == 255
