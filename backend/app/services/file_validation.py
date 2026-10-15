"""Kiểm tra tính hợp lệ của file upload."""
from pathlib import Path

from app.core.config import get_settings

settings = get_settings()

# Magic bytes để kiểm tra loại file thực tế
MAGIC_BYTES = {
    "pdf": (b"%PDF", "application/pdf"),
    "jpg": (b"\xff\xd8\xff", "image/jpeg"),
    "jpeg": (b"\xff\xd8\xff", "image/jpeg"),
    "png": (b"\x89PNG\r\n\x1a\n", "image/png"),
}

ALLOWED_MIME = {"application/pdf", "image/jpeg", "image/png"}


class FileValidationError(Exception):
    """Lỗi khi file không hợp lệ."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _detect_extension(content: bytes) -> str | None:
    """Phát hiện loại file dựa trên magic bytes."""
    for ext, (magic, _) in MAGIC_BYTES.items():
        if content.startswith(magic):
            return ext
    return None


def validate_upload(
    filename: str, content: bytes, content_type: str = ""
) -> None:
    """Kiểm tra tên file, kích thước, magic bytes và MIME type."""
    # 1. Kiểm tra tên file có đuôi hợp lệ
    ext = Path(filename).suffix.lower().lstrip(".")
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise FileValidationError(
            f"Loại file không được hỗ trợ: .{ext}. "
            f"Chỉ chấp nhận: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )

    # 2. Kiểm tra kích thước
    if len(content) > settings.max_upload_size_bytes:
        raise FileValidationError(
            f"File quá lớn: {len(content)} bytes. "
            f"Giới hạn tối đa {settings.MAX_UPLOAD_SIZE_MB}MB"
        )
    if len(content) == 0:
        raise FileValidationError("File rỗng, không thể xử lý")

    # 3. Kiểm tra magic bytes (loại file thực tế)
    detected = _detect_extension(content)
    if detected is None:
        raise FileValidationError(
            "Không thể nhận diện loại file. File có thể bị hỏng hoặc không phải PDF/ảnh"
        )
    if detected != ext:
        raise FileValidationError(
            f"Đuôi file (.{ext}) không khớp với nội dung thực tế ({detected})"
        )

    # 4. Kiểm tra MIME type nếu có
    if content_type and content_type not in ALLOWED_MIME:
        raise FileValidationError(f"MIME type không hợp lệ: {content_type}")
