import warnings
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import pymupdf
from PIL import Image, UnidentifiedImageError


class InvalidDocument(ValueError):
    pass


@dataclass(frozen=True)
class ValidatedDocument:
    mime_type: str
    extension: str
    size_bytes: int


SIGNATURES = {
    b"%PDF-": ("application/pdf", ".pdf"),
    b"\x89PNG\r\n\x1a\n": ("image/png", ".png"),
    b"\xff\xd8\xff": ("image/jpeg", ".jpg"),
}


def _validate_filename(filename: str) -> str:
    if any(ord(character) < 32 or ord(character) == 127 for character in filename):
        raise InvalidDocument("Tên tệp chứa ký tự điều khiển")
    basename = filename.replace("\\", "/").rsplit("/", 1)[-1].strip()
    if not basename or len(basename) > 255:
        raise InvalidDocument("Tên tệp phải có từ 1 đến 255 ký tự")
    return basename


def _validate_pdf(content: bytes) -> None:
    if not content.rstrip().endswith(b"%%EOF"):
        raise InvalidDocument("PDF bị hỏng hoặc chưa tải lên đầy đủ")
    try:
        with pymupdf.open(stream=content, filetype="pdf") as document:
            if document.needs_pass:
                raise InvalidDocument("Không hỗ trợ PDF được bảo vệ bằng mật khẩu")
            if not document.is_pdf or document.is_repaired or document.page_count < 1:
                raise InvalidDocument("PDF bị hỏng hoặc không có trang")
            for index in range(document.page_count):
                document.load_page(index)
    except (RuntimeError, ValueError, OSError) as error:
        if isinstance(error, InvalidDocument):
            raise
        raise InvalidDocument("Nội dung PDF không hợp lệ") from error


def _validate_image(content: bytes, mime_type: str) -> None:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(content)) as image:
                expected_format = "PNG" if mime_type == "image/png" else "JPEG"
                if image.format != expected_format:
                    raise InvalidDocument("Định dạng ảnh không khớp nội dung tệp")
                if image.width * image.height > 40_000_000:
                    raise InvalidDocument("Ảnh vượt giới hạn 40 triệu pixel")
                image.verify()
            # verify() checks the container; load() also catches truncated pixel
            # data such as a JPEG with a valid header but an incomplete scan.
            with Image.open(BytesIO(content)) as image:
                image.load()
    except (
        OSError,
        ValueError,
        SyntaxError,
        UnidentifiedImageError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as error:
        if isinstance(error, InvalidDocument):
            raise
        raise InvalidDocument("Nội dung ảnh bị hỏng hoặc không hợp lệ") from error


def validate_document(
    filename: str, content: bytes, max_bytes: int, content_type: str | None = None
) -> ValidatedDocument:
    filename = _validate_filename(filename)
    if not content:
        raise InvalidDocument("Tệp rỗng")
    if len(content) > max_bytes:
        raise InvalidDocument(f"Tệp vượt giới hạn {max_bytes} byte")

    detected = next((value for signature, value in SIGNATURES.items() if content.startswith(signature)), None)
    if not detected:
        raise InvalidDocument("Chỉ hỗ trợ PDF, PNG và JPEG hợp lệ")

    mime_type, canonical_extension = detected
    supplied_extension = Path(filename).suffix.lower()
    accepted_extensions = {canonical_extension}
    if canonical_extension == ".jpg":
        accepted_extensions.add(".jpeg")
    if supplied_extension not in accepted_extensions:
        raise InvalidDocument("Phần mở rộng không khớp nội dung tệp")
    if content_type:
        declared_mime = content_type.split(";", 1)[0].strip().lower()
        if declared_mime not in (mime_type, "application/octet-stream"):
            raise InvalidDocument("MIME type không khớp nội dung tệp")
    if mime_type == "application/pdf":
        _validate_pdf(content)
    else:
        _validate_image(content, mime_type)
    return ValidatedDocument(mime_type, supplied_extension, len(content))
