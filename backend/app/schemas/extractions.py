from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator
from ai_service.extraction.schemas import ExtractedField


class ExtractionRead(BaseModel):
    id: str
    document_id: str
    data: dict[str, Any]
    warnings: list[str]
    model_version: str
    confirmed: bool
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExtractionUpdate(BaseModel):
    data: dict[str, Any]
    warnings: list[str] = Field(default_factory=list)

    @field_validator("data")
    @classmethod
    def validate_fields(cls, data):
        fields = data.get("fields")
        if not isinstance(fields, dict) or len(fields) > 100:
            raise ValueError("fields phải là object, tối đa 100 trường")
        return {
            **data,
            "fields": {
                name: ExtractedField.model_validate(value).model_dump()
                for name, value in fields.items()
            },
        }
