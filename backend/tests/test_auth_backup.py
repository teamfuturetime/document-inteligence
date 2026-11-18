"""Legacy migration/adoption/restore preserves authoritative content on real SQLite."""

import shutil
import sqlite3
from importlib.resources import files

import pytest
from fastapi.testclient import TestClient
from test_product import image_bytes, inference

from docintel.api.app import create_app
from docintel.config import ROOT, Settings
from docintel.services.documents import DocumentService


def test_legacy_migrate_adopt_backup_restore_keeps_prediction_review_and_owner(
    tmp_path, monkeypatch
):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    import backup_runtime
    import manage_auth

    monkeypatch.setattr(DocumentService, "ensure_ready", lambda self: {})
    source = tmp_path / "source"
    settings = Settings(_env_file=None, runtime_dir=source, provider_mode="tesseract")
    with TestClient(create_app(settings, start_worker=False)) as api:
        service = api.app.state.documents
        monkeypatch.setattr(service.pipeline, "run", inference)
        created = api.post(
            "/api/v1/documents?document_type=hoa_don&data_origin=synthetic",
            content=image_bytes(),
        ).json()
        assert service.process_next()
        document_id, run_id = created["document_id"], created["run"]["run_id"]
        path = "/api/v1/documents/" + document_id
        assert (
            api.post(path + "/confirm", json={"run_id": run_id, "expected_revision": 1}).status_code
            == 200
        )
        before = api.get(path).json()
        params = {"run_id": run_id, "revision": 1}
        exported = api.get(path + "/export", params=params).json()
        history = api.get(path + "/history").json()

    # Build a genuine schema-1 snapshot using the historical schema and persisted rows.
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    shutil.copytree(source / "documents", legacy / "documents")
    with sqlite3.connect(legacy / "documents.sqlite3") as old:
        old.executescript(
            files("docintel").joinpath("repositories/migrations/001_documents.sql").read_text()
        )
        old.execute("INSERT INTO schema_migrations VALUES(1,'historical')")
        old.execute("ATTACH DATABASE ? AS original", (str(source / "documents.sqlite3"),))
        for table in ("documents", "runs", "revisions", "events"):
            columns = ",".join(row[1] for row in old.execute(f"PRAGMA table_info({table})"))
            old.execute(f"INSERT INTO {table}({columns}) SELECT {columns} FROM original.{table}")

    legacy_settings = settings.model_copy(update={"runtime_dir": legacy})
    with pytest.raises(RuntimeError, match="offline backup"):
        DocumentService(legacy_settings)
    manage_auth.migrate_runtime(legacy, tmp_path / "schema1-backup")
    manage_auth.manage_user(legacy, "create-user", "alpha", "synthetic-password-123")
    manage_auth.manage_user(legacy, "create-user", "beta", "synthetic-password-123")
    session_settings = legacy_settings.model_copy(update={"auth_mode": "session"})
    with TestClient(
        create_app(session_settings, start_worker=False), base_url="https://testserver"
    ) as api:
        login = api.post(
            "/api/v1/auth/login",
            json={"username": "alpha", "password": "synthetic-password-123"},
            headers={"Origin": "http://127.0.0.1:5173", "X-Requested-With": "docintel"},
        )
        assert login.status_code == 200
        assert api.get(path).status_code == 404  # No first-login adoption.
    manage_auth.adopt_local(legacy, "alpha", tmp_path / "adoption-backup")
    backup_runtime.backup(legacy, tmp_path / "owner-backup")
    restored = tmp_path / "restored"
    backup_runtime.restore(tmp_path / "owner-backup", restored)
    restored_settings = session_settings.model_copy(update={"runtime_dir": restored})
    with TestClient(
        create_app(restored_settings, start_worker=False), base_url="https://testserver"
    ) as api:
        headers = {"Origin": "http://127.0.0.1:5173", "X-Requested-With": "docintel"}
        assert (
            api.post(
                "/api/v1/auth/login",
                json={"username": "alpha", "password": "synthetic-password-123"},
                headers=headers,
            ).status_code
            == 200
        )
        assert api.get(path).json() == before
        assert api.get(path + "/history").json() == history
        after = api.get(path + "/export", params=params).json()
        exported.pop("exported_at")
        after.pop("exported_at")
        assert after == exported
        assert (restored / "documents" / (document_id + ".source")).read_bytes() == (
            source / "documents" / (document_id + ".source")
        ).read_bytes()
        assert (
            api.post(
                "/api/v1/auth/login",
                json={"username": "beta", "password": "synthetic-password-123"},
                headers=headers,
            ).status_code
            == 200
        )
        assert api.get(path).status_code == 404
        assert api.get(path + "/export", params=params).status_code == 404
        assert api.get("/api/v1/documents").json()["total"] == 0
    # The schema-1 backup remains available for rollback into the old binary.
    with sqlite3.connect(tmp_path / "schema1-backup/documents.sqlite3") as original:
        assert original.execute("SELECT max(version) FROM schema_migrations").fetchone()[0] == 1
