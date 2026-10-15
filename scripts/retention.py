"""Delete expired metadata and local files; run daily after a database backup."""

from datetime import datetime, timezone

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models import Document
from app.services.storage import LocalStorage


def purge_expired() -> int:
    storage = LocalStorage(get_settings().storage_dir)
    with SessionLocal() as db:
        documents = list(db.scalars(select(Document).where(Document.expires_at < datetime.now(timezone.utc))))
        for document in documents:
            path = storage.resolve(document.stored_name)
            if path.is_file():
                path.unlink()
            db.delete(document)
        db.commit()
        return len(documents)


if __name__ == "__main__":
    print(f"purged={purge_expired()}")
