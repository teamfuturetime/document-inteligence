from fastapi import APIRouter

from document_contracts.models import APIErrorResponse, HealthResponse

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={500: {"model": APIErrorResponse}},
    summary="Service health; OCR readiness reported separately",
)
def health() -> HealthResponse:
    # No OCR adapter or extraction service has been wired into this skeleton.
    return HealthResponse(status="ok", mode="mock", ocr_ready=False)
