"""Stable error responses; never serialize request bodies or raw exceptions."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from document_contracts.models import APIErrorDetail, APIErrorResponse


class DocumentError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code


def error_response(status: int, code: str, message: str) -> JSONResponse:
    payload = APIErrorResponse(
        error=APIErrorDetail(code=code, message=message, field=None)
    )
    return JSONResponse(status_code=status, content=payload.model_dump(mode="json"))


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DocumentError)
    async def document_error(request: Request, exc: DocumentError):
        return error_response(exc.status, exc.code, str(exc))

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, exc: RequestValidationError):
        return error_response(422, "invalid_request", "Yêu cầu không đúng cấu trúc dữ liệu.")

    @app.exception_handler(Exception)
    async def internal_error(request: Request, exc: Exception):
        return error_response(500, "internal_error", "Không thể xử lý yêu cầu.")
