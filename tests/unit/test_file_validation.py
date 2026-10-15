import pytest

from app.services.file_validation import InvalidDocument, validate_document


def test_detects_png_from_signature() -> None:
    result = validate_document("scan.png", b"\x89PNG\r\n\x1a\ncontent", 100)
    assert result.mime_type == "image/png"


@pytest.mark.parametrize(
    ("name", "content"),
    [("fake.pdf", b"not a pdf"), ("fake.png", b"%PDF-content")],
)
def test_rejects_invalid_or_mismatched_files(name: str, content: bytes) -> None:
    with pytest.raises(InvalidDocument):
        validate_document(name, content, 100)


def test_rejects_oversize_file() -> None:
    with pytest.raises(InvalidDocument, match="giới hạn"):
        validate_document("file.pdf", b"%PDF-" + b"x" * 50, 20)
