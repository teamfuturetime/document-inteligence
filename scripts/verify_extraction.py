"""Generate synthetic extraction documents, then verify real OCR/API in Docker.

Host: python scripts/verify_extraction.py --generate
Docker: pipe this script to backend python - --verify /tmp/extraction-fixtures
The verification uses its own temporary SQLite database and upload directory.
"""

from __future__ import annotations

import argparse
from io import BytesIO
import json
import os
from pathlib import Path
import re
from tempfile import TemporaryDirectory
import unicodedata


def normalize(value):
    text = unicodedata.normalize("NFKD", str(value)).replace("đ", "d").replace("Đ", "D")
    return (
        re.sub(r"\s+", " ", "".join(c for c in text if not unicodedata.combining(c)))
        .casefold()
        .strip()
    )


def generate():
    from PIL import Image, ImageDraw, ImageFont
    import shutil

    root = Path(__file__).resolve().parents[1]
    output = root / "storage/extraction-verification/fixtures"
    output.mkdir(parents=True, exist_ok=True)
    cases = json.loads(
        (root / "tests/fixtures/extraction/cases.json").read_text(encoding="utf-8")
    )
    font_path = next(
        (
            path
            for path in [
                Path("C:/Windows/Fonts/arial.ttf"),
                Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            ]
            if path.exists()
        ),
        None,
    )
    if font_path is None:
        raise RuntimeError("A Vietnamese Unicode font is required to generate fixtures")
    font = ImageFont.truetype(str(font_path), 32)
    heading = ImageFont.truetype(str(font_path), 36)

    def render(lines):
        image = Image.new("RGB", (1654, 1800), "white")
        draw = ImageDraw.Draw(image)
        draw.rectangle((55, 55, 1599, 1745), outline="#222222", width=2)
        y = 105
        for index, line in enumerate(lines):
            selected = heading if index == 0 else font
            if draw.textlength(line, font=selected) > 1450:
                selected = ImageFont.truetype(str(font_path), 27)
            if draw.textlength(line, font=selected) > 1450:
                raise ValueError("Fixture line needs explicit wrapping")
            draw.text((95, y), line, fill="black", font=selected)
            y += 78
        return image

    manifest = []
    for case in cases:
        filename = case["name"] + ".png"
        render(case["text"].splitlines()).save(output / filename, dpi=(200, 200))
        manifest.append(
            {
                "file": filename,
                "type": case["type"],
                "fields": case["fields"],
                "pages": 1,
            }
        )
    invoice = cases[0]
    lines = invoice["text"].splitlines()
    pages = [render(lines[:8]), render(lines[8:])]
    pages[0].save(
        output / "invoice-multipage.pdf",
        save_all=True,
        append_images=pages[1:],
        resolution=200,
    )
    pages[0].save(
        output / "invoice-multipage.tiff",
        save_all=True,
        append_images=pages[1:],
        compression="tiff_lzw",
    )
    for suffix in ["pdf", "tiff"]:
        manifest.append(
            {
                "file": "invoice-multipage." + suffix,
                "type": invoice["type"],
                "fields": invoice["fields"],
                "pages": 2,
            }
        )
    existing = json.loads(
        (root / "tests/fixtures/vietnamese/manifest.json").read_text(encoding="utf-8")
    )
    for case in existing:
        if (
            case["category"]
            in {"invoice_table", "administrative_form", "vietnamese_text"}
            and case["expected_document_type"] != "hop_dong_lao_dong"
        ):
            shutil.copy2(
                root / "tests/fixtures/vietnamese" / case["file"], output / case["file"]
            )
            fields = case.get("expected_fields", {})
            if case["expected_document_type"] == "don_xin_viec":
                fields = {"full_name": "NGUYỄN VĂN DEMO"}
            if case["category"] == "administrative_form":
                fields = {"form_name": "BIỂU MẪU HÀNH CHÍNH TỔNG HỢP"}
            manifest.append(
                {
                    "file": case["file"],
                    "type": case["expected_document_type"],
                    "fields": fields,
                    "pages": 1,
                }
            )
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Generated {len(manifest)} synthetic document cases in {output}")


def verify(directory: Path):
    cases = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    with TemporaryDirectory(prefix="extraction-verification-") as temporary:
        os.environ["DATABASE_URL"] = "sqlite://"
        os.environ["STORAGE_PATH"] = temporary
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
            with factory() as db:
                yield db

        app.dependency_overrides[get_db] = database
        report = []
        try:
            with TestClient(app) as client:
                auth = client.post(
                    "/api/v1/auth/register",
                    json={
                        "email": "extraction@example.test",
                        "username": "extraction",
                        "password": "Extraction-test-password-123",
                    },
                )
                assert auth.status_code == 201
                client.headers["X-CSRF-Token"] = auth.json()["csrf_token"]
                for case in cases:
                    source = directory / case["file"]
                    mime = (
                        "application/pdf"
                        if source.suffix == ".pdf"
                        else "image/tiff"
                        if source.suffix == ".tiff"
                        else "image/png"
                    )
                    data = source.read_bytes()
                    uploaded = client.post(
                        "/api/v1/documents",
                        files={"file": (source.name, BytesIO(data), mime)},
                    )
                    assert uploaded.status_code == 201, f"{source.name}: upload failed"
                    base = "/api/v1/documents/" + uploaded.json()["id"]
                    processed = client.post(base + "/process")
                    assert (
                        processed.status_code == 200
                    ), f"{source.name}: real OCR processing failed"
                    ext = processed.json()
                    assert (
                        ext["document_type"] == case["type"]
                    ), f"{source.name}: incorrect document classification"
                    assert (
                        ext["ai_document_type"] == case["type"]
                        and ext["reviewed_document_type"] is None
                    )
                    assert ext["status"] == "pending_review"
                    for key, value in case["fields"].items():
                        assert key in ext["data"], f"{source.name}: missing field {key}"
                        assert normalize(ext["data"][key]) == normalize(
                            value
                        ), f"{source.name}: incorrect field {key}"
                    detail = client.get(base).json()
                    assert len(detail["ocr_pages"]) == case["pages"]
                    raw = detail["ocr_text_raw"]
                    assert client.get(base + "/preview").status_code == 200
                    human = dict(ext["data"])
                    if human:
                        human.pop(next(iter(human)))
                    human["Manual review note"] = "Checked against original"
                    review = client.patch(
                        base + "/extraction",
                        json={"document_type": "other", "data": human},
                    )
                    assert review.status_code == 200
                    assert review.json()["ai_document_type"] == case["type"]
                    assert (
                        client.patch(
                            base + "/ocr-correction",
                            json={"text": "Manually saved OCR", "expected_revision": 0},
                        ).status_code
                        == 200
                    )
                    assert client.get(base + "/extraction").json()["data"] == human
                    assert client.post(base + "/process").status_code == 409
                    assert client.post(base + "/confirm").status_code == 200
                    exported = client.get(base + "/export").json()
                    assert exported["fields"] == human
                    assert exported["ocr_text_raw"] == raw
                    assert exported["ocr_text"] == "Manually saved OCR"
                    assert exported["ai_document_type"] == case["type"]
                    assert exported["reviewed_document_type"] == "other"
                    assert client.post(base + "/reopen").status_code == 200
                    assert client.post(base + "/process").status_code == 409
                    assert client.get(base + "/extraction").json()["data"] == human
                    assert source.read_bytes() == data
                    assert client.delete(base).status_code == 200
                    report.append(
                        {
                            "file": source.name,
                            "type": case["type"],
                            "pages": case["pages"],
                            "field_names": list(ext["data"]),
                            "result": "PASS",
                        }
                    )
                    print(
                        f"PASS {source.name}: real OCR, classification, {len(ext['data'])} fields, manual review/OCR, protected reprocessing, confirm/export/reopen",
                        flush=True,
                    )
            return report
        finally:
            app.dependency_overrides.clear()
            engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate", action="store_true")
    parser.add_argument("--verify", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if args.generate:
        generate()
    elif args.verify:
        result = verify(args.verify)
        if args.report:
            args.report.write_text(json.dumps({"ocr": "real Tesseract", "database": "temporary SQLite", "cases": result}, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        parser.error("Choose --generate or --verify DIRECTORY")
