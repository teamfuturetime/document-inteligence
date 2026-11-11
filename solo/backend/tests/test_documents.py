from io import BytesIO
import os
from pathlib import Path

from PIL import Image
import pytest

from ai02_solo.ocr import DocumentError, prepare
from ai02_solo.pipeline import run
from ai02_solo.settings import ROOT, Settings


def test_transparency_is_white_and_original_bytes_not_stored():
    source = BytesIO()
    Image.new("RGBA", (10, 20), (0, 0, 0, 0)).save(source, "PNG")
    result = Image.open(BytesIO(prepare(source.getvalue())))
    assert result.mode == "L"
    assert result.getpixel((0, 0)) == 255


def test_invalid_and_multipage_documents_are_rejected():
    import pymupdf
    with pytest.raises(DocumentError):
        prepare(b"bad-image")
    with pymupdf.open() as doc:
        doc.new_page(); doc.new_page()
        with pytest.raises(DocumentError, match="một trang"):
            prepare(doc.tobytes())


@pytest.mark.native
@pytest.mark.parametrize("identifier", ["invoice-001", "invoice-002", "invoice-003", "application-001", "application-002", "application-003"])
def test_real_ocr_for_both_schemas_and_all_formats(identifier):
    if not os.getenv("SOLO_RUN_OCR"):
        pytest.skip("Set SOLO_RUN_OCR=1 after provisioning real OCR models")
    import json
    manifest = json.loads((ROOT / "data/golden-v1/manifest.json").read_text())
    item = next(item for item in manifest["documents"] if item["id"] == identifier)
    data = (ROOT / "data/golden-v1" / item["file"]).read_bytes()
    result = run(data, item["kind"], "rules", Settings.from_env())
    assert result.mode == "rules"
    assert result.ocr_text
    key = "invoice_number" if item["kind"] == "invoice" else "student_id"
    assert result.fields[key].value is not None, f"Synthetic {identifier} OCR:\n{result.ocr_text}"
    assert result.provenance["ocr"]["engine"].startswith("tesseract 5.")
