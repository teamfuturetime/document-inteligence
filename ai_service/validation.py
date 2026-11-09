from pathlib import Path

from ai_service.config import ALLOWED_EXTENSIONS
from document_images import MIME_TYPES, detect_extension, matching_extensions


class DocumentValidationError(ValueError):
    pass


def validate_document(filename: str, header: bytes, content_type: str = "") -> str:
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise DocumentValidationError("Định dạng tài liệu không được hỗ trợ")
    detected = detect_extension(header)
    if detected is None or not matching_extensions(detected, extension.lstrip(".")):
        raise DocumentValidationError("Nội dung file không khớp định dạng khai báo")
    if content_type and content_type != "application/octet-stream" and content_type not in MIME_TYPES[extension.lstrip(".")]:
        raise DocumentValidationError("MIME type không hợp lệ")
    return extension
