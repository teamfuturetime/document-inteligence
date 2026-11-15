import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from document_pipeline.config import PipelineConfig
from document_pipeline.errors import PipelineError
from document_pipeline.preprocessing import prepare_image
from document_pipeline.service import DocumentPipeline
from document_pipeline.tesseract import probe

from docintel.adapters.pipeline import to_domain
from docintel.config import Settings
from docintel.domain.documents import (
    DEFINITIONS,
    DocumentDetail,
    DocumentHistory,
    DocumentList,
    DocumentSummary,
    FinalInvoiceData,
    HistoryEvent,
    ProductExportArtifact,
    ProductInsights,
    ProductReviewedField,
    ProductRevision,
    ProductRun,
    ReviewRequest,
    RevisionRequest,
    effective_values,
    validate_values,
)
from docintel.domain.models import FinalApplicationData, Provenance
from docintel.repositories.sqlite import DocumentRepository, now
from docintel.services.notifications import DocumentConfirmed
from docintel.storage.local import LocalDocumentStorage


class ProductError(Exception):
    def __init__(
        self, status: int, code: str, message: str, *, headers: dict[str, str] | None = None
    ):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message
        self.headers = headers


def require(row):
    if row is None:
        raise ProductError(404, "DOCUMENT_NOT_FOUND", "Không tìm thấy tài liệu hoặc lần xử lý.")
    return row


def event(connection, document_id, run_id, revision, action, changes):
    connection.execute(
        "INSERT INTO events(document_id,run_id,revision,action,occurred_at,changes_json) "
        "VALUES(?,?,?,?,?,?)",
        (document_id, run_id, revision, action, now(), json.dumps(changes)),
    )


def machine_run(row) -> ProductRun:
    content = json.loads(row["result_json"]) if row["result_json"] else {}
    return ProductRun.model_validate_json(
        json.dumps(
            {
                "run_id": row["run_id"],
                "status": row["status"],
                "created_at": row["created_at"],
                "finished_at": row["finished_at"],
                "error_code": row["error_code"],
                **content,
            }
        )
    )


def revision_view(row, run: ProductRun, document_type: str) -> ProductRevision | None:
    if row is None:
        return None
    fields = {
        key: ProductReviewedField.model_validate(value)
        for key, value in json.loads(row["fields_json"]).items()
    }
    data = effective_values(document_type, run.fields, fields)
    return ProductRevision(
        revision=row["revision"],
        review_status=row["review_status"],
        fields=fields,
        effective_data=data,
        validation_issues=validate_values(document_type, data),
        saved_at=datetime.fromisoformat(row["saved_at"]),
    )


def summary(row) -> DocumentSummary:
    return DocumentSummary.model_validate_json(
        json.dumps({key: row[key] for key in DocumentSummary.model_fields})
    )


SUMMARY_SELECT = """
SELECT d.*,r.status,(SELECT review_status FROM revisions v WHERE v.run_id=d.latest_run_id
ORDER BY revision DESC LIMIT 1) review_status
FROM documents d JOIN runs r ON r.run_id=d.latest_run_id
"""


@dataclass(frozen=True)
class ConfirmationResult:
    detail: DocumentDetail
    notice: DocumentConfirmed | None


class DocumentService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.repository = DocumentRepository(settings.runtime_dir / "documents.sqlite3")
        self.repository.initialize()
        self.storage = LocalDocumentStorage(settings.runtime_dir / "documents")
        self.pipeline_config = PipelineConfig(
            max_upload_bytes=settings.max_upload_bytes,
            max_image_pixels=settings.max_image_pixels,
            timeout_seconds=float(settings.provider_timeout_seconds),
        )
        self.pipeline = DocumentPipeline(
            settings.tessdata_dir, settings.tesseract_executable, self.pipeline_config
        )

    def ensure_ready(self):
        if self.settings.provider_mode != "tesseract":
            raise ProductError(
                503, "PROVIDER_UNAVAILABLE", "Cần bật provider tesseract cho OCR thật."
            )
        try:
            return probe(self.settings.tesseract_executable, self.settings.tessdata_dir)
        except PipelineError as exc:
            raise ProductError(503, exc.code, str(exc)) from exc

    def list_documents(
        self, limit: int, offset: int, document_type: str | None = None, status: str | None = None
    ) -> DocumentList:
        conditions, params = [], []
        if document_type:
            conditions.append("d.document_type=?")
            params.append(document_type)
        if status:
            conditions.append("r.status=?")
            params.append(status)
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        with self.repository.transaction() as connection:
            total = connection.execute(
                "SELECT count(*) FROM (" + SUMMARY_SELECT + where + ")", params
            ).fetchone()[0]
            rows = connection.execute(
                SUMMARY_SELECT + where + " ORDER BY d.created_at DESC LIMIT ? OFFSET ?",
                [*params, limit, offset],
            ).fetchall()
        return DocumentList(
            items=[summary(row) for row in rows], total=total, limit=limit, offset=offset
        )

    def detail(self, document_id: str, run_id: str | None = None) -> DocumentDetail:
        with self.repository.transaction() as connection:
            document = require(
                connection.execute(
                    SUMMARY_SELECT + " WHERE d.document_id=?", (document_id,)
                ).fetchone()
            )
            selected = run_id or document["latest_run_id"]
            run = machine_run(
                require(
                    connection.execute(
                        "SELECT * FROM runs WHERE document_id=? AND run_id=?",
                        (document_id, selected),
                    ).fetchone()
                )
            )
            revision = connection.execute(
                "SELECT * FROM revisions WHERE run_id=? ORDER BY revision DESC LIMIT 1", (selected,)
            ).fetchone()
        return DocumentDetail(
            **summary(document).model_dump(),
            image_url=f"/api/v1/documents/{document_id}/image",
            definitions=DEFINITIONS[document["document_type"]],
            run=run,
            review=revision_view(revision, run, document["document_type"]),
            is_latest_run=selected == document["latest_run_id"],
        )

    def upload(
        self,
        data: bytes,
        document_type: str,
        data_origin: str,
        filename: str,
        idempotency_key: str | None,
    ) -> DocumentDetail:
        digest = hashlib.sha256(data).hexdigest()
        with self.repository.transaction() as connection:
            existing = (
                connection.execute(
                    "SELECT * FROM documents WHERE idempotency_key=?", (idempotency_key,)
                ).fetchone()
                if idempotency_key
                else None
            )
        if existing:
            if (existing["input_sha256"], existing["document_type"], existing["data_origin"]) != (
                digest,
                document_type,
                data_origin,
            ):
                raise ProductError(409, "IDEMPOTENCY_CONFLICT", "Khóa đã dùng cho tài liệu khác.")
            return self.detail(existing["document_id"])
        self.ensure_ready()
        try:
            page = prepare_image(
                data,
                self.pipeline_config.model_copy(
                    update={
                        "timeout_seconds": min(5.0, self.pipeline_config.timeout_seconds),
                    }
                ),
            )
        except PipelineError as exc:
            status = 413 if exc.code in ("FILE_TOO_LARGE", "IMAGE_TOO_LARGE") else 415
            raise ProductError(status, exc.code, str(exc)) from exc
        document_id, run_id, created = uuid4().hex, uuid4().hex, now()
        try:
            self.storage.write(document_id, "source", data)
            self.storage.write(document_id, "preview", page.png)
            with self.repository.transaction(write=True) as connection:
                # Serialize the retry decision with admission, before capacity rejection.
                replay = (
                    connection.execute(
                        "SELECT * FROM documents WHERE idempotency_key=?", (idempotency_key,)
                    ).fetchone()
                    if idempotency_key
                    else None
                )
                if replay:
                    if (replay["input_sha256"], replay["document_type"], replay["data_origin"]) != (
                        digest,
                        document_type,
                        data_origin,
                    ):
                        raise ProductError(
                            409, "IDEMPOTENCY_CONFLICT", "Khóa đã dùng cho tài liệu khác."
                        )
                    self.storage.discard(document_id)
                    return self.detail(replay["document_id"])
                self.check_capacity(connection)
                connection.execute(
                    "INSERT INTO documents VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (
                        document_id,
                        document_type,
                        filename,
                        data_origin,
                        digest,
                        page.width,
                        page.height,
                        created,
                        run_id,
                        idempotency_key,
                    ),
                )
                connection.execute(
                    "INSERT INTO runs(run_id,document_id,status,created_at) VALUES(?,?,'queued',?)",
                    (run_id, document_id, created),
                )
                event(connection, document_id, run_id, None, "uploaded", {"input_sha256": digest})
        except sqlite3.IntegrityError:
            self.storage.discard(document_id)
            # A concurrent request with the same key may have won the transaction.
            if idempotency_key:
                return self.upload(data, document_type, data_origin, filename, idempotency_key)
            raise
        except BaseException:
            self.storage.discard(document_id)
            raise
        return self.detail(document_id)

    def check_capacity(self, connection):
        pending = connection.execute(
            "SELECT count(*) FROM runs WHERE status IN ('queued','running')"
        ).fetchone()[0]
        if pending >= self.settings.max_pending_runs:
            raise ProductError(429, "QUEUE_FULL", "Hàng đợi đã đầy. Vui lòng thử lại sau.")

    def reprocess(self, document_id: str, expected_run_id: str) -> DocumentDetail:
        self.ensure_ready()
        with self.repository.transaction(write=True) as connection:
            document = require(
                connection.execute(
                    "SELECT * FROM documents WHERE document_id=?", (document_id,)
                ).fetchone()
            )
            run = require(
                connection.execute(
                    "SELECT * FROM runs WHERE run_id=?", (document["latest_run_id"],)
                ).fetchone()
            )
            if expected_run_id != run["run_id"] or run["status"] in ("queued", "running"):
                raise ProductError(409, "RUN_CONFLICT", "Lần xử lý đã đổi hoặc còn đang chạy.")
            self.check_capacity(connection)
            run_id = uuid4().hex
            connection.execute(
                "INSERT INTO runs(run_id,document_id,status,created_at) VALUES(?,?,'queued',?)",
                (run_id, document_id, now()),
            )
            connection.execute(
                "UPDATE documents SET latest_run_id=? WHERE document_id=?", (run_id, document_id)
            )
            event(
                connection,
                document_id,
                run_id,
                None,
                "reprocess_requested",
                {"previous_run_id": expected_run_id},
            )
        return self.detail(document_id)

    def checked_revision(self, connection, document_id: str, request: RevisionRequest):
        document = require(
            connection.execute(
                "SELECT * FROM documents WHERE document_id=?", (document_id,)
            ).fetchone()
        )
        if document["latest_run_id"] != request.run_id:
            raise ProductError(409, "STALE_RUN", "Đang xem lần xử lý cũ; hãy tải bản mới.")
        run = machine_run(
            require(
                connection.execute(
                    "SELECT * FROM runs WHERE run_id=?", (request.run_id,)
                ).fetchone()
            )
        )
        revision = connection.execute(
            "SELECT * FROM revisions WHERE run_id=? ORDER BY revision DESC LIMIT 1",
            (request.run_id,),
        ).fetchone()
        if run.status != "succeeded" or not revision:
            raise ProductError(409, "RUN_NOT_READY", "Lần xử lý chưa có kết quả để review.")
        if revision["revision"] != request.expected_revision:
            raise ProductError(
                409, "REVISION_CONFLICT", "Bản đã thay đổi. Hãy đối chiếu trước khi lưu."
            )
        return document, run, revision

    def save_review(self, document_id: str, request: ReviewRequest) -> DocumentDetail:
        with self.repository.transaction(write=True) as connection:
            document, run, row = self.checked_revision(
                connection,
                document_id,
                RevisionRequest(
                    run_id=request.run_id,
                    expected_revision=request.expected_revision,
                ),
            )
            allowed = {field.field_id for field in DEFINITIONS[document["document_type"]]}
            if set(request.fields) - allowed:
                raise ProductError(422, "INVALID_FIELD", "Trường không thuộc schema tài liệu.")
            previous = json.loads(row["fields_json"])
            fields = {
                **previous,
                **{key: field.model_dump() for key, field in request.fields.items()},
            }
            number = row["revision"] + 1
            connection.execute(
                "INSERT INTO revisions VALUES(?,?,'draft',?,?)",
                (run.run_id, number, json.dumps(fields), now()),
            )
            event(
                connection,
                document_id,
                run.run_id,
                number,
                "review_saved",
                {
                    key: {"old": previous[key], "new": value}
                    for key, value in fields.items()
                    if previous[key] != value
                },
            )
        return self.detail(document_id)

    def confirm(self, document_id: str, request: RevisionRequest) -> DocumentDetail:
        # Keep the synchronous business service API; delivery belongs to the HTTP adapter.
        return self.confirm_with_notice(document_id, request).detail

    def confirm_with_notice(self, document_id: str, request: RevisionRequest) -> ConfirmationResult:
        notice = None
        with self.repository.transaction(write=True) as connection:
            document, run, row = self.checked_revision(connection, document_id, request)
            review = revision_view(row, run, document["document_type"])
            if review.validation_issues:
                raise ProductError(
                    422, "VALIDATION_FAILED", "Cần sửa các trường lỗi trước xác nhận."
                )
            self.final_data(document["document_type"], review.effective_data)
            if row["review_status"] != "confirmed":
                connection.execute(
                    "UPDATE revisions SET review_status='confirmed' WHERE run_id=? AND revision=?",
                    (run.run_id, request.expected_revision),
                )
                event(
                    connection, document_id, run.run_id, request.expected_revision, "confirmed", {}
                )
                notice = DocumentConfirmed(document_id, run.run_id, request.expected_revision)
        # Returning a receipt is only possible after the transaction context committed.
        return ConfirmationResult(self.detail(document_id), notice)

    @staticmethod
    def final_data(document_type: str, values: dict):
        model = FinalInvoiceData if document_type == "hoa_don" else FinalApplicationData
        return model.model_validate(values)

    def export(self, document_id: str, request: RevisionRequest) -> ProductExportArtifact:
        with self.repository.transaction(write=True) as connection:
            document, run, row = self.checked_revision(connection, document_id, request)
            review = revision_view(row, run, document["document_type"])
            if review.review_status != "confirmed":
                raise ProductError(409, "NOT_CONFIRMED", "Cần xác nhận bản đã lưu trước khi xuất.")
            if review.validation_issues:
                raise ProductError(422, "VALIDATION_FAILED", "Bản lưu không đạt validation.")
            artifact = ProductExportArtifact(
                document_type=document["document_type"],
                document_id=document_id,
                run_id=run.run_id,
                revision=review.revision,
                data=self.final_data(document["document_type"], review.effective_data),
                provenance=Provenance(
                    data_origin=document["data_origin"], prediction_source="model"
                ),
                exported_at=datetime.fromisoformat(now()),
            )
            event(connection, document_id, run.run_id, review.revision, "exported", {})
        return artifact

    def history(self, document_id: str) -> DocumentHistory:
        with self.repository.transaction() as connection:
            require(
                connection.execute(
                    "SELECT 1 FROM documents WHERE document_id=?", (document_id,)
                ).fetchone()
            )
            runs = connection.execute(
                "SELECT * FROM runs WHERE document_id=? ORDER BY created_at DESC", (document_id,)
            ).fetchall()
            rows = connection.execute(
                "SELECT * FROM events WHERE document_id=? ORDER BY event_id DESC", (document_id,)
            ).fetchall()
        return DocumentHistory(
            runs=[machine_run(row) for row in runs],
            events=[
                HistoryEvent(
                    run_id=row["run_id"],
                    revision=row["revision"],
                    action=row["action"],
                    occurred_at=datetime.fromisoformat(row["occurred_at"]),
                    changes=json.loads(row["changes_json"]),
                )
                for row in rows
            ],
        )

    def insights(self) -> ProductInsights:
        reviewed = corrected = 0
        with self.repository.transaction() as connection:
            count = connection.execute("SELECT count(*) FROM documents").fetchone()[0]
            completed = connection.execute(
                "SELECT count(*) FROM runs WHERE status='succeeded'"
            ).fetchone()[0]
            failed = connection.execute(
                "SELECT count(*) FROM runs WHERE status IN ('failed','unavailable')"
            ).fetchone()[0]
        documents = self.list_documents(100, 0)
        # Aggregate all documents in bounded pages, not only the first screen.
        confirmed = 0
        for offset in range(0, documents.total, 100):
            for item in self.list_documents(100, offset).items:
                detail = self.detail(item.document_id)
                if detail.review:
                    confirmed += detail.review.review_status == "confirmed"
                    machine = {
                        field.field_id: field.normalized_value for field in detail.run.fields
                    }
                    for key, value in detail.review.fields.items():
                        if value.is_reviewed:
                            reviewed += 1
                            corrected += detail.review.effective_data[key] != machine.get(key)
        return ProductInsights(
            documents=count,
            completed_runs=completed,
            failed_runs=failed,
            confirmed_documents=confirmed,
            reviewed_fields=reviewed,
            corrected_fields=corrected,
        )

    def recover_interrupted(self):
        with self.repository.transaction(write=True) as connection:
            interrupted = connection.execute("SELECT * FROM runs WHERE status='running'").fetchall()
            for row in interrupted:
                connection.execute(
                    "UPDATE runs SET status='failed',error_code='PROCESSING_INTERRUPTED',"
                    "finished_at=? WHERE run_id=?",
                    (now(), row["run_id"]),
                )
                event(connection, row["document_id"], row["run_id"], None, "interrupted", {})

    def process_next(self) -> bool:
        with self.repository.transaction(write=True) as connection:
            row = connection.execute(
                "SELECT r.*,d.document_type,d.input_sha256 FROM runs r "
                "JOIN documents d USING(document_id) "
                "WHERE r.status='queued' ORDER BY r.created_at LIMIT 1"
            ).fetchone()
            if row is None:
                return False
            connection.execute("UPDATE runs SET status='running' WHERE run_id=?", (row["run_id"],))
        try:
            with self.storage.path(row["document_id"], "source").open("rb") as stream:
                data = stream.read(self.settings.max_upload_bytes + 1)
            if hashlib.sha256(data).hexdigest() != row["input_sha256"]:
                raise PipelineError("INPUT_CHANGED", "Dữ liệu nguồn không khớp checksum đã lưu.")
            result = to_domain(self.pipeline.run(data, row["document_type"]))
            with self.repository.transaction(write=True) as connection:
                connection.execute(
                    "UPDATE runs SET status='succeeded',finished_at=?,result_json=? WHERE run_id=?",
                    (now(), json.dumps(result), row["run_id"]),
                )
                fields = {
                    definition.field_id: {"is_reviewed": False, "reviewed_value": None}
                    for definition in DEFINITIONS[row["document_type"]]
                }
                connection.execute(
                    "INSERT INTO revisions VALUES(?,1,'draft',?,?)",
                    (row["run_id"], json.dumps(fields), now()),
                )
                event(connection, row["document_id"], row["run_id"], 1, "processed", {})
        except Exception as exc:
            code = exc.code if isinstance(exc, PipelineError) else "PROCESSING_FAILED"
            status = (
                "unavailable"
                if code in ("PROVIDER_UNAVAILABLE", "MODEL_HASH_MISMATCH")
                else "failed"
            )
            with self.repository.transaction(write=True) as connection:
                connection.execute(
                    "UPDATE runs SET status=?,finished_at=?,error_code=? WHERE run_id=?",
                    (status, now(), code, row["run_id"]),
                )
                event(
                    connection,
                    row["document_id"],
                    row["run_id"],
                    None,
                    "processing_failed",
                    {"error_code": code},
                )
        return True

    def image_path(self, document_id: str) -> Path:
        self.detail(document_id)
        path = self.storage.path(document_id, "preview")
        if not path.is_file():
            raise ProductError(404, "IMAGE_UNAVAILABLE", "Không tìm thấy ảnh nguồn.")
        return path
