from collections.abc import AsyncIterator
from uuid import uuid4

import anyio
from fastapi import APIRouter, Request
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from starlette.exceptions import HTTPException
from starlette.types import Message

from document_backend.errors import DocumentError
from document_backend.services.documents import MAX_FILE_BYTES
from document_backend.services.mock_extraction import mock_extraction
from document_contracts.models import APIErrorResponse, ExtractionResponse
from document_pipeline.preprocessing import PreprocessingConfig, PreprocessingError, prepare_document
from document_pipeline.runner import PipelineError, run_document

router = APIRouter(prefix="/api/v1", tags=["documents"])
MAX_REQUEST_BYTES = MAX_FILE_BYTES + 64 * 1024  # Bounded multipart overhead.


async def bounded_body(chunks: AsyncIterator[bytes]) -> bytes:
    body = bytearray()
    async for chunk in chunks:
        if len(body) + len(chunk) > MAX_REQUEST_BYTES:
            raise DocumentError(413, "file_too_large", "Yêu cầu upload vượt giới hạn dung lượng.")
        body.extend(chunk)
    return bytes(body)


@router.post(
    "/extract", response_model=ExtractionResponse,
    summary="Extract a single-page invoice using the configured real or explicit mock mode",
    responses={status: {"model": APIErrorResponse} for status in [413, 415, 422, 503, 504, 500]},
    openapi_extra={"requestBody": {"required": True, "content": {"multipart/form-data": {
        "schema": {"type": "object", "required": ["file"], "additionalProperties": False,
                   "properties": {"file": {"type": "string", "format": "binary"}}},
    }}}},
)
async def extract(request: Request) -> ExtractionResponse:
    if request.headers.get("content-type", "").split(";")[0].strip().lower() != "multipart/form-data":
        raise DocumentError(422, "invalid_request", "Upload cần multipart/form-data với một file.")
    try:
        with anyio.fail_after(30):
            body = await bounded_body(request.stream())
    except TimeoutError as exc:
        raise DocumentError(504, "processing_timeout", "Hết thời gian nhận upload.") from exc

    async def receive() -> Message:
        return {"type": "http.request", "body": body, "more_body": False}

    # Parse only after bounding raw bytes, including requests without Content-Length.
    # The form context closes all UploadFile temporary handles on exit.
    parsed = Request(request.scope, receive=receive)
    try:
        async with parsed.form(max_files=1, max_fields=0) as form:
            if list(form.keys()) != ["file"] or not isinstance(form["file"], UploadFile):
                raise DocumentError(422, "invalid_request", "Cần đúng một file có tên trường file.")
            data = await form["file"].read(MAX_FILE_BYTES + 1)
    except HTTPException as exc:
        raise DocumentError(422, "invalid_request", "Multipart upload không hợp lệ.") from exc
    settings = request.app.state.settings
    try:
        if settings.mode == "mock":
            await run_in_threadpool(prepare_document, data,
                                   PreprocessingConfig(timeout_seconds=settings.processing_timeout))
            return mock_extraction()
        run = await run_in_threadpool(run_document, data, settings.tessdata_dir,
                                     str(uuid4()), settings.processing_timeout)
        return run.result
    except (PipelineError, PreprocessingError) as exc:
        status = {"file_too_large": 413, "unsupported_media_type": 415,
                  "invalid_document": 422, "image_too_large": 422, "multiple_pages": 422,
                  "ocr_unavailable": 503, "processing_timeout": 504}.get(exc.code, 500)
        messages = {413: "Tài liệu vượt giới hạn dung lượng.", 415: "Chỉ hỗ trợ PNG/JPG/PDF.",
                    422: "Tài liệu lỗi, vượt giới hạn pixel hoặc không đúng một trang.",
                    503: "OCR chưa sẵn sàng. Kiểm tra Tesseract và model đã pin.",
                    504: "Quá thời gian xử lý tài liệu.", 500: "Không thể xử lý tài liệu."}
        raise DocumentError(status, exc.code, messages[status]) from exc
