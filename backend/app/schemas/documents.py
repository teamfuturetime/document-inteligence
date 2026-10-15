from datetime import datetime

from pydantic import BaseModel, ConfigDict


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
