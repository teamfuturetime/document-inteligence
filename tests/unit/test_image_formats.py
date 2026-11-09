from io import BytesIO

import numpy as np
import pytest
from PIL import Image

from app.core.config import Settings
from app.services import file_validation
from app.services.file_validation import FileValidationError, validate_upload
from ai_service.pipeline import DocumentPipeline, PipelineError
from ai_service.ocr.engine import OCRResult
from document_images import open_image, rgb_page


@pytest.mark.parametrize(
    "extension,mime,pages",
    [
        ("webp", "image/webp", 1),
        ("bmp", "image/bmp", 1),
        ("tif", "image/tiff", 1),
        ("tiff", "image/tiff", 3),
        ("png", "image/png", 1),
        ("jpg", "image/jpeg", 1),
        ("jpeg", "image/jpeg", 1),
        ("BMP", "image/x-ms-bmp", 1),
        ("tiff", "", 1),
        ("tif", "application/octet-stream", 1),
    ],
)
def test_real_images_pass_validation_and_decode(
    tmp_path, image_bytes, extension, mime, pages
):
    content = image_bytes(extension.lower(), pages=pages)
    validate_upload("scan." + extension, content, mime)
    path = tmp_path / ("scan." + extension)
    path.write_bytes(content)
    loaded = list(DocumentPipeline()._load_pages(path))
    assert len(loaded) == pages
    assert all(page.shape == (60, 80, 3) and page.dtype == np.uint8 for page in loaded)


@pytest.mark.parametrize("extension", ["png", "jpg", "webp", "bmp", "tiff"])
def test_truncated_images_rejected(image_bytes, extension):
    data = image_bytes(extension)
    with pytest.raises(FileValidationError):
        validate_upload("scan." + extension, data[: max(16, len(data) // 2)])


@pytest.mark.parametrize(
    "filename,mime",
    [
        ("scan.gif", "image/gif"),
        ("scan.heic", "image/heic"),
        ("scan.heif", "image/heif"),
        ("scan.webp", "text/plain"),
        ("scan.bmp", "image/webp"),
        ("scan.png", "image/png"),
        ("scan.tiff", "image/tiff"),
    ],
)
def test_unsupported_or_spoofed_images_rejected(image_bytes, filename, mime):
    with pytest.raises(FileValidationError):
        validate_upload(filename, image_bytes("webp"), mime)


def test_image_limits_cover_later_pages_and_total(tmp_path, image_bytes, monkeypatch):
    monkeypatch.setattr(file_validation.settings, "MAX_IMAGE_PIXELS", 5000)
    monkeypatch.setattr(file_validation.settings, "MAX_IMAGE_PAGES", 2)
    monkeypatch.setattr(file_validation.settings, "MAX_TOTAL_IMAGE_PIXELS", 20000)
    with pytest.raises(FileValidationError, match="pixel"):
        validate_upload("large.png", image_bytes(size=(100, 100)))
    with pytest.raises(FileValidationError, match="trang"):
        validate_upload("many.tiff", image_bytes("tiff", pages=3))
    monkeypatch.setattr(file_validation.settings, "MAX_TOTAL_IMAGE_PIXELS", 5000)
    with pytest.raises(FileValidationError, match="Tổng"):
        validate_upload("total.tiff", image_bytes("tiff", pages=2))
    output = BytesIO()
    Image.new("RGB", (10, 10)).save(
        output,
        format="TIFF",
        save_all=True,
        append_images=[Image.new("RGB", (100, 100))],
    )
    with pytest.raises(FileValidationError, match="pixel"):
        validate_upload("later.tiff", output.getvalue())


def test_decompression_bomb_rejected(image_bytes, monkeypatch):
    data = image_bytes(size=(80, 60))
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 3000)
    with pytest.raises(FileValidationError, match="giới hạn"):
        validate_upload("bomb.png", data)


def test_png_with_corrupt_chunk_crc_rejected(image_bytes):
    data = bytearray(image_bytes())
    offset = data.index(b"IDAT")
    length = int.from_bytes(data[offset - 4:offset], "big")
    data[offset + 4 + length] ^= 0xFF
    with pytest.raises(FileValidationError):
        validate_upload("corrupt.png", bytes(data), "image/png")


@pytest.mark.parametrize("extension", ["png", "tiff"])
def test_16_bit_grayscale_keeps_tones(tmp_path, extension):
    pixels = np.array([[0, 32768, 65535]], dtype=np.uint16)
    path = tmp_path / ("depth." + extension)
    Image.fromarray(pixels).save(path)
    decoded = list(DocumentPipeline()._load_pages(path))[0]
    assert decoded[0, :, 0].tolist() == [0, 127, 255]


@pytest.mark.parametrize("compression", ["raw", "tiff_lzw", "tiff_adobe_deflate", "packbits"])
def test_compressed_multipage_tiff(tmp_path, image_bytes, compression):
    content = image_bytes("tiff", pages=2, colors=["red", "blue"], compression=compression)
    validate_upload("compressed.tiff", content, "image/tiff")
    path = tmp_path / "compressed.tiff"
    path.write_bytes(content)
    pages = list(DocumentPipeline()._load_pages(path))
    assert len(pages) == 2
    assert pages[0][0, 0].tolist() == [0, 0, 255]
    assert pages[1][0, 0].tolist() == [255, 0, 0]


@pytest.mark.parametrize("extension", ["png", "webp", "tiff"])
def test_transparent_background_becomes_white(tmp_path, image_bytes, extension):
    path = tmp_path / ("transparent." + extension)
    path.write_bytes(image_bytes(extension, mode="RGBA", colors=[(0, 0, 0, 0)]))
    loaded = list(DocumentPipeline()._load_pages(path))
    assert np.all(loaded[0] == 255)


@pytest.mark.parametrize("extension", ["jpg", "png", "tiff"])
def test_orientation_applied_once(image_bytes, extension):
    exif = Image.Exif()
    exif[274] = 6
    data = image_bytes(extension, exif=exif)
    with open_image(
        BytesIO(data), extension, max_pixels=10000, max_pages=20, max_total_pixels=20000
    ) as (image, count):
        assert count == 1
        assert rgb_page(image).size == (60, 80)


def test_multipage_tiff_ocr_order_and_contract(tmp_path, image_bytes, monkeypatch):
    import ai_service.pipeline as pipeline

    # Keep real decoding, but bypass expensive candidates so distinct pixels
    # prove that page 2 is actually read rather than page 1 being repeated.
    monkeypatch.setattr(pipeline, "deskew", lambda image: image)
    monkeypatch.setattr(
        pipeline, "build_preprocessing_candidates", lambda image: [image]
    )
    seen = []

    class Engine:
        prefer = "test"

        def recognize_candidates(self, candidates, *, page_number, **kwargs):
            seen.append((page_number, candidates[0][0, 0].tolist()))
            return OCRResult(
                text=f"Trang {page_number}",
                engine="test",
                pages=[
                    {
                        "page_number": page_number,
                        "width": 80,
                        "height": 60,
                        "blocks": [],
                    }
                ],
            )

    path = tmp_path / "pages.tiff"
    path.write_bytes(image_bytes("tiff", pages=2, colors=["red", "blue"]))
    result = DocumentPipeline(Engine()).process(path)
    assert seen == [(1, [0, 0, 255]), (2, [255, 0, 0])]
    assert result["ocr"]["text"] == "Trang 1\n\f\nTrang 2"
    assert [page["page_number"] for page in result["ocr"]["pages"]] == [1, 2]
    assert {
        "text",
        "engine",
        "mean_confidence",
        "quality",
        "config",
        "boxes",
        "pages",
    } == set(result["ocr"])
    assert "document_type" in result["classification"]
    assert set(result["extraction"]) == {"data", "assessment"}


def test_ai_pipeline_enforces_page_limit(tmp_path, image_bytes, monkeypatch):
    import ai_service.pipeline as pipeline

    monkeypatch.setattr(pipeline, "MAX_IMAGE_PAGES", 1)
    path = tmp_path / "many.tif"
    path.write_bytes(image_bytes("tif", pages=2))
    with pytest.raises(PipelineError):
        DocumentPipeline().process(path)


def test_extension_settings_accept_json_and_csv():
    assert Settings(ALLOWED_EXTENSIONS='["pdf","webp","tiff"]').ALLOWED_EXTENSIONS == [
        "pdf",
        "webp",
        "tiff",
    ]
    assert Settings(ALLOWED_EXTENSIONS="pdf,webp,tiff").ALLOWED_EXTENSIONS == [
        "pdf",
        "webp",
        "tiff",
    ]
