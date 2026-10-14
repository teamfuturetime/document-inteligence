from collections.abc import AsyncIterator

import anyio
from fastapi import APIRouter, Request
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from starlette.exceptions import HTTPException
from starlette.types import Message

from document_backend.errors import DocumentError
from document_backend.services.documents import MAX_FILE_BYTES, validate_document
from document_backend.services.mock_extraction import mock_extraction
from document_contracts.models import APIErrorResponse, ExtractionResponse

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
    summary="Validate an upload and return a fixed mock invoice (no OCR)",
    responses={status: {"model": APIErrorResponse} for status in [413, 415, 422, 504, 500]},
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
            await run_in_threadpool(validate_document, data)
    except HTTPException as exc:
        raise DocumentError(422, "invalid_request", "Multipart upload không hợp lệ.") from exc
    return mock_extraction()
