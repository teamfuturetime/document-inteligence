"""Bound credential JSON before FastAPI parses it or password hashing starts."""

import asyncio
import re

from fastapi import Request
from fastapi.routing import APIRoute
from starlette.requests import ClientDisconnect

from docintel.services.documents import ProductError


async def bounded_auth_body(
    request: Request, *, maximum: int = 4096, timeout: float = 2.0
) -> bytes:
    headers = (
        {"Connection": "close"}
        if request.scope.get("http_version", "1.1").startswith("1.")
        else None
    )

    def error(status, code):
        return ProductError(
            status, code, "Yêu cầu tài khoản không hợp lệ hoặc quá giới hạn.", headers=headers
        )

    lengths = request.headers.getlist("content-length")
    declared = None
    if lengths:
        if (
            len(lengths) != 1
            or not re.fullmatch(r"[0-9]{1,20}", lengths[0])
            or "transfer-encoding" in request.headers
        ):
            raise error(400, "INVALID_CONTENT_LENGTH")
        declared = int(lengths[0])
        if declared > maximum:
            raise error(413, "AUTH_BODY_TOO_LARGE")
    data = bytearray()
    try:
        async with asyncio.timeout(timeout):
            async for chunk in request.stream():
                if len(data) + len(chunk) > maximum:
                    raise error(413, "AUTH_BODY_TOO_LARGE")
                data.extend(chunk)
    except TimeoutError as exc:
        raise error(408, "AUTH_BODY_TIMEOUT") from exc
    except ClientDisconnect as exc:
        raise error(400, "AUTH_BODY_DISCONNECTED") from exc
    if declared is not None and len(data) != declared:
        raise error(400, "AUTH_BODY_LENGTH_MISMATCH")
    return bytes(data)


class BoundedAuthRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        async def bounded(request: Request):
            if request.method == "POST" and request.url.path.endswith("/login"):
                if (
                    request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                    != "application/json"
                ):
                    raise ProductError(415, "AUTH_JSON_REQUIRED", "Đăng nhập yêu cầu JSON.")
            if request.method == "POST":
                data = await bounded_auth_body(request)

                async def receive():
                    return {"type": "http.request", "body": data, "more_body": False}

                request = Request(request.scope, receive=receive)
            return await original(request)

        return bounded
