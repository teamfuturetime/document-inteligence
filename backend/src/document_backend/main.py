"""Run with: python -m uvicorn document_backend.main:app."""

from fastapi import FastAPI

from document_backend.api.health import router as health_router
from document_backend.errors import register_error_handlers


def create_app() -> FastAPI:
    application = FastAPI(
        title="Vietnamese Document Intelligence",
        version="0.1.0",
        description=(
            "Backend skeleton: health only. OCR, extraction and review validation "
            "are not implemented yet."
        ),
    )
    register_error_handlers(application)
    application.include_router(health_router)
    return application


app = create_app()
