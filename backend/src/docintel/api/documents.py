import re
from typing import Annotated, Literal

from fastapi import APIRouter, Header, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from starlette.concurrency import run_in_threadpool

from docintel.domain.documents import (
    DEFINITIONS,
    DocumentDetail,
    DocumentHistory,
    DocumentList,
    DocumentType,
    ProductExportArtifact,
    ProductInsights,
    ProductSchema,
    ReprocessRequest,
    ReviewRequest,
    RevisionRequest,
)
from docintel.services.documents import DocumentService, ProductError
from docintel.services.notifications import notify_safely

router = APIRouter(prefix="/api/v1", tags=["product"])


def service(request: Request) -> DocumentService:
    return request.app.state.documents


@router.get("/document-schemas", response_model=list[ProductSchema])
def document_schemas():
    return [
        ProductSchema(document_type=kind, fields=fields) for kind, fields in DEFINITIONS.items()
    ]


@router.get("/documents", response_model=DocumentList)
def documents(
    request: Request,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    document_type: DocumentType | None = None,
    status: Literal["queued", "running", "succeeded", "failed", "unavailable"] | None = None,
):
    return service(request).list_documents(limit, offset, document_type, status)


@router.post("/documents", response_model=DocumentDetail, status_code=202)
async def upload_document(
    request: Request,
    document_type: DocumentType,
    data_origin: Literal["synthetic", "sample"],
    filename: Annotated[str, Query(min_length=1, max_length=200)] = "document.png",
    idempotency_key: Annotated[str | None, Header(pattern=r"^[A-Za-z0-9_-]{1,96}$")] = None,
):
    maximum = service(request).settings.max_upload_bytes
    data = bytearray()
    async for chunk in request.stream():
        if len(data) + len(chunk) > maximum:
            raise ProductError(413, "FILE_TOO_LARGE", "Tài liệu vượt giới hạn kích thước.")
        data.extend(chunk)
    filename = re.split(r"[/\\]", filename)[-1]
    filename = "".join(character for character in filename if character.isprintable()) or "document"
    return await run_in_threadpool(
        service(request).upload, bytes(data), document_type, data_origin, filename, idempotency_key
    )


@router.get("/documents/{document_id}", response_model=DocumentDetail)
def document(request: Request, document_id: str, run_id: str | None = None):
    return service(request).detail(document_id, run_id)


@router.get("/documents/{document_id}/image", response_class=FileResponse)
def image(request: Request, document_id: str):
    return FileResponse(
        service(request).image_path(document_id),
        media_type="image/png",
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.get("/documents/{document_id}/history", response_model=DocumentHistory)
def history(request: Request, document_id: str):
    return service(request).history(document_id)


@router.post("/documents/{document_id}/runs", response_model=DocumentDetail, status_code=202)
def reprocess(request: Request, document_id: str, body: ReprocessRequest):
    return service(request).reprocess(document_id, body.expected_run_id)


@router.put("/documents/{document_id}/review", response_model=DocumentDetail)
def save_review(request: Request, document_id: str, body: ReviewRequest):
    return service(request).save_review(document_id, body)


@router.post("/documents/{document_id}/confirm", response_model=DocumentDetail)
async def confirm(request: Request, document_id: str, body: RevisionRequest):
    documents = service(request)
    result = await run_in_threadpool(documents.confirm_with_notice, document_id, body)
    if result.notice is not None and documents.settings.notification_mode != "disabled":
        await notify_safely(
            request.app.state.confirmation_notifier,
            result.notice,
            documents.settings.notification_timeout_seconds,
        )
    return result.detail


@router.get("/documents/{document_id}/export", response_model=ProductExportArtifact)
def export(request: Request, document_id: str, run_id: str, revision: Annotated[int, Query(ge=1)]):
    artifact = service(request).export(
        document_id, RevisionRequest(run_id=run_id, expected_revision=revision)
    )
    return JSONResponse(
        artifact.model_dump(mode="json"),
        headers={
            "Content-Disposition": (
                f'attachment; filename="document-{artifact.document_id}-r{revision}.json"'
            ),
            "Cache-Control": "no-store",
        },
    )


@router.get("/insights", response_model=ProductInsights)
def insights(request: Request):
    return service(request).insights()
