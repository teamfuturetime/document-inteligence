from ai_service.classification.engine import DocumentClass, DocumentClassifier, build_vietnamese_classifier


def test_empty_and_noise_are_unknown():
    classifier = build_vietnamese_classifier()
    assert classifier.classify("").document_type == "unknown"
    assert classifier.classify("### 123 xyz").document_type == "unknown"


def test_missing_vietnamese_diacritics():
    result = build_vietnamese_classifier().classify("CAN CUOC CONG DAN So: 079201012345")
    assert result.document_type == "cccd"
    assert result.confidence_type == "heuristic"
    assert result.matched_rules


def test_tie_becomes_unknown_and_requires_review():
    classifier = DocumentClassifier([
        DocumentClass("a", ["mau chung"]),
        DocumentClass("b", ["mau chung"]),
    ])
    result = classifier.classify("mau chung")
    assert result.document_type == "unknown"
    assert result.needs_review


def test_clear_result_never_claims_probability_or_100_percent():
    result = build_vietnamese_classifier().classify(
        "Căn cước công dân CCCD Số: 079201012345 Ngày cấp Nơi cấp"
    )
    assert result.document_type == "cccd"
    assert 0 < result.confidence < 100
    assert result.raw_score > 0


def test_close_scores_require_review():
    classifier = DocumentClassifier([
        DocumentClass("a", ["alpha", "shared"]),
        DocumentClass("b", ["beta", "shared"]),
    ])
    result = classifier.classify("alpha beta shared")
    assert result.document_type == "unknown"
    assert result.needs_review


def test_very_weak_evidence_falls_back_to_unknown():
    classifier = DocumentClassifier([
        DocumentClass("form", [f"signal {index}" for index in range(10)])
    ])
    result = classifier.classify("signal 1")
    assert result.document_type == "unknown"
    assert result.confidence < 50
