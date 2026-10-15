from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class ExtractedField(BaseModel):
    value: Any = None
    confidence: float = Field(ge=0, le=1)
    source_text: str | None = None

    @field_validator("source_text")
    @classmethod
    def limit_source_text(cls, value: str | None) -> str | None:
        return value[:500] if value else value


class ExtractionResult(BaseModel):
    document_type: Literal[
        "identity_card", "birth_certificate", "application_form", "unknown"
    ]
    fields: dict[str, ExtractedField]
    warnings: list[str] = Field(default_factory=list)
    model_version: str = "rules-v1"


DOCUMENT_FIELDS = {
    "identity_card": {"id_number", "full_name", "date_of_birth", "address"},
    "birth_certificate": {"full_name", "date_of_birth", "place_of_birth", "father_name", "mother_name"},
    "application_form": {"applicant_name", "recipient", "subject", "date"},
    "unknown": set(),
}
