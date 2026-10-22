"""Pydantic schemas cho tài liệu và kết quả trích xuất."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class DocumentCreate(BaseModel):
    """Dữ liệu cần thiết để tạo bản ghi tài liệu."""

    filename: str = Field(..., max_length=255)
    content_type: str = Field(..., max_length=100)
    file_size: int = Field(..., ge=0)
    file_path: str = Field(..., max_length=500)
    owner_id: Optional[str] = None


class DocumentOut(BaseModel):
    """Thông tin tài liệu trả về cho client."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    content_type: str
    file_size: int
    status: str
    ocr_text: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None


class DocumentList(BaseModel):
    """Danh sách tài liệu kèm phân trang."""

    items: List[DocumentOut]
    total: int
    page: int
    page_size: int


class ExtractionOut(BaseModel):
    """Kết quả trích xuất trả về cho client."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    document_type: str
    data: Dict[str, Any]
    confidence: float
    classification_metadata: Optional[Dict[str, Any]] = None
    status: str
    created_at: datetime
    updated_at: datetime
    confirmed_at: Optional[datetime] = None


class ExtractionUpdate(BaseModel):
    """Dữ liệu chỉnh sửa kết quả trích xuất."""

    data: Dict[str, Any]
    document_type: Optional[str] = None


class MessageOut(BaseModel):
    message: str


class DashboardOut(BaseModel):
    total: int
    processed: int
    awaiting_review: int
    confirmed: int
    recent: List[DocumentOut]
