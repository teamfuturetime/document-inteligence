"""Local Tesseract CLI adapter. No network, model downloads or fake fallback."""

import csv
import hashlib
from io import BytesIO, StringIO
import json
import math
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError, __version__ as pillow_version
from pydantic import ValidationError

from app.providers.contracts import ProviderError
from app.schemas.extraction import BoundingBox, DocumentInput, ProviderIdentity
from app.schemas.ocr import OCRMetadata, OCRResult, OCRWord

_HEADER = "level page_num block_num par_num line_num word_num left top width height conf text".split()


def _invoke(args: list[str], timeout: float, content: bytes | None = None) -> bytes:
    try:
        result = subprocess.run(
            args, input=content, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=timeout, check=False, shell=False,
        )
    except subprocess.TimeoutExpired:
        # subprocess.run kills and waits for its child before raising TimeoutExpired.
        raise ProviderError("provider_timeout") from None
    except OSError:
        raise ProviderError("provider_unavailable") from None
    if result.returncode != 0:
        # stderr can contain document text/paths; never expose it as a public error.
        raise ProviderError("provider_failed")
    return result.stdout


def parse_tsv(raw: str, width: int, height: int) -> list[OCRWord]:
    """Keep word text and native scores, rejecting malformed or out-of-bounds output."""
    try:
        reader = csv.DictReader(StringIO(raw), delimiter="\t", quoting=csv.QUOTE_NONE)
        if reader.fieldnames != _HEADER:
            raise ValueError("Unexpected TSV header")
        words = []
        pages = 0
        for row in reader:
            if set(row) != set(_HEADER) or any(value is None for value in row.values()):
                raise ValueError("Malformed TSV row")
            level, page = int(row["level"]), int(row["page_num"])
            left, top, w, h = (int(row[key]) for key in ("left", "top", "width", "height"))
            if level not in range(1, 6) or page != 1:
                raise ValueError("Only one-page TSV is supported")
            if min(left, top, w, h) < 0 or left + w > width or top + h > height:
                raise ValueError("Invalid TSV geometry")
            if level == 1:
                pages += 1
                if (left, top, w, h) != (0, 0, width, height):
                    raise ValueError("Wrong source image size")
            if level != 5 or not row["text"].strip():
                continue
            score = float(row["conf"])
            words.append(OCRWord(
                text=row["text"], page=1,
                bbox=BoundingBox(x0=left, y0=top, x1=left+w, y1=top+h),
                native_confidence=None if score == -1 else score,
            ))
        if pages != 1:
            raise ValueError("Missing/duplicate page")
        return words
    except (ValueError, TypeError, csv.Error, ValidationError):
        raise ProviderError("provider_failed") from None


class TesseractOCRProvider:
    def __init__(
        self, executable: str = "tesseract", *, tessdata_dir: Path | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        if isinstance(timeout_seconds, bool) or not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive and finite")
        self.executable = executable
        self.tessdata_dir = tessdata_dir
        self.timeout_seconds = float(timeout_seconds)

    @property
    def identity(self) -> ProviderIdentity:
        return ProviderIdentity(name="tesseract-ocr", implementation_version="1.0.0",
                                config_version="tesseract-ocr-1", mode="real")

    def recognize(self, document: DocumentInput) -> OCRResult:
        try:
            document = DocumentInput.model_validate(document.model_dump(warnings=False))
        except (AttributeError, ValidationError, ValueError, TypeError):
            raise ProviderError("invalid_document") from None
        # Adapter resource guards, not invoice business rules or an upload API policy.
        if len(document.content) > 10 * 1024 * 1024:
            raise ProviderError("invalid_document")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(BytesIO(document.content)) as source:
                    expected = {"image/png": "PNG", "image/jpeg": "JPEG"}[document.media_type]
                    if (source.format != expected or source.width * source.height > 20_000_000
                            or getattr(source, "n_frames", 1) != 1):
                        raise ValueError("Unsupported image")
                    source.load()
                    oriented = ImageOps.exif_transpose(source).convert("RGBA")
                    image = Image.new("RGBA", oriented.size, "white")
                    image.alpha_composite(oriented)
                    image = image.convert("RGB")
                    buffer = BytesIO()
                    image.save(buffer, format="PNG")
                    content = buffer.getvalue()
                    width, height = image.size
        except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombWarning,
                Image.DecompressionBombError):
            raise ProviderError("invalid_document") from None

        executable = shutil.which(self.executable)
        if executable is None:
            raise ProviderError("provider_unavailable")
        tessdata = self.tessdata_dir or Path(executable).parent / "tessdata"
        try:
            models = {language: hashlib.sha256((tessdata / f"{language}.traineddata").read_bytes()).hexdigest()
                      for language in ("vie",)}
        except OSError:
            raise ProviderError("provider_unavailable") from None
        try:
            version = _invoke([executable, "--version"], self.timeout_seconds).decode("utf-8").splitlines()[0]
            if not version.startswith("tesseract "):
                raise ValueError("Unknown engine")
            config = {"languages": "vie", "oem": 1, "psm": 6, "dpi": 300,
                      "timeout_seconds": self.timeout_seconds, "max_bytes": 10 * 1024 * 1024,
                      "max_pixels": 20_000_000, "preprocessing": "exif_transposed_rgb_white",
                      "outputs": "txt+tsv"}
            with TemporaryDirectory(prefix="ai02-ocr-") as directory:
                output = Path(directory) / "result"
                _invoke([
                    executable, "stdin", str(output), "--tessdata-dir", str(tessdata),
                    "-l", "vie", "--oem", "1", "--psm", "6", "--dpi", "300",
                    "-c", "tessedit_create_txt=1", "-c", "tessedit_create_tsv=1",
                ], self.timeout_seconds, content)
                raw_text = output.with_suffix(".txt").read_bytes().decode("utf-8")
                raw_tsv = output.with_suffix(".tsv").read_bytes().decode("utf-8")
            words = parse_tsv(raw_tsv, width, height)
            if bool(raw_text.strip()) != bool(words):
                raise ValueError("Inconsistent text and word output")
            return OCRResult(
                document_id=document.document_id, input_sha256=hashlib.sha256(document.content).hexdigest(),
                processed_image_sha256=hashlib.sha256(content).hexdigest(), width=width, height=height,
                raw_text=raw_text, raw_tsv=raw_tsv, words=words,
                metadata=OCRMetadata(
                    provider=self.identity, engine_version=version, model_sha256=models,
                    configuration=config, config_sha256=hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest(),
                    pillow_version=pillow_version,
                ), warnings=[] if words else ["no_text"],
            )
        except (OSError, UnicodeError, ValueError, IndexError, ValidationError):
            raise ProviderError("provider_failed") from None
