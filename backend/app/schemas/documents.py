"""Pydantic schemas cho tài liệu và kết quả trích xuất."""
from datetime import datetime
from typing import Any, Dict, List, Optional
import unicodedata

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from app.services.ocr_text import clean_ocr_text


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
    ocr_text_corrected: Optional[str] = Field(default=None, exclude=True)
    ocr_corrected_at: Optional[datetime] = None
    ocr_revision: int

    @computed_field(return_type=Optional[str])
    @property
    def ocr_text_raw(self) -> Optional[str]:
        """Raw OCR retained for debugging and backward compatibility."""

        return self.ocr_text

    @computed_field(return_type=Optional[str])
    @property
    def ocr_text_cleaned(self) -> Optional[str]:
        """Readability-enhanced OCR generated without changing stored data."""

        return self.ocr_text_corrected or clean_ocr_text(self.ocr_text)

    @computed_field(return_type=bool)
    @property
    def ocr_is_corrected(self) -> bool:
        return self.ocr_text_corrected is not None

    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None


class DocumentDetailOut(DocumentOut):
    """Document detail with optional layout metadata stored in the existing JSON column."""

    ocr_boxes: Optional[List[Dict[str, Any]]] = Field(default=None, exclude=True)

    @computed_field(return_type=List[Dict[str, Any]])
    @property
    def ocr_pages(self) -> List[Dict[str, Any]]:
        pages = self.ocr_boxes or []
        if pages and isinstance(pages[0], dict) and "blocks" in pages[0]:
            return pages
        return []


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
    ai_document_type: Optional[str] = None
    reviewed_document_type: Optional[str] = None
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
    document_type: Optional[str] = Field(default=None, max_length=50)

    @field_validator("data")
    @classmethod
    def validate_fields(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        if len(data) > 200:
            raise ValueError("Không được vượt quá 200 trường dữ liệu")
        normalized: set[str] = set()
        for key, value in data.items():
            clean_key = unicodedata.normalize("NFC", key).strip()
            if not clean_key:
                raise ValueError("Tên trường không được để trống")
            if len(clean_key) > 100:
                raise ValueError("Tên trường không được vượt quá 100 ký tự")
            identity = clean_key.casefold()
            if identity in normalized:
                raise ValueError("Tên trường không được trùng nhau")
            normalized.add(identity)
            if len(str(value)) > 10_000:
                raise ValueError(f"Giá trị của trường '{clean_key}' quá dài")
        return {unicodedata.normalize("NFC", key).strip(): value for key, value in data.items()}

    @field_validator("document_type")
    @classmethod
    def validate_document_type(cls, value: Optional[str]) -> Optional[str]:
        supported = {
            "unknown", "other", "cccd", "cmnd", "hop_dong_lao_dong",
            "don_xin_viec", "ho_khau", "hoa_don", "invoice", "application_form",
        }
        if value is not None and value not in supported:
            raise ValueError("Loại tài liệu không được hỗ trợ")
        return value


class OCRCorrectionUpdate(BaseModel):
    text: str = Field(..., min_length=1, max_length=1_000_000)
    # SQLAlchemy Integer is signed 32-bit on PostgreSQL. Reject oversized input
    # at the API boundary rather than leaking driver conversion/server errors.
    expected_revision: int = Field(..., ge=0, le=2_147_483_647, strict=True)

    @field_validator("text")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Văn bản OCR chỉnh sửa không được để trống")
        return value


class MessageOut(BaseModel):
    message: str


class DashboardOut(BaseModel):
    total: int
    processed: int
    awaiting_review: int
    confirmed: int
    recent: List[DocumentOut]
