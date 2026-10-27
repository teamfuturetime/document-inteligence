from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DocumentCreate(BaseModel):
    """Validated metadata derived from a stored upload, never a client storage path."""

    original_name: str = Field(min_length=1, max_length=255)
    stored_name: str = Field(min_length=1, max_length=255)
    mime_type: Literal["application/pdf", "image/png", "image/jpeg"]
    size_bytes: int = Field(gt=0)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class DocumentRead(BaseModel):
    id: str
    original_name: str
    mime_type: str
    size_bytes: int
    status: str
    document_type: str | None
    created_at: datetime
    expires_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentList(BaseModel):
    items: list[DocumentRead]
    total: int
