"""Run with: python -m uvicorn document_backend.main:app."""

from fastapi import FastAPI

from document_backend.api.health import router as health_router
from document_backend.api.extract import router as extract_router
from document_backend.api.validate import router as validate_router
from document_backend.errors import register_error_handlers


def create_app() -> FastAPI:
    application = FastAPI(
        title="Vietnamese Document Intelligence",
        version="0.1.0",
        description=(
            "Health and fixed mock upload demo. Mock invoice values are not derived "
            "from uploaded content. Reviewed invoice values can be validated separately."
        ),
    )
    register_error_handlers(application)
    application.include_router(health_router)
    application.include_router(extract_router)
    application.include_router(validate_router)
    return application


app = create_app()
