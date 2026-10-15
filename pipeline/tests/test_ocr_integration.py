"""Real native engine tests; opting in makes missing prerequisites a failure."""

from pathlib import Path
import unicodedata

from PIL import Image
import pytest

from document_contracts.models import OCRResult
from document_pipeline.ocr import recognize
from document_pipeline.preprocessing import PreparedPage, prepare_document

pytestmark = pytest.mark.ocr_integration
SAMPLES = Path(__file__).resolve().parents[2] / "data/samples"


@pytest.mark.parametrize("filename", [
    "synthetic-001.png", "synthetic-001.jpg", "synthetic-001.pdf", "synthetic-002-missing.png",
])
def test_real_vietnamese_engine_on_supported_documents(filename, tessdata_dir):
    run = recognize(prepare_document((SAMPLES / filename).read_bytes()), tessdata_dir)
    result = OCRResult.model_validate_json(run.result.model_dump_json())
    text = unicodedata.normalize("NFC", " ".join(token.text for token in result.page.tokens))
    assert result.mode == "real" and result.page.width == 1200 and result.page.height == 1600
    assert "HÓA ĐƠN" in text.upper()
    assert any(character in text.lower() for character in "độếệ")
    assert any(token.confidence is not None for token in result.page.tokens)
    assert run.metadata["engine_version"].startswith("5.")
    assert set(run.metadata["model_sha256"]) == {"vie", "eng"}


def test_real_blank_page_has_no_fabricated_text(tessdata_dir):
    page = PreparedPage(Image.new("L", (400, 400), "white"), {
        "to_original": [1., 0., 0., 0., 1., 0., 0., 0., 1.],
    })
    run = recognize(page, tessdata_dir)
    assert run.result.page.tokens == []
    assert run.metadata["warnings"] == ["no_text_detected"]


def test_real_run_is_reproducible_with_same_engine_models_and_config(tessdata_dir):
    page = prepare_document((SAMPLES / "synthetic-001.png").read_bytes())
    first, second = recognize(page, tessdata_dir), recognize(page, tessdata_dir)
    assert first.result == second.result
    assert first.metadata == second.metadata
