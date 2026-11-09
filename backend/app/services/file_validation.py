"""Kiểm tra tính hợp lệ của file upload."""
from pathlib import Path
from io import BytesIO

from document_images import MIME_TYPES, detect_extension, matching_extensions, validate_image

from app.core.config import get_settings

settings = get_settings()

ALLOWED_MIME = set().union(*MIME_TYPES.values())


class FileValidationError(Exception):
    """Lỗi khi file không hợp lệ."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _detect_extension(content: bytes) -> str | None:
    """Phát hiện loại file dựa trên magic bytes."""
    return detect_extension(content)


def validate_upload(
    filename: str, content: bytes, content_type: str = ""
) -> None:
    """Kiểm tra tên file, kích thước, magic bytes và MIME type."""
    # 1. Kiểm tra tên file có đuôi hợp lệ
    validate_upload_metadata(filename, content_type)

    # 2. Kiểm tra kích thước
    if len(content) > settings.max_upload_size_bytes:
        raise FileValidationError(
            f"File quá lớn: {len(content)} bytes. "
            f"Giới hạn tối đa {settings.MAX_UPLOAD_SIZE_MB}MB"
        )
    if len(content) == 0:
        raise FileValidationError("File rỗng, không thể xử lý")

    # 3. Kiểm tra magic bytes (loại file thực tế)
    validate_upload_signature(filename, content[:16])
    validate_upload_image(filename, BytesIO(content))


def validate_upload_metadata(filename: str, content_type: str = "") -> str:
    """Từ chối metadata sai trước khi bắt đầu ghi stream."""
    ext = Path(filename).suffix.lower().lstrip(".")
    if ext not in settings.ALLOWED_EXTENSIONS or ext not in MIME_TYPES:
        raise FileValidationError(
            f"Loại file không được hỗ trợ: .{ext}. "
            f"Chỉ chấp nhận: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )
    # Browsers may omit MIME for TIFF/BMP; octet-stream is generic, so the
    # signature and full decoder below remain authoritative for those uploads.
    if content_type and content_type != "application/octet-stream" and content_type not in MIME_TYPES[ext]:
        raise FileValidationError(f"MIME type không hợp lệ: {content_type}")
    return ext


def validate_upload_signature(filename: str, header: bytes) -> None:
    """Kiểm tra magic bytes từ phần đầu stream."""
    ext = Path(filename).suffix.lower().lstrip(".")
    detected = _detect_extension(header)
    if detected is None:
        raise FileValidationError("Không thể nhận diện loại file hoặc file bị hỏng")
    if not matching_extensions(detected, ext):
        raise FileValidationError(
            f"Đuôi file (.{ext}) không khớp với nội dung thực tế ({detected})"
        )


def image_limits() -> dict[str, int]:
    return {"max_pixels": settings.MAX_IMAGE_PIXELS, "max_pages": settings.MAX_IMAGE_PAGES,
            "max_total_pixels": settings.MAX_TOTAL_IMAGE_PIXELS}


def validate_upload_image(filename: str, source) -> None:
    extension = Path(filename).suffix.lower().lstrip(".")
    if extension == "pdf":
        return
    try:
        validate_image(source, extension, **image_limits())
    except (ValueError, KeyError) as exc:
        raise FileValidationError(str(exc)) from exc
