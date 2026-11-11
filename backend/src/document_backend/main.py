"""Run with: python -m uvicorn document_backend.main:app."""

from fastapi import FastAPI

from document_backend.api.health import router as health_router
from document_backend.api.extract import router as extract_router
from document_backend.api.validate import router as validate_router
from document_backend.errors import register_error_handlers
from document_backend.services.notifications import LoggingReviewNotifier
from document_backend.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    application = FastAPI(
        title="Vietnamese Document Intelligence",
        version="0.1.0",
        description=(
            "Single-page Vietnamese invoice OCR, field extraction and review validation. "
            "Real mode by default; explicit mock mode is available for development."
        ),
    )
    register_error_handlers(application)
    application.state.settings = settings or Settings.from_environment()
    application.state.review_notifier = LoggingReviewNotifier()
    application.include_router(health_router)
    application.include_router(extract_router)
    application.include_router(validate_router)
    return application


app = create_app()
