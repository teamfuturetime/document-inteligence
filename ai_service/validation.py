from pathlib import Path

from ai_service.config import ALLOWED_EXTENSIONS

MAGIC = {
    ".pdf": b"%PDF",
    ".png": b"\x89PNG\r\n\x1a\n",
    ".jpg": b"\xff\xd8\xff",
    ".jpeg": b"\xff\xd8\xff",
}


class DocumentValidationError(ValueError):
    pass


def validate_document(filename: str, header: bytes) -> str:
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise DocumentValidationError("Định dạng tài liệu không được hỗ trợ")
    if not header.startswith(MAGIC[extension]):
        raise DocumentValidationError("Nội dung file không khớp định dạng khai báo")
    return extension
