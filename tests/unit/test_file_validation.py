import pytest
from PIL import Image

from app.services.file_validation import InvalidDocument, validate_document


@pytest.mark.parametrize(
    ("filename", "kind", "mime_type", "extension"),
    [
        ("Đơn đề nghị.pdf", "pdf", "application/pdf", ".pdf"),
        ("scan.PNG", "png", "image/png", ".png"),
        ("scan.jpg", "jpg", "image/jpeg", ".jpg"),
        ("scan.JPEG", "jpg", "image/jpeg", ".jpeg"),
    ],
)
def test_accepts_real_documents_at_size_limit(
    document_contents, filename, kind, mime_type, extension
) -> None:
    content = document_contents[kind]

    result = validate_document(filename, content, len(content), content_type=mime_type)

    assert result.mime_type == mime_type
    assert result.extension == extension
    assert result.size_bytes == len(content)


@pytest.mark.parametrize("content_type", [None, "application/octet-stream"])
def test_detects_type_when_client_has_no_specific_mime(document_contents, content_type) -> None:
    result = validate_document(
        "scan.png", document_contents["png"], 1024, content_type=content_type
    )

    assert result.mime_type == "image/png"


@pytest.mark.parametrize(
    ("filename", "content"),
    [
        ("empty.pdf", b""),
        ("fake.pdf", b"not a pdf"),
        ("broken.pdf", b"%PDF-1.7\ngarbage\n%%EOF"),
        ("broken.png", b"\x89PNG\r\n\x1a\ncontent"),
        ("broken.jpg", b"\xff\xd8\xffcontent"),
    ],
)
def test_rejects_empty_spoofed_and_truncated_documents(filename, content) -> None:
    with pytest.raises(InvalidDocument):
        validate_document(filename, content, 1024)


def test_rejects_image_with_valid_header_but_truncated_pixels(document_contents) -> None:
    with pytest.raises(InvalidDocument):
        validate_document("truncated.jpg", document_contents["jpg"][:-2], 1024)


def test_rejects_encrypted_pdf(document_contents) -> None:
    with pytest.raises(InvalidDocument):
        validate_document("encrypted.pdf", document_contents["encrypted_pdf"], 4096)


def test_rejects_truncated_real_pdf(document_contents) -> None:
    with pytest.raises(InvalidDocument):
        validate_document("truncated.pdf", document_contents["pdf"][:-40], 4096)


def test_rejects_image_exceeding_decoded_pixel_limit(document_contents, monkeypatch) -> None:
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 100)
    with pytest.raises(InvalidDocument):
        validate_document("large.png", document_contents["png"], 1024)


def test_rejects_extension_and_content_mismatch(document_contents) -> None:
    with pytest.raises(InvalidDocument):
        validate_document("fake.pdf", document_contents["png"], 1024)


def test_rejects_declared_mime_and_content_mismatch(document_contents) -> None:
    with pytest.raises(InvalidDocument):
        validate_document(
            "scan.png", document_contents["png"], 1024, content_type="application/pdf"
        )


@pytest.mark.parametrize("filename", ["", "   ", "bad\x00.png", "bad\n.png", "a" * 252 + ".png"])
def test_rejects_invalid_filename_metadata(document_contents, filename) -> None:
    with pytest.raises(InvalidDocument):
        validate_document(filename, document_contents["png"], 1024)


def test_rejects_oversize_file(document_contents) -> None:
    content = document_contents["pdf"]
    with pytest.raises(InvalidDocument, match="giới hạn"):
        validate_document("file.pdf", content, len(content) - 1)
