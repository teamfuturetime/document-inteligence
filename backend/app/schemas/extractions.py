from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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
