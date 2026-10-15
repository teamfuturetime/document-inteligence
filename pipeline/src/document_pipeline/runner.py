"""Single bounded pipeline entry point shared by HTTP and evaluation (POSIX)."""

from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys

from document_contracts.models import ExtractionResponse, OCRResult
from document_pipeline.preprocessing import MAX_FILE_BYTES


class PipelineError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass
class PipelineRun:
    result: ExtractionResponse
    ocr: OCRResult
    metadata: dict


def run_document(data: bytes, tessdata_dir: Path, document_id: str,
                 timeout: float = 30) -> PipelineRun:
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be finite and positive")
    if len(data) > MAX_FILE_BYTES:
        raise PipelineError("file_too_large")
    if not data:
        raise PipelineError("invalid_document")
    if os.name != "posix":
        raise PipelineError("internal_error")
    try:
        process = subprocess.Popen(
            [sys.executable, "-m", "document_pipeline._pipeline_worker",
             str(tessdata_dir.resolve()), document_id],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            start_new_session=True,
        )
        try:
            output, _ = process.communicate(input=data, timeout=timeout)
        except BaseException:
            # New process group includes preprocessing and native Tesseract children.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.communicate()
            raise
    except subprocess.TimeoutExpired as exc:
        raise PipelineError("processing_timeout") from exc
    except OSError as exc:
        raise PipelineError("internal_error") from exc
    try:
        payload = json.loads(output)
        if process.returncode != 0:
            code = payload.get("error", "internal_error")
            if code not in {"invalid_document", "file_too_large", "image_too_large", "multiple_pages",
                            "unsupported_media_type", "ocr_unavailable", "processing_timeout"}:
                code = "internal_error"
            raise PipelineError(code)
        return PipelineRun(ExtractionResponse.model_validate(payload["result"]),
                           OCRResult.model_validate(payload["ocr"]), payload["metadata"])
    except PipelineError:
        raise
    except (ValueError, KeyError, TypeError) as exc:
        raise PipelineError("internal_error") from exc
