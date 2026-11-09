"""Run inside the AI container to verify new codecs with real Tesseract OCR.

PowerShell:
Get-Content -Raw scripts/verify_image_formats.py | docker compose exec -T ai_service python -
Get-Content -Raw scripts/verify_image_formats.py | docker compose exec -T backend python - --api
"""

from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image, ImageDraw, ImageFont


def sample_pages():
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 36)
    except OSError:
        font = ImageFont.load_default(size=36)
    pages = []
    for name, number in [("ONE", "0101234567"), ("TWO", "0207654321")]:
        image = Image.new("RGB", (1200, 400), "white")
        draw = ImageDraw.Draw(image)
        draw.multiline_text(
            (50, 50),
            f"HO VA TEN: NGUYEN VAN A\nMST: {number}\nPAGE {name}",
            font=font,
            fill="black",
            spacing=20,
        )
        pages.append(image)
    return pages


def main():
    import fitz
    from ai_service.pipeline import DocumentPipeline

    pages = sample_pages()

    with TemporaryDirectory() as directory:
        pipeline = DocumentPipeline()
        for extension, codec, count in [
            ("webp", "WEBP", 1),
            ("bmp", "BMP", 1),
            ("tif", "TIFF", 1),
            ("tiff", "TIFF", 2),
            ("png", "PNG", 1),
            ("jpg", "JPEG", 1),
            ("jpeg", "JPEG", 1),
            ("pdf", "PDF", 2),
        ]:
            path = Path(directory) / ("scan." + extension)
            if codec == "PDF":
                with fitz.open() as pdf:
                    for image in pages:
                        page = pdf.new_page(width=1200, height=400)
                        page.insert_image(page.rect, stream=image_to_png(image))
                    pdf.save(path)
            else:
                options = (
                    {"save_all": True, "append_images": pages[1:]} if count == 2 else {}
                )
                pages[0].save(path, format=codec, **options)
            result = pipeline.process(path)
            ocr = result["ocr"]
            assert len(ocr["pages"]) == count, (extension, ocr["pages"])
            assert "0101234567" in ocr["text"], (extension, ocr["text"])
            assert ocr["engine"] == "tesseract", ocr["engine"]
            if count == 2:
                assert "0207654321" in ocr["text"], ocr["text"]
                assert ocr["text"].index("0101234567") < ocr["text"].index("0207654321")
            assert set(result) == {"ocr", "classification", "extraction"}
            print(
                f"PASS {extension}: {count} page(s), real Tesseract, ordered text and OCR contract",
                flush=True,
            )


def image_to_png(image):
    from io import BytesIO

    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def verify_api():
    """Real backend -> real AI HTTP, isolated SQLite and temporary uploads."""
    import os
    from io import BytesIO

    with TemporaryDirectory() as directory:
        os.environ["DATABASE_URL"] = "sqlite://"
        os.environ["STORAGE_PATH"] = directory
        os.environ["LOG_LEVEL"] = "ERROR"
        from fastapi.testclient import TestClient
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool
        from app.core.database import Base, get_db
        from app.main import app

        engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        factory = sessionmaker(bind=engine)
        Base.metadata.create_all(engine)

        def database():
            with factory() as session:
                yield session

        app.dependency_overrides[get_db] = database
        try:
            with TestClient(app) as client:
                auth = client.post(
                    "/api/v1/auth/register",
                    json={
                        "email": "formats@example.test",
                        "username": "formats",
                        "password": "Formats-test-password-123",
                    },
                )
                assert auth.status_code == 201, auth.text
                client.headers["X-CSRF-Token"] = auth.json()["csrf_token"]
                pages = sample_pages()
                for extension, codec, mime, count in [
                    ("webp", "WEBP", "image/webp", 1),
                    ("bmp", "BMP", "image/bmp", 1),
                    ("tif", "TIFF", "image/tiff", 1),
                    ("tiff", "TIFF", "image/tiff", 2),
                    ("png", "PNG", "image/png", 1),
                    ("jpg", "JPEG", "image/jpeg", 1),
                    ("jpeg", "JPEG", "image/jpeg", 1),
                    ("pdf", "PDF", "application/pdf", 2),
                ]:
                    output = BytesIO()
                    options = (
                        {"save_all": True, "append_images": pages[1:]}
                        if count == 2
                        else {}
                    )
                    pages[0].save(output, format=codec, **options)
                    upload = client.post(
                        "/api/v1/documents",
                        files={
                            "file": ("original." + extension, output.getvalue(), mime)
                        },
                    )
                    assert upload.status_code == 201, upload.text
                    base = "/api/v1/documents/" + upload.json()["id"]
                    processed = client.post(base + "/process")
                    assert processed.status_code == 200, processed.text
                    doc = client.get(base).json()
                    assert len(doc["ocr_pages"]) == count, doc
                    raw = doc["ocr_text_raw"]
                    assert "0101234567" in raw, raw
                    if count == 2:
                        assert raw.index("0101234567") < raw.index("0207654321"), raw
                    preview = client.get(base + "/preview")
                    assert preview.status_code == 200, preview.text
                    if extension in {"bmp", "tif", "tiff"}:
                        assert preview.headers["content-type"] == "image/png"
                        assert int(preview.headers["X-Page-Count"]) == count
                        if count == 2:
                            assert (
                                client.get(base + "/preview?page=2").status_code == 200
                            )
                    assert (
                        client.patch(
                            base + "/ocr-correction",
                            json={"text": "Reviewed OCR", "expected_revision": 0},
                        ).status_code
                        == 200
                    )
                    assert (
                        client.patch(
                            base + "/extraction",
                            json={"document_type": "other", "data": {"checked": "yes"}},
                        ).status_code
                        == 200
                    )
                    assert client.post(base + "/confirm").status_code == 200
                    exported = client.get(base + "/export").json()
                    assert (
                        exported["ocr_text_raw"] == raw
                        and exported["ocr_text"] == "Reviewed OCR"
                    )
                    assert exported["fields"] == {"checked": "yes"}
                    assert client.post(base + "/reopen").status_code == 200
                    assert client.delete(base).status_code == 200
                    print(
                        f"PASS API {extension}: upload -> real OCR -> preview -> review -> confirm -> export -> reopen -> delete",
                        flush=True,
                    )
        finally:
            app.dependency_overrides.clear()
            engine.dispose()


if __name__ == "__main__":
    import sys

    verify_api() if "--api" in sys.argv else main()
