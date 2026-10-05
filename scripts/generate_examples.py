import json

from docintel.config import ROOT
from docintel.domain.models import ExportArtifact
from docintel.services.fixtures import FixtureService


def write(name: str, value):
    path = ROOT / "contracts/examples" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


fixture = FixtureService(ROOT, enabled=True).view("fixture_001")
write("fixture-view.json", fixture.model_dump(mode="json"))
write("draft-invalid.json", {"student_id": "00123456", "date_of_birth": "2005-02-31"})
export = ExportArtifact(
    document_id=fixture.run.document_id,
    run_id=fixture.run.run_id,
    revision=1,
    data=fixture.draft.model_dump(),
    review_status="confirmed",
    provenance=fixture.run.provenance,
)
write("export-fixture.json", export.model_dump(mode="json"))
write(
    "error-unavailable.json",
    {
        "error": {
            "code": "PROVIDER_UNAVAILABLE",
            "message": "Chế độ mẫu giả lập chưa được bật.",
            "request_id": "fixture-request-id",
        }
    },
)
print("Generated contract examples; confirmed export is illustrative only.")
