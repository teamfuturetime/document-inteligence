"""Tesseract 5 adapter producing the unchanged OCRResult v1 wire contract."""

import argparse
from dataclasses import asdict, dataclass
import hashlib
from io import BytesIO
import json
import math
import os
from pathlib import Path
import re
import subprocess
import time

from document_contracts.models import OCRPage, OCRResult, OCRToken
from document_pipeline.ocr_models import MODEL_LOCK, MODELSET_SHA256, ModelError, verify_models
from document_pipeline.preprocessing import (
    MAX_FILE_BYTES, MAX_PIXELS, PreparedPage, PreprocessingError, prepare_document,
)

ADAPTER_VERSION = "1.0.0"
TSV_HEADER = "level page_num block_num par_num line_num word_num left top width height conf text".split()


class OCRError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class OCRConfig:
    psm: int = 3
    image_dpi: int = 150
    timeout_seconds: float = 30.0

    def __post_init__(self):
        # 0/1/2/12 require OSD or do not recognize text; baseline has no OSD model.
        if type(self.psm) is not int or self.psm not in {3, 4, 5, 6, 7, 8, 9, 10, 11, 13}:
            raise ValueError("psm must recognize text without OSD")
        if type(self.image_dpi) is not int or not 72 <= self.image_dpi <= 300:
            raise ValueError("image_dpi must be between 72 and 300")
        if not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be finite and positive")


@dataclass
class OCRRun:
    result: OCRResult
    metadata: dict


def parse_tsv(data: bytes, page: OCRPage) -> list[OCRToken]:
    """Keep word rows in engine reading order; reject malformed output wholesale."""
    try:
        lines = data.decode("utf-8").splitlines()
        if not lines or lines[0].split("\t") != TSV_HEADER:
            raise ValueError("invalid TSV header")
        tokens = []
        for line in lines[1:]:
            if not line:
                continue
            columns = line.split("\t", 11)
            if len(columns) != 12:
                raise ValueError("invalid TSV row")
            row = dict(zip(TSV_HEADER, columns))
            level = int(row["level"])
            if not 1 <= level <= 5 or int(row["page_num"]) != 1:
                raise ValueError("invalid TSV page or level")
            if level != 5 or not row["text"].strip():
                continue
            score = float(row["conf"])
            if not math.isfinite(score) or (score != -1 and not 0 <= score <= 100):
                raise ValueError("invalid TSV confidence")
            left, top, width, height = (int(row[key]) for key in ("left", "top", "width", "height"))
            token = OCRToken(
                text=row["text"].strip(), confidence=None if score == -1 else score / 100,
                box={"x0": left, "y0": top, "x1": left + width, "y1": top + height},
            )
            if token.box.x1 > page.width or token.box.y1 > page.height:
                raise ValueError("TSV box exceeds page")
            tokens.append(token)
        return tokens
    except (ValueError, UnicodeError) as exc:
        raise OCRError("internal_error", "Tesseract trả TSV không hợp lệ.") from exc


def run_engine(command: list[str], timeout: float, data: bytes | None = None):
    if timeout <= 0:
        raise OCRError("processing_timeout", "OCR vượt thời gian cho phép.")
    try:
        return subprocess.run(
            command, input=data, capture_output=True, timeout=timeout, check=False,
            env={**os.environ, "OMP_THREAD_LIMIT": "1"},
        )
    except subprocess.TimeoutExpired as exc:
        raise OCRError("processing_timeout", "OCR vượt thời gian cho phép.") from exc
    except OSError as exc:
        raise OCRError("ocr_unavailable", "Không khởi động được Tesseract.") from exc


def recognize(page: PreparedPage, tessdata_dir: Path, config: OCRConfig | None = None,
              executable: str = "tesseract") -> OCRRun:
    config = config or OCRConfig()
    deadline = time.monotonic() + config.timeout_seconds
    if page.image.mode != "L" or page.image.width * page.image.height > MAX_PIXELS:
        raise OCRError("invalid_document", "OCR cần ảnh grayscale đã tiền xử lý trong giới hạn pixel.")
    try:
        output_page = OCRPage(page=1, width=page.image.width, height=page.image.height,
                              to_original=page.metadata["to_original"], tokens=[])
    except (ValueError, KeyError) as exc:
        raise OCRError("invalid_document", "Thiếu metadata tọa độ hợp lệ.") from exc
    try:
        model_hashes = verify_models(tessdata_dir)
    except ModelError as exc:
        raise OCRError("ocr_unavailable", str(exc)) from exc
    version = run_engine([executable, "--version"], min(5, deadline - time.monotonic()))
    match = re.match(rb"tesseract (5\.\d+\.\d+(?:[-\w.]*)?)\b", version.stdout)
    if version.returncode != 0 or match is None:
        raise OCRError("ocr_unavailable", "Adapter yêu cầu Tesseract phiên bản 5.")
    engine_version = match.group(1).decode("ascii")
    stream = BytesIO()
    page.image.save(stream, format="PNG")
    dpi = page.metadata.get("pdf_dpi", config.image_dpi)
    output = run_engine([
        executable, "stdin", "stdout", "--tessdata-dir", str(tessdata_dir.resolve()),
        "-l", "vie+eng", "--oem", "1", "--psm", str(config.psm), "--dpi", str(dpi),
        "-c", "tessedit_create_tsv=1",
    ], deadline - time.monotonic(), stream.getvalue())
    if output.returncode != 0:
        # Do not expose stderr, source text, paths, or silently retry another model.
        raise OCRError("ocr_unavailable", "Tesseract không xử lý được trang với model đã pin.")
    tokens = parse_tsv(output.stdout, output_page)
    if time.monotonic() > deadline:
        raise OCRError("processing_timeout", "OCR vượt thời gian cho phép.")
    output_page = OCRPage(**{**output_page.model_dump(), "tokens": tokens})
    result = OCRResult(
        schema_version="1.0.0", mode="real", language="vie+eng", page=output_page,
        ocr_version=(f"tesseract-{engine_version}:fast-{MODEL_LOCK['revision'][:12]}:"
                     f"{MODELSET_SHA256[:12]}:adapter-{ADAPTER_VERSION}"),
    )
    settings = {**asdict(config), "effective_dpi": dpi, "language": "vie+eng", "oem": 1,
                "omp_thread_limit": 1, "adapter_version": ADAPTER_VERSION,
                "modelset_sha256": MODELSET_SHA256}
    return OCRRun(result, {
        "engine_version": engine_version, "model_revision": MODEL_LOCK["revision"],
        "model_sha256": model_hashes, "config": settings,
        "config_sha256": hashlib.sha256(json.dumps(settings, sort_keys=True).encode()).hexdigest(),
        "preprocessing": page.metadata, "warnings": [] if tokens else ["no_text_detected"],
    })


def main():
    parser = argparse.ArgumentParser(description="Run real vie+eng OCR on one synthetic document.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--tessdata-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="OCRResult JSON output")
    args = parser.parse_args()
    try:
        with args.input.open("rb") as stream:
            page = prepare_document(stream.read(MAX_FILE_BYTES + 1))
        run = recognize(page, args.tessdata_dir)
        report = args.output.with_suffix(".metadata.json")
        if report == args.output or args.input.resolve() in {args.output.resolve(), report.resolve()}:
            raise ValueError("Output và metadata phải khác nhau và khác input")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(run.result.model_dump_json(indent=2) + "\n", encoding="utf-8")
        report.write_text(json.dumps(run.metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"result": str(args.output), "metadata": str(report),
                          "tokens": len(run.result.page.tokens)}, ensure_ascii=False))
    except (OCRError, PreprocessingError, OSError, ValueError) as exc:
        parser.exit(1, f"{getattr(exc, 'code', 'invalid_input')}: {exc}\n")


if __name__ == "__main__":
    main()
