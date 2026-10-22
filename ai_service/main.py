"""FastAPI adapter mỏng cho AI service."""
from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile

from ai_service.config import MAX_UPLOAD_SIZE_BYTES, OCR_ENGINE, OCR_FALLBACK_ENABLED, OCR_LANG
from ai_service.ocr.engine import VietnameseOCREngine, available_engines
from ai_service.pipeline import DocumentPipeline, PipelineError
from ai_service.validation import DocumentValidationError, validate_document

logger = logging.getLogger(__name__)
app = FastAPI(title="Document Intelligence AI Service", version="0.2.0")


@app.get("/health", tags=["system"])
def health() -> dict:
    engines = available_engines()
    return {
        "status": "ready" if OCR_ENGINE in engines else "degraded",
        "configured_engine": OCR_ENGINE,
        "available_engines": engines,
    }


@app.post("/process", tags=["processing"])
async def process_document(file: UploadFile = File(...)) -> dict:
    filename = file.filename or "document"
    suffix = Path(filename).suffix.lower()
    temporary_path: Path | None = None
    size = 0
    header = b""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temporary:
            temporary_path = Path(temporary.name)
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD_SIZE_BYTES:
                    raise HTTPException(status_code=413, detail="File vượt quá giới hạn dung lượng")
                header = (header + chunk)[:16]
                temporary.write(chunk)
        if size == 0:
            raise DocumentValidationError("File rỗng")
        validate_document(filename, header)
        engine = VietnameseOCREngine(
            prefer=OCR_ENGINE,
            tesseract_lang=OCR_LANG,
            allow_fallback=OCR_FALLBACK_ENABLED,
        )
        return DocumentPipeline(engine).process(temporary_path)
    except DocumentValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PipelineError as exc:
        logger.warning("Document processing failed", exc_info=exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
