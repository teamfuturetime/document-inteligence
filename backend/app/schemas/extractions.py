from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ExtractionRead(BaseModel):
    id: str
    document_id: str
    data: dict[str, Any]
    warnings: list[str]
    model_version: str
    confirmed: bool
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
