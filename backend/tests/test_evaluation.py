import pytest

from docintel.config import ROOT
from docintel.domain.models import (
    ExtractionRun,
    FieldPrediction,
    FixtureManifest,
    GoldAnnotation,
    GoldField,
    Provenance,
)
from docintel.evaluation.manifest import validate_manifest
from docintel.evaluation.metrics import evaluate
from docintel.services.fixtures import FixtureService


def gold(sample_id, status, value):
    return GoldAnnotation(
        sample_id=sample_id, fields={"full_name": GoldField(status=status, value=value)}
    )


def prediction(sample_id, value):
    return ExtractionRun(
        run_id="run_" + sample_id,
        document_id=sample_id,
        schema_version="1.0.0",
        provenance=Provenance(data_origin="synthetic", prediction_source="fixture"),
        fields=[
            FieldPrediction(
                field_id="full_name",
                raw_value=value,
                normalized_value=value,
                observation="found" if value is not None else "unknown",
                evidence_status="unavailable",
            )
        ],
        spans=[],
        status="succeeded",
    )


def test_reference_formula_50_present_48_predictions_45_correct():
    annotations = [gold(str(i), "present", "Nguyễn An") for i in range(50)]
    runs = [prediction(str(i), "Nguyễn An" if i < 45 else "Sai") for i in range(48)]
    report = evaluate(annotations, runs, source="fixture")
    counts = report["micro"]
    assert (counts["tp"], counts["fp"], counts["fn"]) == (45, 3, 5)
    assert counts["precision"] == pytest.approx(45 / 48)
    assert counts["recall"] == pytest.approx(45 / 50)
    assert counts["f1"] == pytest.approx(90 / 98)
    assert counts["support"] == 50 and counts["predicted_non_null"] == 48
    assert report["report_type"] == "evaluator_contract_check"


@pytest.mark.parametrize(
    ("status", "expected", "predicted", "counts"),
    [
        ("present", "An", "An", (1, 0, 0)),
        ("present", "An", "Bảo", (0, 1, 1)),
        ("present", "An", None, (0, 0, 1)),
        ("absent", None, "Bảo", (0, 1, 0)),
        ("absent", None, None, (0, 0, 0)),
        ("unreadable", None, None, (0, 0, 0)),
        ("unreadable", None, "Bảo", (0, 0, 0)),
    ],
)
def test_correct_wrong_missing_extra_absent_unreadable(status, expected, predicted, counts):
    report = evaluate([gold("d", status, expected)], [prediction("d", predicted)], source="fixture")
    actual = report["micro"]
    assert (actual["tp"], actual["fp"], actual["fn"]) == counts
    if status == "absent":
        assert actual["extra_fill_rate"] == (0 if predicted is None else 1)
        assert actual["correct_abstention"] == int(predicted is None)
    if status == "unreadable":
        assert actual["unreadable_support"] == 1
        assert actual["support"] == 0
        assert actual["unreadable_abstention_rate"] == int(predicted is None)


def test_zero_denominator_and_provenance():
    report = evaluate([], [], source="fixture")
    assert report["micro"]["f1"] is None
    assert report["micro"]["undefined_reasons"]["f1"] == "ZERO_DENOMINATOR"
    assert report["macro"]["f1"] is None
    assert report["confidence_buckets"] == {}
    assert report["latency"] is None
    with pytest.raises(ValueError, match="khớp"):
        evaluate([gold("d", "present", "An")], [prediction("d", "An")], source="model")


def test_duplicate_and_unknown_document_fail():
    with pytest.raises(ValueError, match="trùng"):
        evaluate([gold("d", "present", "An")] * 2, [], source="fixture")
    with pytest.raises(ValueError, match="ngoài"):
        evaluate([], [prediction("d", "An")], source="fixture")


def test_primary_metric_retains_diacritics_and_zero():
    report = evaluate(
        [gold("d", "present", "Nguyễn An")], [prediction("d", "Nguyen An")], source="fixture"
    )
    assert report["micro"]["tp"] == 0


def test_document_metric_excludes_absent_and_unreadable():
    manifest = FixtureManifest.model_validate_json(
        (ROOT / "data/manifests/fixtures.json").read_text(encoding="utf-8")
    )
    gold = validate_manifest(ROOT, manifest)
    service = FixtureService(ROOT, enabled=True)
    report = evaluate(
        gold, [service.view(sample.sample_id).run for sample in manifest.samples], source="fixture"
    )
    counts = report["micro"]
    assert (counts["support"], counts["tp"], counts["fp"], counts["fn"]) == (40, 38, 2, 2)
    assert (counts["wrong"], counts["missing"], counts["extra"], counts["unreadable_support"]) == (
        1,
        1,
        1,
        1,
    )
    assert report["document_exact_match"]["support"] == 4
    assert report["document_exact_match"]["correct"] == 2
    assert report["document_exact_match"]["excluded"] == 2
