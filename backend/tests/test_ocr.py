"""Offline contract/error checks; subprocess output here is explicitly simulated."""

from hashlib import sha256
from io import BytesIO
from pathlib import Path
import socket
import subprocess
import sys

from PIL import Image
import pytest

from app.providers.contracts import ProviderError
from app.providers.ocr import OCRProvider
from app.providers.tesseract import TesseractOCRProvider, _invoke, parse_tsv
from app.schemas.extraction import DocumentInput
from app.schemas.ocr import OCRResult

HEADER = "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"


def tsv(width=20, height=20, word="Hóa", score="88.5") -> str:
    page = f"1\t1\t0\t0\t0\t0\t0\t0\t{width}\t{height}\t-1\t\n"
    return HEADER + page + f"5\t1\t1\t1\t1\t1\t1\t2\t6\t5\t{score}\t{word}\n"


@pytest.fixture(autouse=True)
def block_network(monkeypatch):
    def reject(*args, **kwargs):
        raise AssertionError("OCR tests must not open network connections")
    monkeypatch.setattr(socket.socket, "connect", reject)
    monkeypatch.setattr(socket.socket, "connect_ex", reject)
    monkeypatch.setattr(socket, "create_connection", reject)


@pytest.fixture
def document():
    buffer = BytesIO()
    Image.new("RGB", (20, 20), "white").save(buffer, format="PNG")
    return DocumentInput(document_id="synthetic", media_type="image/png", content=buffer.getvalue())


@pytest.fixture
def engine(tmp_path, monkeypatch):
    model_dir = tmp_path / "tessdata"
    model_dir.mkdir()
    (model_dir / "vie.traineddata").write_bytes(b"SYNTHETIC TEST MODEL - NOT FOR INFERENCE")
    executable = tmp_path / "tesseract"
    monkeypatch.setattr("app.providers.tesseract.shutil.which", lambda name: str(executable))
    state = {"raw_text": "Hóa\r\n", "word": "Hóa", "error": None, "calls": [], "output": None}

    def run(args, **kwargs):
        state["calls"].append((args, kwargs))
        assert kwargs["shell"] is False
        assert kwargs["timeout"] > 0
        if args[-1] == "--version":
            return subprocess.CompletedProcess(args, 0, b"tesseract test-build\n", b"")
        state["output"] = Path(args[2])
        assert "tessedit_create_txt=1" in args and "tessedit_create_tsv=1" in args
        if state["error"] is not None:
            raise state["error"]
        with Image.open(BytesIO(kwargs["input"])) as image:
            width, height = image.size
        state["output"].with_suffix(".txt").write_bytes(state["raw_text"].encode("utf-8"))
        raw = tsv(width, height, state["word"]) if state["word"] else tsv(width, height).split("5\t")[0]
        state["output"].with_suffix(".tsv").write_bytes(raw.encode("utf-8"))
        return subprocess.CompletedProcess(args, 0, b"", b"private stderr")

    monkeypatch.setattr("app.providers.tesseract.subprocess.run", run)
    return TesseractOCRProvider(tessdata_dir=model_dir), state


def test_ocr_contract_preserves_raw_text_geometry_and_native_score(document, engine):
    provider, state = engine
    before = document.model_dump()
    result = provider.recognize(document)

    assert isinstance(provider, OCRProvider)
    assert isinstance(result, OCRResult)
    assert result.raw_text == "Hóa\r\n"
    assert result.words[0].text == "Hóa"
    assert result.words[0].native_confidence == 88.5  # Not divided by 100.
    assert result.words[0].bbox.model_dump() == {"x0": 1, "y0": 2, "x1": 7, "y1": 7}
    assert result.metadata.provider.mode == "real"
    assert result.metadata.provider.implementation_version == "1.0.0"
    assert result.metadata.configuration["languages"] == "vie"
    assert result.metadata.model_sha256["vie"] == sha256(b"SYNTHETIC TEST MODEL - NOT FOR INFERENCE").hexdigest()
    assert result.input_sha256 == sha256(document.content).hexdigest()
    assert len(result.metadata.config_sha256) == 64
    assert result.metadata.pillow_version
    assert result.metadata.native_confidence_scale == "tesseract_word_0_100"
    assert not state["output"].parent.exists()
    assert OCRResult.model_validate_json(result.model_dump_json()) == result
    assert document.model_dump() == before
    assert "raw_values" not in result.model_dump()


def test_blank_image_is_success_with_no_text_warning(document, engine):
    provider, state = engine
    state.update(raw_text="", word="")
    result = provider.recognize(document)
    assert result.raw_text == ""
    assert result.words == []
    assert result.warnings == ["no_text"]


@pytest.mark.parametrize("content,media", [
    (b"not an image", "image/png"), (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8truncated", "image/jpeg"), (b"", "image/png"),
])
def test_corrupt_or_empty_image_is_rejected(content, media):
    document = DocumentInput.model_construct(document_id="bad", content=content, media_type=media)
    with pytest.raises(ProviderError, match="invalid_document"):
        TesseractOCRProvider().recognize(document)


def test_mime_must_match_decoded_format(document):
    wrong = document.model_copy(update={"media_type": "image/jpeg"})
    with pytest.raises(ProviderError, match="invalid_document"):
        TesseractOCRProvider().recognize(wrong)


def test_other_image_formats_are_not_accepted():
    buffer = BytesIO()
    Image.new("RGB", (20, 20)).save(buffer, format="GIF")
    with pytest.raises(ProviderError, match="invalid_document"):
        TesseractOCRProvider().recognize(DocumentInput(document_id="gif", media_type="image/png", content=buffer.getvalue()))


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf"), True])
def test_invalid_timeout_is_configuration_error(timeout):
    with pytest.raises(ValueError):
        TesseractOCRProvider(timeout_seconds=timeout)


def test_missing_executable_is_unavailable(document, monkeypatch):
    monkeypatch.setattr("app.providers.tesseract.shutil.which", lambda name: None)
    with pytest.raises(ProviderError, match="provider_unavailable"):
        TesseractOCRProvider().recognize(document)


def test_missing_language_is_unavailable(document, engine, tmp_path):
    with pytest.raises(ProviderError, match="provider_unavailable"):
        TesseractOCRProvider(tessdata_dir=tmp_path).recognize(document)


@pytest.mark.parametrize("error,code", [
    (subprocess.TimeoutExpired("synthetic-command", 0.1, stderr=b"private text"), "provider_timeout"),
    (FileNotFoundError("private path"), "provider_unavailable"),
])
def test_subprocess_errors_are_sanitized_and_temp_files_cleaned(document, engine, error, code, caplog):
    provider, state = engine
    state["error"] = error
    with pytest.raises(ProviderError) as raised:
        provider.recognize(document)
    assert str(raised.value) == code
    assert not state["output"].parent.exists()
    assert caplog.text == ""


def test_nonzero_exit_does_not_expose_stderr(monkeypatch):
    monkeypatch.setattr("app.providers.tesseract.subprocess.run",
                        lambda *args, **kwargs: subprocess.CompletedProcess(args, 1, b"", b"secret document text"))
    with pytest.raises(ProviderError) as raised:
        _invoke(["synthetic-command"], 1)
    assert str(raised.value) == "provider_failed"


def test_real_subprocess_timeout_is_enforced():
    # Real child process, not an assertion about OCR latency or a simulated exception.
    with pytest.raises(ProviderError, match="provider_timeout"):
        _invoke([sys.executable, "-c", "import time; time.sleep(10)"], 0.05)


@pytest.mark.parametrize("score", ["-2", "101", "nan", "inf", "bad"])
def test_bad_native_scores_are_not_accepted(score):
    with pytest.raises(ProviderError, match="provider_failed"):
        parse_tsv(tsv(score=score), 20, 20)


def test_native_unavailable_score_and_literal_quotes():
    result = parse_tsv(tsv(word='"Hóa"', score="-1"), 20, 20)
    assert result[0].native_confidence is None
    assert result[0].text == '"Hóa"'


@pytest.mark.parametrize("mutation", ["header", "page", "bounds", "zero_area", "duplicate_page", "missing_page", "extra_column"])
def test_malformed_tsv_cannot_become_valid_observations(mutation):
    raw = tsv()
    if mutation == "header":
        raw = raw.replace("page_num", "unknown")
    elif mutation == "page":
        raw = raw.replace("5\t1\t", "5\t2\t")
    elif mutation == "bounds":
        raw = raw.replace("\t1\t2\t6\t5\t", "\t19\t2\t6\t5\t")
    elif mutation == "zero_area":
        raw = raw.replace("\t1\t2\t6\t5\t", "\t1\t2\t0\t5\t")
    elif mutation == "duplicate_page":
        raw += raw.splitlines()[1] + "\n"
    elif mutation == "missing_page":
        raw = HEADER + raw.splitlines()[2] + "\n"
    else:
        raw = raw.rstrip("\n") + "\textra\n"
    with pytest.raises(ProviderError, match="provider_failed"):
        parse_tsv(raw, 20, 20)


def test_exif_orientation_and_transparency_use_display_coordinates(engine):
    provider, state = engine
    source = Image.new("RGB", (30, 20), "white")
    buffer = BytesIO()
    exif = source.getexif()
    exif[274] = 6
    source.save(buffer, format="JPEG", exif=exif)
    result = provider.recognize(DocumentInput(document_id="exif", media_type="image/jpeg", content=buffer.getvalue()))
    assert (result.width, result.height) == (20, 30)
    assert result.coordinate_space == "exif_transposed_rgb_white"
    assert result.input_sha256 != result.processed_image_sha256
    transparent = Image.new("RGBA", (20, 20), (0, 0, 0, 0))
    buffer = BytesIO()
    transparent.save(buffer, format="PNG")
    provider.recognize(DocumentInput(document_id="alpha", media_type="image/png", content=buffer.getvalue()))
    with Image.open(BytesIO(state["calls"][-1][1]["input"])) as image:
        assert image.getpixel((0, 0)) == (255, 255, 255)


def test_inconsistent_text_and_tokens_is_not_success(document, engine):
    provider, state = engine
    state["word"] = ""
    with pytest.raises(ProviderError, match="provider_failed"):
        provider.recognize(document)


def test_adapter_byte_limit(document):
    oversized = document.model_copy(update={"content": document.content + b" " * (10 * 1024 * 1024)})
    with pytest.raises(ProviderError, match="invalid_document"):
        TesseractOCRProvider().recognize(oversized)


def test_adapter_pixel_limit():
    buffer = BytesIO()
    Image.new("1", (5000, 5000), 1).save(buffer, format="PNG")
    with pytest.raises(ProviderError, match="invalid_document"):
        TesseractOCRProvider().recognize(DocumentInput(document_id="large", media_type="image/png", content=buffer.getvalue()))


def test_animated_png_is_not_silently_truncated_to_one_frame():
    buffer = BytesIO()
    Image.new("RGB", (20, 20), "white").save(
        buffer, format="PNG", save_all=True, append_images=[Image.new("RGB", (20, 20), "black")], duration=100,
    )
    with pytest.raises(ProviderError, match="invalid_document"):
        TesseractOCRProvider().recognize(DocumentInput(document_id="animated", media_type="image/png", content=buffer.getvalue()))
