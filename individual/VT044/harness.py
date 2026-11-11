"""Executable contract harness; NOT mounted in app.main or production auth.

The sidecar demonstrates the future ownership/tombstone contract against the
real Document/Extraction models. Demo tokens must never be used in production.
"""
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import Boolean, ForeignKey, String, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.models import Base, Document, Extraction
from app.repositories.documents import DocumentRepository


class Lifecycle(Base):
    __tablename__ = "vt044_lifecycle"
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(80), index=True)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)


def missing():
    return HTTPException(404, "Không tìm thấy tài liệu")


class LifecycleService:
    def __init__(self, engine, storage, *, clock=lambda: datetime.now(timezone.utc)):
        self.engine, self.storage, self.clock = engine, storage, clock

    def _owned(self, db, actor, document_id, *, active_only=True):
        state = db.scalar(select(Lifecycle).where(
            Lifecycle.document_id == document_id, Lifecycle.owner_id == actor))
        if state is None:
            raise missing()
        doc = DocumentRepository(db).get(document_id)
        if doc is None or doc.expires_at.replace(tzinfo=timezone.utc) <= self.clock():
            raise missing()
        if active_only and state.deleted:
            raise missing()
        return doc, state

    def transition(self, actor, document_id, target):
        with Session(self.engine) as db:
            try:
                # A no-op UPDATE locks the ownership row before reading state.
                # SQLite serializes writers; PostgreSQL locks this row.
                locked = db.execute(update(Lifecycle).where(
                    Lifecycle.document_id == document_id,
                    Lifecycle.owner_id == actor,
                ).values(deleted=Lifecycle.deleted))
                if locked.rowcount != 1:
                    raise missing()
                # Coordinate with processing's UPDATE on the real document row.
                db.execute(update(Document).where(Document.id == document_id)
                           .values(status=Document.status))
                doc, state = self._owned(db, actor, document_id, active_only=False)
                if doc.status == "processing":
                    raise HTTPException(409, "Tài liệu đang được xử lý")
                if state.deleted != target:
                    state.deleted = target
                db.commit()
                return {"id": document_id, "deleted": target}
            except SQLAlchemyError as error:
                db.rollback()
                raise HTTPException(503, "Cơ sở dữ liệu không khả dụng") from error

    def read(self, actor, document_id):
        with Session(self.engine) as db:
            doc, _ = self._owned(db, actor, document_id)
            return {"id": doc.id, "status": doc.status}

    def content(self, actor, document_id):
        with Session(self.engine) as db:
            doc, _ = self._owned(db, actor, document_id)
            path = self.storage.resolve(doc.stored_name)
            if not path.is_file():
                raise missing()
            return FileResponse(path, media_type=doc.mime_type)

    def extraction(self, actor, document_id):
        with Session(self.engine) as db:
            self._owned(db, actor, document_id)
            extraction = db.scalar(select(Extraction).where(
                Extraction.document_id == document_id
            ).order_by(Extraction.updated_at.desc(), Extraction.id.desc()).limit(1))
            if extraction is None:
                raise missing()
            return extraction.data

    def listing(self, actor):
        with Session(self.engine) as db:
            return {"ids": list(db.scalars(select(Document.id).join(Lifecycle).where(
                Lifecycle.owner_id == actor, Lifecycle.deleted.is_(False),
                Document.expires_at > self.clock(),
            ).order_by(Document.id)))}


def create_app(service, tokens):
    app = FastAPI(title="VT-044 isolated contract harness")
    identities = dict(tokens)

    def actor(x_api_key: str | None = Header(None)):
        identity = identities.get(x_api_key)
        if identity is None:
            raise HTTPException(401, "Không có quyền truy cập")
        return identity

    @app.get("/documents")
    def listing(user=Depends(actor)):
        return service.listing(user)

    @app.get("/documents/{document_id}")
    def read(document_id: str, user=Depends(actor)):
        return service.read(user, document_id)

    @app.get("/documents/{document_id}/content")
    def content(document_id: str, user=Depends(actor)):
        return service.content(user, document_id)

    @app.get("/documents/{document_id}/extraction")
    def extraction(document_id: str, user=Depends(actor)):
        return service.extraction(user, document_id)

    @app.delete("/documents/{document_id}")
    def delete(document_id: str, user=Depends(actor)):
        return service.transition(user, document_id, True)

    @app.post("/documents/{document_id}/restore")
    def restore(document_id: str, user=Depends(actor)):
        return service.transition(user, document_id, False)

    return app
