from pathlib import Path

from docintel.adapters.fixture import FixtureExtractionAdapter, FixtureOCRAdapter
from docintel.domain.models import DraftApplicationData, FixtureManifest, FixtureView
from docintel.domain.validation import validate_draft


class FixtureService:
    def __init__(self, root: Path, *, enabled: bool):
        self.root = root
        self.ocr = FixtureOCRAdapter(root, enabled=enabled)
        self.extractor = FixtureExtractionAdapter(root, enabled=enabled)
        self.manifest = FixtureManifest.model_validate_json(
            (root / "data/manifests/fixtures.json").read_text(encoding="utf-8")
        )

    def catalog(self) -> list[str]:
        return [sample.sample_id for sample in self.manifest.samples]

    def image_path(self, sample_id: str) -> Path:
        sample = next((s for s in self.manifest.samples if s.sample_id == sample_id), None)
        if sample is None:
            raise KeyError(sample_id)
        path = (self.root / sample.input_path).resolve()
        if not path.is_relative_to(self.root / "data/fixtures"):
            raise ValueError("Fixture path ngoài thư mục cho phép")
        return path

    def view(self, sample_id: str) -> FixtureView:
        ocr = self.ocr.recognize(self.image_path(sample_id))
        run = self.extractor.extract(sample_id, ocr)
        draft = DraftApplicationData.model_validate(
            {field.field_id: field.normalized_value for field in run.fields}
        )
        return FixtureView(
            sample_id=sample_id,
            label="Mẫu giả lập — chưa chạy OCR",
            image_url=f"/api/v1/fixtures/{sample_id}/image",
            run=run,
            draft=draft,
            validation_issues=validate_draft(draft),
        )
