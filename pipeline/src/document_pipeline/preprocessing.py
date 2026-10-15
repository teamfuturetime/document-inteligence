"""Bounded image/PDF preprocessing in a disposable local worker process."""

import argparse
from dataclasses import asdict, dataclass
import hashlib
from io import BytesIO
import json
import math
from pathlib import Path
import subprocess
import sys

from PIL import Image

PREPROCESSING_VERSION = "1.0.0"
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 25_000_000


class PreprocessingError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class PreprocessingConfig:
    pdf_dpi: int = 150
    max_pixels: int = MAX_PIXELS
    timeout_seconds: float = 30.0

    def __post_init__(self):
        if type(self.pdf_dpi) is not int or not 72 <= self.pdf_dpi <= 300:
            raise ValueError("pdf_dpi must be an integer between 72 and 300")
        if type(self.max_pixels) is not int or not 1 <= self.max_pixels <= MAX_PIXELS:
            raise ValueError("max_pixels must be between 1 and 25,000,000")
        if not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be finite and positive")

    @property
    def sha256(self) -> str:
        text = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(text.encode()).hexdigest()


@dataclass
class PreparedPage:
    image: Image.Image
    metadata: dict


def prepare_document(data: bytes, config: PreprocessingConfig | None = None) -> PreparedPage:
    """Return a detached grayscale page and processed→source transform metadata.

    This does not call OCR, extract fields, or mutate HTTP wire contracts.
    subprocess.run kills/reaps the worker on timeout, including native PDF work.
    """
    config = config or PreprocessingConfig()
    if not data:
        raise PreprocessingError("invalid_document", "Tài liệu rỗng.")
    if len(data) > MAX_FILE_BYTES:
        raise PreprocessingError("file_too_large", "Tài liệu vượt giới hạn 10 MiB.")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "document_pipeline._preprocess_worker",
             str(config.pdf_dpi), str(config.max_pixels)],
            input=data, capture_output=True, timeout=config.timeout_seconds, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise PreprocessingError("processing_timeout", "Preprocessing vượt thời gian cho phép.") from exc
    except OSError as exc:
        raise PreprocessingError("internal_error", "Không khởi động được preprocessing worker.") from exc
    try:
        header, _, payload = result.stdout.partition(b"\n")
        metadata = json.loads(header)
        if "error" in metadata:
            raise PreprocessingError(metadata["error"]["code"], metadata["error"]["message"])
        if result.returncode != 0:
            raise ValueError("worker failed")
        with Image.open(BytesIO(payload)) as image:
            if image.width * image.height > config.max_pixels or image.format != "PNG":
                raise ValueError("invalid worker output")
            normalized = image.convert("L")
    except PreprocessingError:
        raise
    except (ValueError, OSError, KeyError, TypeError) as exc:
        raise PreprocessingError("internal_error", "Preprocessing worker không trả ảnh hợp lệ.") from exc
    metadata.update(
        preprocessing_version=PREPROCESSING_VERSION,
        config=asdict(config), config_sha256=config.sha256,
        input_sha256=hashlib.sha256(data).hexdigest(),
    )
    return PreparedPage(image=normalized, metadata=metadata)


def main():
    parser = argparse.ArgumentParser(description="Normalize one synthetic image/PDF page; no OCR.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True, help="Normalized PNG output")
    parser.add_argument("--dpi", type=int, default=150)
    args = parser.parse_args()
    try:
        # Read at most one byte beyond the file limit rather than loading huge files.
        with args.input.open("rb") as stream:
            page = prepare_document(stream.read(MAX_FILE_BYTES + 1), PreprocessingConfig(pdf_dpi=args.dpi))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        page.image.save(args.output, format="PNG")
        report = args.output.with_suffix(".metadata.json")
        report.write_text(json.dumps(page.metadata, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps({"image": str(args.output), "metadata": str(report)}, ensure_ascii=False))
    except (PreprocessingError, OSError, ValueError) as exc:
        parser.exit(1, f"{getattr(exc, 'code', 'invalid_input')}: {exc}\n")


if __name__ == "__main__":
    main()
