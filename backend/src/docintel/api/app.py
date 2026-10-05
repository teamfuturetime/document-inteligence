from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from docintel import __version__
from docintel.api.models import Capabilities, ErrorEnvelope, FixtureCatalog, Health, SchemaInfo
from docintel.config import ROOT, Settings
from docintel.domain.models import FIELD_IDS, SCHEMA_VERSION, FixtureView
from docintel.services.fixtures import FixtureService


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or Settings()
    application = FastAPI(
        title="AI-02 Document Intelligence Foundation",
        version=__version__,
        responses={
            404: {"model": ErrorEnvelope},
            422: {"model": ErrorEnvelope},
            503: {"model": ErrorEnvelope},
            500: {"model": ErrorEnvelope},
        },
    )
    application.add_middleware(
        CORSMiddleware, allow_origins=config.cors_origins, allow_methods=["GET"]
    )

    @application.middleware("http")
    async def request_identifier(request: Request, call_next):
        request.state.request_id = str(uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

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
        return Capabilities(
            provider_mode=config.provider_mode,
            supported_schemas=["don_de_nghi@1.0.0"],
            features={
                "normalization": "implemented",
                "validation": "implemented",
                "fixture_catalog": "fixture"
                if config.provider_mode == "fixture"
                else "unavailable",
                "ocr": "planned",
                "extraction": "planned",
                "upload": "planned",
                "review": "planned",
                "persistence": "planned",
                "export": "planned",
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

    return application


app = create_app()
