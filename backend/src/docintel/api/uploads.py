"""Bound reception separately from native processing and the persisted OCR queue."""

import re

from anyio import fail_after
from starlette.requests import ClientDisconnect, Request

from docintel.config import Settings
from docintel.services.documents import ProductError


def upload_error(request: Request, status: int, code: str, message: str) -> ProductError:
    # Do not reuse an HTTP/1 connection whose unread body may still be arriving.
    headers = {"Connection": "close"} if request.scope["http_version"].startswith("1.") else None
    return ProductError(status, code, message, headers=headers)


async def receive_upload(request: Request, settings: Settings) -> bytes:
    lengths = request.headers.getlist("content-length")
    declared = None
    if lengths:
        if (
            len(lengths) != 1
            or not re.fullmatch(r"[0-9]{1,20}", lengths[0])
            or "transfer-encoding" in request.headers
        ):
            raise upload_error(
                request, 400, "INVALID_CONTENT_LENGTH", "Độ dài yêu cầu không hợp lệ."
            )
        declared = int(lengths[0])
        if declared > settings.max_upload_bytes:
            raise upload_error(request, 413, "FILE_TOO_LARGE", "Tài liệu vượt giới hạn kích thước.")

    data = bytearray()
    try:
        # One deadline for the entire body, never reset by a trickled chunk.
        with fail_after(settings.upload_receive_timeout_seconds):
            async for chunk in request.stream():
                size = len(data) + len(chunk)
                if size > settings.max_upload_bytes:
                    raise upload_error(
                        request, 413, "FILE_TOO_LARGE", "Tài liệu vượt giới hạn kích thước."
                    )
                if declared is not None and size > declared:
                    raise upload_error(
                        request, 400, "UPLOAD_LENGTH_MISMATCH", "Độ dài dữ liệu không khớp."
                    )
                data.extend(chunk)
    except TimeoutError as exc:
        raise upload_error(
            request, 408, "UPLOAD_TIMEOUT", "Nhận tài liệu quá thời gian. Vui lòng thử lại."
        ) from exc
    except ClientDisconnect as exc:
        raise upload_error(
            request, 400, "UPLOAD_DISCONNECTED", "Kết nối bị ngắt khi nhận tài liệu."
        ) from exc
    if declared is not None and len(data) != declared:
        raise upload_error(request, 400, "UPLOAD_LENGTH_MISMATCH", "Độ dài dữ liệu không khớp.")
    return bytes(data)
