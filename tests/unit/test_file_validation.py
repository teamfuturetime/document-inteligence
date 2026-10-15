"""Unit tests cho file validation."""
import pytest

from app.services.file_validation import (
    ALLOWED_MIME,
    FileValidationError,
    _detect_extension,
    validate_upload,
)

# Mẫu nội dung file hợp lệ (magic bytes)
PDF_CONTENT = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n%%EOF"
JPG_CONTENT = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01"
PNG_CONTENT = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"


def test_detect_extension():
    assert _detect_extension(PDF_CONTENT) == "pdf"
    assert _detect_extension(JPG_CONTENT) == "jpg"
    assert _detect_extension(PNG_CONTENT) == "png"
    assert _detect_extension(b"not a real file") is None


def test_validate_valid_pdf():
    validate_upload("hoa-don.pdf", PDF_CONTENT, "application/pdf")


def test_validate_valid_png():
    validate_upload("anh.png", PNG_CONTENT, "image/png")


def test_validate_rejects_unsupported_extension():
    with pytest.raises(FileValidationError) as exc:
        validate_upload("file.exe", PDF_CONTENT, "application/pdf")
    assert "không được hỗ trợ" in str(exc.value)


def test_validate_rejects_empty_file():
    with pytest.raises(FileValidationError):
        validate_upload("empty.pdf", b"", "application/pdf")


def test_validate_rejects_oversized_file():
    big = PDF_CONTENT + b"0" * (11 * 1024 * 1024)  # > 10MB
    with pytest.raises(FileValidationError) as exc:
        validate_upload("big.pdf", big, "application/pdf")
    assert "quá lớn" in str(exc.value)


def test_validate_rejects_spoofed_extension():
    # Đuôi .pdf nhưng nội dung thực tế là PNG
    with pytest.raises(FileValidationError) as exc:
        validate_upload("fake.pdf", PNG_CONTENT, "image/png")
    assert "không khớp" in str(exc.value)


def test_validate_rejects_unknown_content():
    with pytest.raises(FileValidationError) as exc:
        validate_upload("file.pdf", b"\x00\x01\x02\x03random", "application/pdf")
    assert "không thể nhận diện" in str(exc.value).lower()


def test_validate_rejects_bad_mime():
    with pytest.raises(FileValidationError) as exc:
        validate_upload("file.pdf", PDF_CONTENT, "text/html")
    assert "MIME type" in str(exc.value)


def test_allowed_mime_set():
    assert ALLOWED_MIME == {"application/pdf", "image/jpeg", "image/png"}
