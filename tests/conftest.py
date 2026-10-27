from io import BytesIO

import fitz
import pytest
from PIL import Image


@pytest.fixture(scope="session")
def document_contents() -> dict[str, bytes]:
    """Real files shared by validation and API tests, without external fixtures."""
    contents = {}
    for extension, image_format in (("png", "PNG"), ("jpg", "JPEG")):
        output = BytesIO()
        Image.new("RGB", (16, 12), color="white").save(output, format=image_format)
        contents[extension] = output.getvalue()
    with fitz.open() as document:
        page = document.new_page(width=200, height=200)
        page.insert_text((20, 40), "Week 1 upload test")
        contents["pdf"] = document.tobytes()
        contents["encrypted_pdf"] = document.tobytes(
            encryption=fitz.PDF_ENCRYPT_AES_256,
            owner_pw="owner-secret",
            user_pw="reader-secret",
        )
    return contents
