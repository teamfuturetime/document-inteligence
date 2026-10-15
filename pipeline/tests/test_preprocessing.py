import io
import subprocess
import sys
from pathlib import Path

from PIL import Image
from pypdf import PdfWriter
import pytest

from document_pipeline.preprocessing import (
    MAX_FILE_BYTES, PreprocessingConfig, PreprocessingError, prepare_document,
)

SAMPLES = Path(__file__).resolve().parents[2] / "data/samples"


@pytest.mark.parametrize("extension", ["png", "jpg", "pdf"])
def test_real_decoders_return_detached_grayscale_pages(extension):
    page = prepare_document((SAMPLES / f"synthetic-001.{extension}").read_bytes())
    assert page.image.mode == "L"
    assert page.image.size == (1200, 1600)
    assert page.image.getpixel((0, 0)) >= 250
    assert len(page.metadata["input_sha256"]) == 64
    assert len(page.metadata["config_sha256"]) == 64
    assert page.metadata["preprocessing_version"] == "1.0.0"
    assert page.metadata["to_original"] == [1, 0, 0, 0, 1, 0, 0, 0, 1]


@pytest.mark.parametrize("orientation", range(1, 9))
def test_exif_orientation_and_transform_map_pixels_to_source(orientation):
    source = Image.new("L", (4, 3))
    for y in range(3):
        for x in range(4):
            source.putpixel((x, y), 10 + 30 * y + 5 * x)
    exif = Image.Exif(); exif[274] = orientation
    stream = io.BytesIO(); source.save(stream, format="PNG", exif=exif)
    page = prepare_document(stream.getvalue())
    assert page.image.size == ((3, 4) if orientation >= 5 else (4, 3))
    matrix = page.metadata["to_original"]
    for y in range(page.image.height):
        for x in range(page.image.width):
            # Transform pixel centers; box-edge coordinates use the same matrix.
            original_x = matrix[0] * (x + .5) + matrix[1] * (y + .5) + matrix[2]
            original_y = matrix[3] * (x + .5) + matrix[4] * (y + .5) + matrix[5]
            assert page.image.getpixel((x, y)) == source.getpixel((int(original_x), int(original_y)))


def test_transparent_background_becomes_white():
    stream = io.BytesIO()
    Image.new("RGBA", (10, 10), (0, 0, 0, 0)).save(stream, format="PNG")
    assert prepare_document(stream.getvalue()).image.getextrema() == (255, 255)


def test_animated_png_is_rejected_instead_of_silently_using_first_frame():
    stream = io.BytesIO()
    Image.new("RGB", (10, 10), "white").save(
        stream, format="PNG", save_all=True,
        append_images=[Image.new("RGB", (10, 10), "black")], duration=100,
    )
    with pytest.raises(PreprocessingError) as error:
        prepare_document(stream.getvalue())
    assert error.value.code == "multiple_pages"


@pytest.mark.parametrize("data,code", [
    (b"", "invalid_document"),
    (b"text pretending to be png", "unsupported_media_type"),
    (b"\x89PNG\r\n\x1a\nbroken", "invalid_document"),
    (b"%PDF-broken", "invalid_document"),
    (b"x" * (MAX_FILE_BYTES + 1), "file_too_large"),
])
def test_invalid_input_returns_stable_errors(data, code):
    with pytest.raises(PreprocessingError) as error:
        prepare_document(data)
    assert error.value.code == code


def pdf_bytes(pages=1, encrypted=False, width=300, height=400):
    with PdfWriter() as writer, io.BytesIO() as stream:
        for _ in range(pages):
            writer.add_blank_page(width=width, height=height)
        if encrypted:
            writer.encrypt("synthetic")
        writer.write(stream)
        return stream.getvalue()


@pytest.mark.parametrize("data,code", [
    (pdf_bytes(pages=2), "multiple_pages"),
    (pdf_bytes(encrypted=True), "invalid_document"),
    (pdf_bytes(width=100000, height=100000), "image_too_large"),
])
def test_pdf_limits_before_raster_allocation(data, code):
    with pytest.raises(PreprocessingError) as error:
        prepare_document(data)
    assert error.value.code == code


def test_image_pixel_budget_applies_before_decode():
    stream = io.BytesIO()
    Image.new("L", (40, 40)).save(stream, format="PNG")
    with pytest.raises(PreprocessingError) as error:
        prepare_document(stream.getvalue(), PreprocessingConfig(max_pixels=1000))
    assert error.value.code == "image_too_large"


def test_configuration_and_output_are_reproducible():
    data = (SAMPLES / "synthetic-001.png").read_bytes()
    first, second = prepare_document(data), prepare_document(data)
    assert first.metadata == second.metadata
    assert first.image.tobytes() == second.image.tobytes()
    assert PreprocessingConfig(pdf_dpi=200).sha256 != PreprocessingConfig().sha256


def test_pdf_dpi_changes_dimensions_and_is_recorded():
    page = prepare_document(pdf_bytes(width=72, height=144), PreprocessingConfig(pdf_dpi=150))
    assert page.image.size == (150, 300)
    assert page.metadata["pdf_dpi"] == 150
    assert page.metadata["source_coordinate_space"] == "pdf_raster_pixels"


def test_timeout_kills_and_reaps_a_real_worker(monkeypatch):
    run = subprocess.run
    def sleeping_worker(command, **kwargs):
        return run([sys.executable, "-c", "import time; time.sleep(60)"], **kwargs)
    monkeypatch.setattr("document_pipeline.preprocessing.subprocess.run", sleeping_worker)
    with pytest.raises(PreprocessingError) as error:
        prepare_document(b"input", PreprocessingConfig(timeout_seconds=.05))
    assert error.value.code == "processing_timeout"


def test_failed_worker_does_not_expose_stderr(monkeypatch):
    monkeypatch.setattr("document_pipeline.preprocessing.subprocess.run", lambda *args, **kwargs:
                        subprocess.CompletedProcess(args, 1, stdout=b"", stderr=b"synthetic-private-path"))
    with pytest.raises(PreprocessingError) as error:
        prepare_document(b"input")
    assert error.value.code == "internal_error"
    assert "synthetic-private-path" not in str(error.value)


@pytest.mark.parametrize("options", [
    {"pdf_dpi": 0}, {"pdf_dpi": 301}, {"max_pixels": 0},
    {"max_pixels": 25_000_001}, {"timeout_seconds": float("inf")}, {"timeout_seconds": -1},
])
def test_invalid_config_rejected(options):
    with pytest.raises(ValueError):
        PreprocessingConfig(**options)
