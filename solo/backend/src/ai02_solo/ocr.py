"""Single-page bounded preprocessing and Tesseract. Called only inside worker."""

import csv
import hashlib
from io import BytesIO, StringIO
import json
from pathlib import Path
import subprocess
import warnings

from PIL import Image, ImageOps

from .contracts import Token

MAX_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 25_000_000
MODEL_SHA = {
    "vie": "79df64caf7bcfb2a27df5042ecb6121e196eada34da774956995747636d5bfa1",
    "eng": "7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2",
}
MODEL_COMMIT = "87416418657359cb625c412a48b6e1d6d41c29bd"


class DocumentError(Exception):
    def __init__(self, code, message, status=422):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def prepare(data: bytes) -> bytes:
    if not data or len(data) > MAX_BYTES:
        raise DocumentError("file_size", "Tài liệu trống hoặc lớn hơn 10 MiB.", 413)
    try:
        if data.startswith(b"%PDF-"):
            import pymupdf
            with pymupdf.open(stream=data, filetype="pdf") as doc:
                if doc.needs_pass or doc.is_repaired or len(doc) != 1:
                    raise DocumentError("pdf_pages", "PDF phải đúng một trang, không khóa hoặc hỏng.")
                page = doc[0]
                scale = 150 / 72
                if page.rect.width * page.rect.height * scale ** 2 > MAX_PIXELS:
                    raise DocumentError("pixels", "Ảnh render vượt 25 triệu pixel.", 413)
                pix = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False, colorspace=pymupdf.csRGB)
                image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        else:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(BytesIO(data)) as source:
                    if source.format not in {"PNG", "JPEG"}:
                        raise DocumentError("media_type", "Chỉ hỗ trợ PNG, JPEG hoặc PDF.", 415)
                    if getattr(source, "n_frames", 1) != 1:
                        raise DocumentError("pages", "Chỉ hỗ trợ ảnh đúng một frame.")
                    if source.width * source.height > MAX_PIXELS:
                        raise DocumentError("pixels", "Ảnh vượt 25 triệu pixel.", 413)
                    oriented = ImageOps.exif_transpose(source)
                    rgba = oriented.convert("RGBA")
                    background = Image.new("RGBA", rgba.size, "white")
                    background.alpha_composite(rgba)
                    image = background.convert("RGB")
        if image.width * image.height > MAX_PIXELS:
            raise DocumentError("pixels", "Ảnh vượt 25 triệu pixel.", 413)
        output = BytesIO()
        ImageOps.grayscale(image).save(output, format="PNG")
        return output.getvalue()
    except DocumentError:
        raise
    except Exception as exc:
        raise DocumentError("invalid_document", "Không đọc được nội dung tài liệu.") from exc


def readiness(directory: str) -> dict:
    try:
        hashes = {}
        for language, expected in MODEL_SHA.items():
            path = Path(directory) / f"{language}.traineddata"
            if path.stat().st_size > 8 * 1024 * 1024:
                raise ValueError("unexpected model size")
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual != expected:
                raise ValueError("model hash differs")
            hashes[language] = actual
        engine = subprocess.run(["tesseract", "--version"], capture_output=True, timeout=3, check=True)
        version = engine.stdout.decode().splitlines()[0]
        if not version.startswith("tesseract 5."):
            raise ValueError("Tesseract 5 required")
        return {"ready": True, "engine": version, "model_commit": MODEL_COMMIT, "model_sha256": hashes}
    except (OSError, ValueError, subprocess.SubprocessError):
        return {"ready": False, "reason": "Cần Tesseract 5 và hai model vie/eng đúng hash. Chạy lệnh models."}


def recognize(png: bytes, directory: str):
    import os
    metadata = readiness(directory)
    if not metadata["ready"]:
        raise DocumentError("ocr_unavailable", metadata["reason"], 503)
    result = subprocess.run(["tesseract", "stdin", "stdout", "--tessdata-dir", directory,
        "-l", "vie+eng", "--oem", "1", "--psm", "6", "-c", "tessedit_create_tsv=1"], input=png,
        capture_output=True, timeout=35, env={**os.environ, "OMP_THREAD_LIMIT": "1"})
    if result.returncode:
        raise DocumentError("ocr_failed", "OCR không xử lý được tài liệu.")
    tokens = []
    try:
        for row in csv.DictReader(StringIO(result.stdout.decode("utf-8")), delimiter="\t", quoting=csv.QUOTE_NONE):
            if row["level"] != "5" or not row["text"].strip():
                continue
            left, top, width, height = (int(row[k]) for k in ["left", "top", "width", "height"])
            score = float(row["conf"])
            if width <= 0 or height <= 0 or left < 0 or top < 0:
                raise ValueError("invalid geometry")
            tokens.append(Token(text=row["text"], confidence=None if score == -1 else score / 100,
                box=(left, top, left + width, top + height),
                line=tuple(int(row[k]) for k in ["block_num", "par_num", "line_num"])))
    except (ValueError, KeyError, UnicodeError) as exc:
        raise DocumentError("ocr_output", "OCR trả dữ liệu không hợp lệ.") from exc
    metadata.update({"language": "vie+eng", "oem": 1, "psm": 6, "preprocessing": "gray-exif-pdf150-v1"})
    return tokens, metadata


def install_models():
    """Explicit model provisioning; never invoked during extraction."""
    import urllib.request
    from .settings import Settings
    directory = Path(Settings.from_env().tessdata_dir)
    directory.mkdir(parents=True, exist_ok=True)
    for language, expected in MODEL_SHA.items():
        url = f"https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/{MODEL_COMMIT}/{language}.traineddata"
        with urllib.request.urlopen(url, timeout=60) as response:
            data = response.read(8 * 1024 * 1024 + 1)
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError("Downloaded model failed SHA-256 check")
        path = directory / f"{language}.traineddata"
        temporary = path.with_suffix(".partial")
        try:
            temporary.write_bytes(data)
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
    print(json.dumps(readiness(str(directory)), ensure_ascii=False))


if __name__ == "__main__":
    install_models()
