from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.api.documents import router as documents_router

settings = get_settings()
configure_logging(settings.log_level)
app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type"],
)
app.include_router(documents_router, prefix="/api/v1")


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "environment": settings.app_env}
