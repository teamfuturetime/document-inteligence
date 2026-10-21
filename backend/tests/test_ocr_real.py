"""Real local inference; no mocks or network. Requires installed Tesseract + vie."""

from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import shutil
import socket
import subprocess
import sys

from PIL import Image
import pytest

from app.providers.contracts import ProviderError
from app.providers.tesseract import TesseractOCRProvider
from app.schemas.extraction import DocumentInput
from app.schemas.ocr import OCRResult

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "ocr-smoke"
pytestmark = pytest.mark.ocr_real


@pytest.fixture
def provider(request, monkeypatch):
    def reject(*args, **kwargs):
        raise AssertionError("Real OCR must remain offline")
    monkeypatch.setattr(socket.socket, "connect", reject)
    monkeypatch.setattr(socket, "create_connection", reject)
    executable = shutil.which(request.config.getoption("--ocr-executable"))
    directory = request.config.getoption("--ocr-tessdata-dir")
    tessdata = Path(directory) if directory else (Path(executable).parent / "tessdata" if executable else Path("missing-tessdata"))
    if not executable or not (tessdata / "vie.traineddata").is_file():
        if request.config.getoption("--require-real-ocr"):
            pytest.fail("Real OCR required: install Tesseract/vie or pass --ocr-tessdata-dir")
        pytest.skip("Local Tesseract/vie not available; use --require-real-ocr to enforce")
    return TesseractOCRProvider(executable, tessdata_dir=tessdata)


@pytest.mark.parametrize("name,media", [("invoice_vi.png", "image/png"), ("invoice_vi.jpg", "image/jpeg")])
def test_real_vietnamese_invoice_recognition(provider, name, media):
    document = DocumentInput(document_id=name, media_type=media, content=(DATA / name).read_bytes())
    result = provider.recognize(document)
    # Stable smoke anchors, not a claim of perfect OCR or field-level accuracy.
    for phrase in ("HÓA ĐƠN BÁN HÀNG", "Cửa hàng Mây Việt", "HD-0000123", "03/04/2026", "125.000 VND"):
        assert phrase in result.raw_text
    assert result.words and all(word.page == 1 for word in result.words)
    assert result.metadata.provider.mode == "real"
    assert result.metadata.engine_version.startswith("tesseract ")
    assert result.metadata.model_sha256["vie"] == sha256((provider.tessdata_dir / "vie.traineddata").read_bytes()).hexdigest()
    assert OCRResult.model_validate_json(result.model_dump_json()) == result


def test_real_blank_image(provider):
    result = provider.recognize(DocumentInput(document_id="blank", media_type="image/png", content=(DATA / "blank.png").read_bytes()))
    assert not result.raw_text.strip()
    assert result.words == []
    assert result.warnings == ["no_text"]


def test_corrupt_image_is_not_fake_success(provider):
    with pytest.raises(ProviderError, match="invalid_document"):
        provider.recognize(DocumentInput(document_id="bad", media_type="image/png", content=b"not an image"))


def test_real_rotated_jpeg_exif(provider):
    with Image.open(DATA / "invoice_vi.png") as image:
        rotated = image.transpose(Image.Transpose.ROTATE_90)
        exif = rotated.getexif()
        exif[274] = 6
        buffer = BytesIO()
        rotated.save(buffer, format="JPEG", quality=95, exif=exif)
        expected_size = image.size
    result = provider.recognize(DocumentInput(document_id="exif", media_type="image/jpeg", content=buffer.getvalue()))
    assert (result.width, result.height) == expected_size
    assert "Cửa hàng Mây Việt" in result.raw_text


def test_real_cli_outputs_ocr_json(provider):
    command = [sys.executable, "-m", "app.ocr_cli", str(DATA / "invoice_vi.png"),
               "--tesseract", provider.executable, "--tessdata-dir", str(provider.tessdata_dir)]
    process = subprocess.run(command, cwd=ROOT / "backend", capture_output=True, timeout=35, check=True)
    result = OCRResult.model_validate_json(process.stdout)
    assert "HD-0000123" in result.raw_text
    assert process.stderr == b""


def test_manifest_describes_only_synthetic_matching_images():
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["synthetic"] is True
    assert manifest["font"]["redistributed"] is False
    assert len({item["id"] for item in manifest["images"]}) == 3
    for item in manifest["images"]:
        data = (DATA / item["file"]).read_bytes()
        assert sha256(data).hexdigest() == item["sha256"]
        with Image.open(BytesIO(data)) as image:
            assert image.size == (item["width"], item["height"])
