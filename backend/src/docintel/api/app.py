import asyncio
from contextlib import asynccontextmanager
from uuid import uuid4

from anyio import CapacityLimiter
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from docintel import __version__
from docintel.api.documents import router as document_router
from docintel.api.models import Capabilities, ErrorEnvelope, FixtureCatalog, Health, SchemaInfo
from docintel.config import ROOT, Settings
from docintel.domain.models import FIELD_IDS, SCHEMA_VERSION, FixtureView
from docintel.services.documents import DocumentService, ProductError
from docintel.services.fixtures import FixtureService
from docintel.services.notifications import LoggingConfirmationNotifier
from docintel.services.worker import LocalInferenceWorker


def create_app(settings: Settings | None = None, *, start_worker: bool = True) -> FastAPI:
    config = settings or Settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        application.state.documents = DocumentService(config)
        application.state.confirmation_notifier = LoggingConfirmationNotifier()
        application.state.upload_limiter = CapacityLimiter(config.max_concurrent_uploads)
        application.state.upload_tasks = set()
        worker = None
        if start_worker and config.provider_mode == "tesseract":
            worker = LocalInferenceWorker(application.state.documents)
            worker.start()
        yield
        # A complete upload may still be committing after its client went away.
        if application.state.upload_tasks:
            await asyncio.gather(*application.state.upload_tasks, return_exceptions=True)
        if worker:
            worker.close()

    application = FastAPI(
        title="AI-02 Document Intelligence",
        version=__version__,
        lifespan=lifespan,
        responses={
            409: {"model": ErrorEnvelope},
            413: {"model": ErrorEnvelope},
            415: {"model": ErrorEnvelope},
            429: {"model": ErrorEnvelope},
            404: {"model": ErrorEnvelope},
            422: {"model": ErrorEnvelope},
            503: {"model": ErrorEnvelope},
            500: {"model": ErrorEnvelope},
        },
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=["Content-Type", "Idempotency-Key"],
    )

    @application.middleware("http")
    async def request_identifier(request: Request, call_next):
        request.state.request_id = str(uuid4())
        if request.method in {"POST", "PUT", "DELETE", "PATCH"}:
            origin = request.headers.get("origin")
            if origin and origin not in config.cors_origins:
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": {
                            "code": "ORIGIN_NOT_ALLOWED",
                            "message": "Nguồn yêu cầu không được phép.",
                            "request_id": request.state.request_id,
                        }
                    },
                    headers={"X-Request-ID": request.state.request_id},
                )
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @application.exception_handler(ProductError)
    async def product_error(request: Request, exc: ProductError):
        return JSONResponse(
            status_code=exc.status,
            headers=exc.headers,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "request_id": request.state.request_id,
                }
            },
        )

    @application.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException):
        detail = (
            exc.detail
            if isinstance(exc.detail, dict)
            else {
                "code": "HTTP_ERROR",
                "message": "Không tìm thấy tài nguyên hoặc thao tác không hợp lệ.",
            }
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {**detail, "request_id": request.state.request_id}},
        )

    @application.exception_handler(RequestValidationError)
    async def input_error(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": "Đầu vào không đúng contract.",
                    "request_id": request.state.request_id,
                }
            },
        )

    @application.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", str(uuid4()))
        return JSONResponse(
            status_code=500,
            headers={"X-Request-ID": request_id},
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Không thể đọc dữ liệu nền. Vui lòng thử lại.",
                    "request_id": request_id,
                }
            },
        )

    @application.get("/api/v1/health", response_model=Health)
    def health():
        return Health(app_version=__version__)

    @application.get("/api/v1/capabilities", response_model=Capabilities)
    def capabilities():
        ready = False
        if config.provider_mode == "tesseract":
            from document_pipeline.errors import PipelineError
            from document_pipeline.tesseract import probe

            try:
                probe(config.tesseract_executable, config.tessdata_dir)
                ready = True
            except PipelineError:
                pass
        return Capabilities(
            provider_mode=config.provider_mode,
            ocr_ready=ready,
            max_upload_bytes=config.max_upload_bytes,
            supported_schemas=["don_de_nghi@1.0.0", "hoa_don@1.0.0"],
            features={
                "normalization": "implemented",
                "validation": "implemented",
                "fixture_catalog": "fixture"
                if config.provider_mode == "fixture"
                else "unavailable",
                "ocr": "implemented" if ready else "unavailable",
                "extraction": "implemented",
                "upload": "implemented",
                "review": "implemented",
                "persistence": "implemented",
                "export": "implemented",
            },
        )

    @application.get("/api/v1/schemas", response_model=list[SchemaInfo])
    def schemas():
        return [
            SchemaInfo(
                document_type="don_de_nghi",
                schema_version=SCHEMA_VERSION,
                required_fields=list(FIELD_IDS),
            )
        ]

    def service() -> FixtureService:
        if config.provider_mode != "fixture":
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "PROVIDER_UNAVAILABLE",
                    "message": "Chế độ mẫu giả lập chưa được bật.",
                },
            )
        return FixtureService(ROOT, enabled=True)

    def check_sample(sample_id: str) -> FixtureService:
        fixture_service = service()
        if sample_id not in fixture_service.catalog():
            raise HTTPException(
                status_code=404,
                detail={"code": "SAMPLE_NOT_FOUND", "message": "Không tìm thấy mẫu minh họa."},
            )
        return fixture_service

    @application.get("/api/v1/fixtures", response_model=FixtureCatalog)
    def fixture_catalog():
        return FixtureCatalog(sample_ids=service().catalog())

    @application.get("/api/v1/fixtures/{sample_id}", response_model=FixtureView)
    def fixture_view(sample_id: str):
        return check_sample(sample_id).view(sample_id)

    @application.get("/api/v1/fixtures/{sample_id}/image", response_class=FileResponse)
    def fixture_image(sample_id: str):
        return FileResponse(check_sample(sample_id).image_path(sample_id), media_type="image/png")

    application.include_router(document_router)
    return application


app = create_app()
