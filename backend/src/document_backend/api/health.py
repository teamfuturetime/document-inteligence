from fastapi import APIRouter, Request

from document_pipeline.ocr import OCRError, run_engine
from document_pipeline.ocr_models import ModelError, verify_models

from document_contracts.models import APIErrorResponse, HealthResponse

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={500: {"model": APIErrorResponse}},
    summary="Service health; OCR readiness reported separately",
)
def health(request: Request) -> HealthResponse:
    settings = request.app.state.settings
    ready = False
    if settings.mode == "real":
        try:
            verify_models(settings.tessdata_dir)
            version = run_engine(["tesseract", "--version"], 3)
            ready = version.returncode == 0 and version.stdout.startswith(b"tesseract 5.")
        except (ModelError, OCRError):
            pass
    return HealthResponse(status="ok", mode=settings.mode, ocr_ready=ready)
