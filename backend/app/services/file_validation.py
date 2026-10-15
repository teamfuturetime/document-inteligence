from dataclasses import dataclass
from pathlib import Path


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


def validate_document(filename: str, content: bytes, max_bytes: int) -> ValidatedDocument:
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
    return ValidatedDocument(mime_type, supplied_extension, len(content))
