"""Local HTTP boundary; AI packages never import FastAPI."""

import asyncio
from dataclasses import replace
import json
import time
from typing import Literal

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from starlette.concurrency import run_in_threadpool

from .contracts import ExportRequest, Kind, LABELS, MODELS, Mode, Review, TITLES, reviewed_export, validate_values
from .ocr import DocumentError, MAX_BYTES
from .ocr_backends import available
from .pipeline import run
from .settings import Settings


class UploadLimit:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        size, start, chunks = 0, time.monotonic(), []
        try:
            while True:
                remaining = 30 - (time.monotonic() - start)
                message = await asyncio.wait_for(receive(), timeout=max(.001, remaining))
                if message["type"] == "http.disconnect":
                    return
                size += len(message.get("body", b""))
                if size > MAX_BYTES + 128 * 1024:
                    raise DocumentError("file_size", "Request vượt giới hạn upload.", 413)
                chunks.append(message.get("body", b""))
                if not message.get("more_body", False):
                    break
        except DocumentError as exc:
            return await JSONResponse({"error": {"code": exc.code, "message": exc.message}}, status_code=exc.status)(scope, receive, send)
        except TimeoutError:
            return await JSONResponse({"error": {"code": "upload_timeout", "message": "Upload quá thời gian cho phép."}}, status_code=408)(scope, receive, send)
        body, delivered = b"".join(chunks), False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()
        await self.app(scope, replay, send)


def create_app(settings=None):
    settings = settings or Settings.from_env()
    app = FastAPI(title="AI-02 Solo", version="0.1.0")
    app.add_middleware(UploadLimit)
    capacity = asyncio.Semaphore(2)

    @app.exception_handler(DocumentError)
    async def document_error(request, exc):
        return JSONResponse({"error": {"code": exc.code, "message": exc.message}}, status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def request_error(request, exc):
        return JSONResponse({"error": {"code": "invalid_request", "message": "Request không khớp schema API."}}, status_code=422)

    @app.exception_handler(ValueError)
    async def value_error(request, exc):
        return JSONResponse({"error": {"code": "invalid_values", "message": str(exc)}}, status_code=422)

    @app.get("/health")
    async def health():
        providers = await run_in_threadpool(available, settings)
        return {"app": "AI-02 Solo", "ocr": {**providers[settings.ocr_provider], "provider": settings.ocr_provider},
            "ocr_providers": providers, "vlm": {"provider": settings.vlm_provider,
            "model": settings.vlm_model or None, "configured": bool(settings.vlm_model), "inference_verified": False}}

    @app.get("/api/schemas")
    def schemas():
        return {kind: {"title": TITLES[kind], "fields": [
            {"key": key, "label": aliases[0], "type": "date" if key.endswith("_date") else "text"}
            for key, aliases in fields.items()], "json_schema": MODELS[kind].model_json_schema()}
            for kind, fields in LABELS.items()}

    @app.post("/api/extract")
    async def extract(document_type: Kind = Form(), mode: Mode = Form(), file: UploadFile = File(),
                      ocr_provider: Literal["tesseract", "ocrspace"] | None = Form(None)):
        try:
            data = await file.read(MAX_BYTES + 1)
        finally:
            await file.close()
        if capacity.locked():
            raise DocumentError("busy", "Đang xử lý tài liệu khác. Vui lòng thử lại.", 429)
        async with capacity:
            selected = replace(settings, ocr_provider=ocr_provider or settings.ocr_provider)
            result = await run_in_threadpool(run, data, document_type, mode, selected)
        return result.model_dump(mode="json")

    @app.post("/api/validate")
    def validate(request: Review):
        return validate_values(request.document_type, request.values)

    @app.post("/api/export")
    def export(request: ExportRequest):
        result = reviewed_export(request)
        return Response(json.dumps(result, ensure_ascii=False, indent=2) + "\n", media_type="application/json",
            headers={"Content-Disposition": 'attachment; filename="ai02-reviewed.json"'})

    return app


app = create_app()
