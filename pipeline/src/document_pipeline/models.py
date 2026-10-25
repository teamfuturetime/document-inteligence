from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

DocumentType = Literal["hoa_don", "don_de_nghi"]
Value = str | int | None
Score = Annotated[float, Field(ge=0, le=1)]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class Token(Model):
    token_id: str
    line_id: str
    text: str
    box: tuple[float, float, float, float]
    confidence: Score | None


class Prediction(Model):
    field_id: str
    raw_value: str | None
    normalized_value: Value
    observation: Literal["found", "not_found", "unknown"]
    evidence_token_ids: tuple[str, ...] = ()
    ocr_score: Score | None = None
    reason_codes: tuple[str, ...] = ()
    candidate_count: int = 0


class InferenceResult(Model):
    pipeline_version: str
    document_type: DocumentType
    image_width: int
    image_height: int
    tokens: tuple[Token, ...]
    fields: tuple[Prediction, ...]
    warnings: tuple[str, ...]
    metadata: dict
