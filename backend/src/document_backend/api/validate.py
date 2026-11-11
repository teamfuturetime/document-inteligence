import asyncio
from collections.abc import AsyncIterator

from fastapi import APIRouter, Request
from fastapi.routing import APIRoute

from document_backend.errors import DocumentError
from document_backend.services.notifications import ReviewValidated, notify_safely
from document_backend.services.validation import validate_review
from document_contracts.models import APIErrorResponse, ValidationRequest, ValidationResponse

MAX_VALIDATION_BYTES = 32 * 1024
RECEIVE_TIMEOUT_SECONDS = 1.0


async def bounded_validation_body(chunks: AsyncIterator[bytes]) -> bytes:
    body = bytearray()
    try:
        async with asyncio.timeout(RECEIVE_TIMEOUT_SECONDS):
            async for chunk in chunks:
                if len(body) + len(chunk) > MAX_VALIDATION_BYTES:
                    raise DocumentError(413, "invalid_request", "JSON vượt giới hạn 32 KiB.")
                body.extend(chunk)
    except TimeoutError as exc:
        raise DocumentError(504, "processing_timeout", "Hết thời gian nhận JSON.") from exc
    return bytes(body)


class BoundedValidationRoute(APIRoute):
    """Bound bytes before FastAPI parses JSON, retaining its schema/error handling."""

    def get_route_handler(self):
        original = super().get_route_handler()

        async def bounded(request: Request):
            body = await bounded_validation_body(request.stream())

            async def receive():
                return {"type": "http.request", "body": body, "more_body": False}

            return await original(Request(request.scope, receive=receive))

        return bounded


router = APIRouter(prefix="/api/v1", tags=["documents"], route_class=BoundedValidationRoute)


@router.post("/validate", response_model=ValidationResponse,
             responses={status: {"model": APIErrorResponse} for status in [413, 422, 504, 500]})
async def validate(body: ValidationRequest, request: Request) -> ValidationResponse:
    result = validate_review(body)
    if result.valid:
        await notify_safely(request.app.state.review_notifier,
                            ReviewValidated(invoice_number=result.normalized_values.invoice_number))
    return result
