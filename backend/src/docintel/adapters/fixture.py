import json
from pathlib import Path

from docintel.domain.models import ExtractionRun, OCRResult


class FixtureOCRAdapter:
    """Chỉ nạp OCR giả lập; không nhận dạng ảnh, không đọc gold annotations."""

    def __init__(self, root: Path, *, enabled: bool):
        if not enabled:
            raise ValueError("Fixture adapter cần được bật rõ")
        self.root = root

    def recognize(self, image_path: Path) -> OCRResult:
        sample_id = image_path.stem
        record = json.loads((self.root / "data/fixtures/ocr.json").read_text(encoding="utf-8"))
        return OCRResult.model_validate(record[sample_id])


class FixtureExtractionAdapter:
    """Tra cứu prediction fixture theo ID, chỉ cho contract/UI check."""

    def __init__(self, root: Path, *, enabled: bool):
        if not enabled:
            raise ValueError("Fixture adapter cần được bật rõ")
        self.root = root

    def extract(self, document_id: str, ocr: OCRResult) -> ExtractionRun:
        runs = json.loads(
            (self.root / "data/fixtures/predictions.json").read_text(encoding="utf-8")
        )
        run = ExtractionRun.model_validate(runs[document_id])
        return ExtractionRun.model_validate(
            {**run.model_dump(), "spans": [span.model_dump() for span in ocr.spans]}
        )
