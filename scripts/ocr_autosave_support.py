"""Isolated SQLite environment for HTTP autosave experiments (never production data)."""
from __future__ import annotations

import os
import secrets
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))
# Set before importing app settings; the experiment always overrides get_db below.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import httpx  # noqa: E402
from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.api.dependencies import get_storage  # noqa: E402
from app.core.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Document  # noqa: E402
from app.services.storage import StorageService  # noqa: E402

RAW_OCR = "HO VA TEN: NGUYEN VAN A\nMST: 0101234567"
LOGIN = "vt043-load@example.test"
# Test-only credential, scoped to a newly created temporary SQLite database.
TEST_PASSWORD = secrets.token_urlsafe(24)


@dataclass
class HTTPEnvironment:
    application: object
    sessions: sessionmaker
    database_url: str

    def client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.application, raise_app_exceptions=False),
            base_url="http://vt043.test", timeout=30.0,
        )

    def seed_documents(self, owner_id: str, count: int) -> list[str]:
        with self.sessions() as db:
            documents = [Document(
                filename=f"vt043-{index}.pdf", content_type="application/pdf",
                file_size=20, file_path=f"vt043-{index}.pdf", owner_id=owner_id,
                status="processed", ocr_text=RAW_OCR,
            ) for index in range(count)]
            db.add_all(documents)
            db.flush()
            ids = [document.id for document in documents]
            db.commit()
            return ids


@contextmanager
def isolated_http_environment(directory: Path):
    """Each HTTP request gets its own Session against a disposable file DB.

    WAL allows concurrent readers; SQLite still serializes writers. This does
    not establish PostgreSQL isolation/performance behavior.
    """
    directory.mkdir(parents=True, exist_ok=True)
    database_url = "sqlite:///" + (directory / "autosave.sqlite3").as_posix()
    engine = create_engine(
        database_url, connect_args={"check_same_thread": False, "timeout": 20},
        pool_size=20, max_overflow=80,
    )

    @event.listens_for(engine, "connect")
    def configure_sqlite(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=20000")

    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA journal_mode=WAL")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def request_session():
        with sessions() as session:
            yield session

    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = request_session
    app.dependency_overrides[get_storage] = lambda: StorageService(str(directory / "uploads"))
    try:
        yield HTTPEnvironment(app, sessions, database_url)
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)
        engine.dispose()


async def register_owner(client: httpx.AsyncClient) -> str:
    response = await client.post("/api/v1/auth/register", json={
        "email": LOGIN, "username": "vt043-load", "password": TEST_PASSWORD,
    })
    assert response.status_code == 201, f"register HTTP {response.status_code}"
    client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    return response.json()["user"]["id"]


async def login_owner(client: httpx.AsyncClient) -> None:
    response = await client.post("/api/v1/auth/login", json={
        "login": LOGIN, "password": TEST_PASSWORD,
    })
    assert response.status_code == 200, f"login HTTP {response.status_code}"
    client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
