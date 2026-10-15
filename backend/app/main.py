"""FastAPI application entrypoint với health check và xử lý lỗi."""
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging

settings = get_settings()
setup_logging(settings.LOG_LEVEL, settings.LOG_FORMAT)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Khởi tạo và dọn dẹp tài nguyên khi app start/stop."""
    logger.info("Application starting", extra={"app": settings.APP_NAME})
    yield
    logger.info("Application stopped")


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description="Document Intelligence cho biểu mẫu tiếng Việt",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
def health_check() -> dict:
    """Health check cho Docker Compose và monitoring."""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": "0.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/", tags=["system"])
def root() -> dict:
    return {"message": "Document Intelligence API", "docs": "/docs"}


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Xử lý lỗi không lường trước, không lộ chi tiết nội bộ."""
    logger.error(
        "Unhandled error",
        exc_info=exc,
        extra={"request_id": getattr(request.state, "request_id", None)},
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Vui lòng thử lại sau."},
    )
