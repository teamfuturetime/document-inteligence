from document_pipeline.models import InferenceResult

from docintel.domain.documents import ProductPrediction, ProductSpan
from docintel.domain.models import Confidence


def to_domain(result: InferenceResult) -> dict:
    """Translate AI implementation DTOs into canonical backend contracts."""
    fields = []
    for field in result.fields:
        confidence = Confidence(
            method="heuristic"
            if field.observation == "found" or field.ocr_score is not None
            else "unknown",
            policy_version=result.metadata["confidence_version"],
            score=field.ocr_score,
            ocr_score=field.ocr_score,
            mapping_signals={
                "candidate_count": field.candidate_count,
                "evidence_count": len(field.evidence_token_ids),
            },
            reason_codes=list(field.reason_codes),
        )
        fields.append(
            ProductPrediction(
                field_id=field.field_id,
                raw_value=field.raw_value,
                normalized_value=field.normalized_value,
                observation=field.observation,
                evidence_span_ids=list(field.evidence_token_ids),
                confidence=confidence,
            )
        )
    return {
        "fields": [field.model_dump(mode="json") for field in fields],
        "spans": [
            ProductSpan(
                span_id=token.token_id,
                text=token.text,
                box=token.box,
                ocr_score=token.confidence,
            ).model_dump(mode="json")
            for token in result.tokens
        ],
        "metadata": result.metadata,
        "warnings": list(result.warnings),
    }
