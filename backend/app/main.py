from fastapi import FastAPI

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.api.documents import router as documents_router

settings = get_settings()
configure_logging(settings.log_level)
app = FastAPI(title=settings.app_name, version="0.1.0")
app.include_router(documents_router, prefix="/api/v1")


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "environment": settings.app_env}
