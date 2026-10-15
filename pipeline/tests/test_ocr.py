import io
import subprocess
import sys

from PIL import Image
import pytest

from document_contracts.models import OCRPage
from document_pipeline import ocr
from document_pipeline.ocr import OCRConfig, OCRError, parse_tsv, recognize, run_engine
from document_pipeline.preprocessing import PreparedPage

HEADER = "\t".join(ocr.TSV_HEADER) + "\n"
WORD = "5\t1\t1\t1\t1\t1\t10\t20\t30\t15\t96.25\tHóa\n"
STRUCTURE = "1\t1\t0\t0\t0\t0\t0\t0\t100\t60\t-1\t\n"


@pytest.fixture
def page():
    return PreparedPage(Image.new("L", (100, 60), "white"), {
        "to_original": [-1., 0., 100., 0., 1., 0., 0., 0., 1.],
        "source_coordinate_space": "raw_image_pixels",
    })


def contract_page():
    return OCRPage(page=1, width=100, height=60,
                   to_original=[1., 0., 0., 0., 1., 0., 0., 0., 1.], tokens=[])


def test_parse_words_preserves_order_unicode_boxes_and_confidence():
    unknown = WORD.replace("96.25", "-1").replace("Hóa", "đơn")
    tokens = parse_tsv((HEADER + STRUCTURE + WORD + unknown).encode(), contract_page())
    assert [token.text for token in tokens] == ["Hóa", "đơn"]
    assert [token.confidence for token in tokens] == [.9625, None]
    assert tokens[0].box.model_dump() == {"x0": 10, "y0": 20, "x1": 40, "y1": 35}


@pytest.mark.parametrize("data", [
    b"", b"not TSV", b"\xff", HEADER.encode() + b"truncated\n",
    (HEADER + WORD.replace("96.25", "nan")).encode(),
    (HEADER + WORD.replace("96.25", "inf")).encode(),
    (HEADER + WORD.replace("96.25", "101")).encode(),
    (HEADER + WORD.replace("96.25", "-2")).encode(),
    (HEADER + WORD.replace("5\t1\t", "5\t2\t", 1)).encode(),
    (HEADER + WORD.replace("5\t1\t", "6\t1\t", 1)).encode(),
    (HEADER + WORD.replace("\t30\t15\t", "\t300\t15\t")).encode(),
    (HEADER + WORD.replace("\t10\t20\t", "\t-1\t20\t")).encode(),
    (HEADER + WORD.replace("\t30\t15\t", "\t0\t15\t")).encode(),
])
def test_malformed_engine_output_is_rejected_without_partial_results(data):
    with pytest.raises(OCRError) as error:
        parse_tsv(data, contract_page())
    assert error.value.code == "internal_error"


def test_no_text_is_an_empty_result_not_fabricated_tokens():
    assert parse_tsv((HEADER + STRUCTURE).encode(), contract_page()) == []


@pytest.fixture
def engine(monkeypatch):
    calls = []
    monkeypatch.setattr(ocr, "verify_models", lambda directory: {"vie": "test-vie", "eng": "test-eng"})
    def run(command, **kwargs):
        calls.append((command, kwargs))
        output = b"tesseract 5.5.2\nleptonica-test\n" if command[-1] == "--version" else (HEADER + WORD).encode()
        return subprocess.CompletedProcess(command, 0, output, b"")
    monkeypatch.setattr(ocr.subprocess, "run", run)
    return calls


def test_adapter_passes_explicit_settings_and_produces_real_contract(page, engine, tmp_path):
    run = recognize(page, tmp_path)
    assert run.result.mode == "real" and run.result.language == "vie+eng"
    assert run.result.page.to_original == page.metadata["to_original"]
    assert run.result.page.tokens[0].text == "Hóa"
    assert "tesseract-5.5.2" in run.result.ocr_version
    assert run.metadata["model_sha256"] == {"vie": "test-vie", "eng": "test-eng"}
    assert len(run.metadata["config_sha256"]) == 64
    command, options = engine[-1]
    assert command[1:3] == ["stdin", "stdout"]
    assert command[command.index("-l") + 1] == "vie+eng"
    assert command[command.index("--oem") + 1] == "1"
    assert command[command.index("--psm") + 1] == "3"
    assert command[-2:] == ["-c", "tessedit_create_tsv=1"]
    assert options["env"]["OMP_THREAD_LIMIT"] == "1"
    assert options["timeout"] <= 30
    with Image.open(io.BytesIO(options["input"])) as image:
        assert image.mode == "L" and image.size == (100, 60)


def test_pdf_raster_dpi_is_used_and_changes_config_identity(page, engine, tmp_path):
    first = recognize(page, tmp_path)
    page.metadata["pdf_dpi"] = 200
    second = recognize(page, tmp_path)
    assert second.metadata["config"]["effective_dpi"] == 200
    assert first.metadata["config_sha256"] != second.metadata["config_sha256"]
    assert engine[-1][0][engine[-1][0].index("--dpi") + 1] == "200"


def test_engine_failure_is_not_retried_or_replaced_with_mock(page, engine, monkeypatch, tmp_path):
    run = ocr.subprocess.run
    def fail(command, **kwargs):
        if command[-1] == "--version":
            return run(command, **kwargs)
        return subprocess.CompletedProcess(command, 1, b"", b"private-path and raw text")
    monkeypatch.setattr(ocr.subprocess, "run", fail)
    with pytest.raises(OCRError) as error:
        recognize(page, tmp_path)
    assert error.value.code == "ocr_unavailable"
    assert "private-path" not in str(error.value)


def test_unsupported_engine_is_unavailable(page, engine, monkeypatch, tmp_path):
    monkeypatch.setattr(ocr.subprocess, "run", lambda *args, **kwargs:
                        subprocess.CompletedProcess(args, 0, b"tesseract 4.1.0\n", b""))
    with pytest.raises(OCRError) as error:
        recognize(page, tmp_path)
    assert error.value.code == "ocr_unavailable"


def test_missing_models_fail_without_starting_engine(page, tmp_path):
    with pytest.raises(OCRError) as error:
        recognize(page, tmp_path, executable="never-start-this-executable")
    assert error.value.code == "ocr_unavailable"


def test_missing_engine_has_stable_error(tmp_path):
    with pytest.raises(OCRError) as error:
        run_engine([str(tmp_path / "missing-tesseract")], 1)
    assert error.value.code == "ocr_unavailable"


def test_real_subprocess_deadline_kills_worker():
    with pytest.raises(OCRError) as error:
        run_engine([sys.executable, "-c", "import time; time.sleep(60)"], .05)
    assert error.value.code == "processing_timeout"


def test_expired_budget_does_not_launch_engine():
    with pytest.raises(OCRError) as error:
        run_engine(["never-start"], 0)
    assert error.value.code == "processing_timeout"


@pytest.mark.parametrize("config", [
    {"psm": 0}, {"psm": 2}, {"psm": 12}, {"psm": True},
    {"image_dpi": 0}, {"image_dpi": 301},
    {"timeout_seconds": 0}, {"timeout_seconds": float("nan")},
])
def test_invalid_config_is_rejected(config):
    with pytest.raises(ValueError):
        OCRConfig(**config)
