from ai_service.classification import classify_document
from ai_service.evaluation import field_metrics
from ai_service.extraction import extract_fields


def test_classifies_and_extracts_identity_card() -> None:
    text = "CĂN CƯỚC CÔNG DÂN\nSố: 012345678901\nHọ và tên: NGUYỄN VĂN AN\nNgày sinh: 01/02/2000"
    classification = classify_document(text)
    result = extract_fields(text, classification.document_type)
    assert classification.document_type == "identity_card"
    assert result.fields["id_number"].value == "012345678901"
    assert result.fields["full_name"].value == "NGUYỄN VĂN AN"


def test_field_metrics_are_computed_from_labeled_values() -> None:
    metrics = field_metrics(
        {"name": "Nguyễn An", "id": "123"},
        {"name": "nguyễn an", "id": "999"},
    )
    assert metrics.precision == 0.5
    assert metrics.recall == 0.5
    assert metrics.f1 == 0.5
