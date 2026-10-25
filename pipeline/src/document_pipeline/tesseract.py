"""Tesseract subprocess/TSV adapter. See docs/ml/source-lineage.md for prior work."""

import hashlib
import json
import math
import os
import re
import subprocess
import tempfile
import time
from contextlib import contextmanager
from importlib.resources import files
from pathlib import Path

from document_pipeline.config import PipelineConfig
from document_pipeline.errors import PipelineError
from document_pipeline.models import Token
from document_pipeline.preprocessing import PreparedImage

MODEL_LOCK = json.loads(
    files("document_pipeline").joinpath("resources/tessdata-lock.json").read_text()
)
TSV_HEADER = (
    "level page_num block_num par_num line_num word_num left top width height conf text".split()
)


def verify_models(directory: Path) -> dict[str, str]:
    hashes = {}
    for language, expected in MODEL_LOCK["models"].items():
        path = directory / f"{language}.traineddata"
        try:
            if not path.is_file():
                raise OSError("model is not a regular file")
            with path.open("rb") as stream:
                content = stream.read(10 * 1024 * 1024 + 1)
            actual = hashlib.sha256(content).hexdigest()
        except OSError as exc:
            raise PipelineError("PROVIDER_UNAVAILABLE", "Thiếu model OCR đã pin.") from exc
        if actual != expected:
            raise PipelineError("MODEL_HASH_MISMATCH", "Model OCR không khớp checksum đã pin.")
        hashes[language] = actual
    return hashes


def execute(command: list[str], timeout: float, data: bytes | None = None):
    if timeout <= 0:
        raise PipelineError("PROCESSING_TIMEOUT", "OCR quá thời gian.")
    try:
        return subprocess.run(
            command,
            input=data,
            capture_output=True,
            timeout=timeout,
            check=False,
            env={**os.environ, "OMP_THREAD_LIMIT": "1"},
        )
    except subprocess.TimeoutExpired as exc:
        raise PipelineError("PROCESSING_TIMEOUT", "OCR quá thời gian.") from exc
    except OSError as exc:
        raise PipelineError("PROVIDER_UNAVAILABLE", "Không khởi động được Tesseract.") from exc


@contextmanager
def native_model_directory(directory: Path):
    # Some Windows Tesseract builds cannot open Unicode command-line paths. Keep
    # the configured, hash-checked source and copy only these two small models to
    # an ASCII temporary directory, removed after the native process has exited.
    if os.name != "nt" or str(directory.resolve()).isascii():
        yield directory.resolve()
        return
    with tempfile.TemporaryDirectory(prefix="docintel-models-") as temporary:
        native = Path(temporary)
        if not str(native).isascii():
            raise PipelineError("PROVIDER_UNAVAILABLE", "Tesseract cần thư mục model ASCII.")
        for language in MODEL_LOCK["models"]:
            with (directory / f"{language}.traineddata").open("rb") as stream:
                content = stream.read(10 * 1024 * 1024 + 1)
            (native / f"{language}.traineddata").write_bytes(content)
        verify_models(native)
        yield native


def probe(executable: str, directory: Path, timeout: float = 5.0) -> dict:
    models = verify_models(directory)
    result = execute([executable, "--version"], timeout)
    match = re.match(rb"tesseract v?(5\.\d+\.\d+(?:[-\w.]*)?)\b", result.stdout)
    if result.returncode or match is None:
        raise PipelineError("PROVIDER_UNAVAILABLE", "Cần Tesseract phiên bản 5.")
    return {
        "engine_version": match[1].decode("ascii"),
        "model_revision": MODEL_LOCK["revision"],
        "model_sha256": models,
    }


def parse_tsv(data: bytes, page: PreparedImage) -> tuple[Token, ...]:
    try:
        rows = data.decode("utf-8").splitlines()
        if not rows or rows[0].split("\t") != TSV_HEADER:
            raise ValueError("TSV header")
        tokens = []
        for row in rows[1:]:
            if not row:
                continue
            values = row.split("\t", 11)
            if len(values) != 12:
                raise ValueError("TSV row")
            record = dict(zip(TSV_HEADER, values, strict=True))
            level = int(record["level"])
            if int(record["page_num"]) != 1 or level not in range(1, 6):
                raise ValueError("TSV page")
            if level != 5 or not record["text"].strip():
                continue
            if any(
                int(record[key]) < 1 for key in ("block_num", "par_num", "line_num", "word_num")
            ):
                raise ValueError("TSV word identifiers")
            x, y, w, h = (int(record[key]) for key in ("left", "top", "width", "height"))
            if min(x, y, w, h) < 0 or w == 0 or h == 0:
                raise ValueError("TSV rectangle")
            if x + w > page.processed_width or y + h > page.processed_height:
                raise ValueError("TSV out of bounds")
            confidence = float(record["conf"])
            if not math.isfinite(confidence) or confidence != -1 and not 0 <= confidence <= 100:
                raise ValueError("TSV confidence")
            tokens.append(
                Token(
                    token_id=f"p0-w{len(tokens)}",
                    line_id="-".join(record[key] for key in ("block_num", "par_num", "line_num")),
                    text=record["text"].strip(),
                    box=page.source_box((x, y, x + w, y + h)),
                    confidence=None if confidence == -1 else confidence / 100,
                )
            )
        return tuple(tokens)
    except (ValueError, UnicodeError) as exc:
        raise PipelineError("INVALID_OCR_OUTPUT", "OCR trả dữ liệu không hợp lệ.") from exc


def recognize(page: PreparedImage, directory: Path, executable: str, config: PipelineConfig):
    deadline = time.monotonic() + config.timeout_seconds
    metadata = probe(executable, directory, min(5.0, config.timeout_seconds))
    with native_model_directory(directory) as native:
        result = execute(
            [
                executable,
                "stdin",
                "stdout",
                "--tessdata-dir",
                str(native),
                "-l",
                "vie+eng",
                "--oem",
                "1",
                "--psm",
                str(config.psm),
                "--dpi",
                "300",
                "-c",
                "tessedit_create_tsv=1",
            ],
            deadline - time.monotonic(),
            page.png,
        )
    if result.returncode:
        raise PipelineError("PROVIDER_FAILED", "OCR không xử lý được tài liệu.")
    return parse_tsv(result.stdout, page), metadata
