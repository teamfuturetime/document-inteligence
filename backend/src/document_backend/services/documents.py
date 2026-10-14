"""Validate upload content, without running preprocessing or OCR."""

from io import BytesIO

from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader
from pypdf.errors import PyPdfError

from document_backend.errors import DocumentError

MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 25_000_000


def validate_document(data: bytes) -> None:
    if len(data) > MAX_FILE_BYTES:
        raise DocumentError(413, "file_too_large", "Tài liệu vượt giới hạn 10 MiB.")
    if not data:
        raise DocumentError(422, "invalid_document", "Tài liệu rỗng.")
    if data.startswith(b"%PDF-"):
        try:
            with BytesIO(data) as stream:
                doc = PdfReader(stream, strict=True)
                if doc.is_encrypted:
                    raise DocumentError(422, "invalid_document", "Không hỗ trợ PDF có mật khẩu.")
                if len(doc.pages) != 1:
                    raise DocumentError(422, "multiple_pages", "MVP chỉ hỗ trợ tài liệu một trang.")
        except DocumentError:
            raise
        except (PyPdfError, ValueError) as exc:
            raise DocumentError(422, "invalid_document", "Không đọc được PDF.") from exc
        return
    if not (data.startswith(b"\x89PNG\r\n\x1a\n") or data.startswith(b"\xff\xd8")):
        raise DocumentError(415, "unsupported_media_type", "Nội dung file phải là PNG, JPG hoặc PDF.")
    try:
        with Image.open(BytesIO(data), formats=["PNG", "JPEG"]) as image:
            if image.width * image.height > MAX_PIXELS:
                raise DocumentError(422, "image_too_large", "Ảnh vượt giới hạn 25 megapixel.")
            if getattr(image, "n_frames", 1) != 1:
                raise DocumentError(422, "multiple_pages", "Không hỗ trợ ảnh nhiều khung hình.")
            image.verify()
        with Image.open(BytesIO(data), formats=["PNG", "JPEG"]) as image:
            image.load()
    except Image.DecompressionBombError as exc:
        raise DocumentError(422, "image_too_large", "Ảnh vượt giới hạn decode.") from exc
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError) as exc:
        raise DocumentError(422, "invalid_document", "Không đọc được ảnh.") from exc
