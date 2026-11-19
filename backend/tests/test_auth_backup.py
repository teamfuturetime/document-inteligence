"""Legacy migration/adoption/restore preserves authoritative content on real SQLite."""

import json
import os
import shutil
import sqlite3
import stat
import subprocess
import sys
from importlib.resources import files

import pytest
from fastapi.testclient import TestClient
from test_product import image_bytes, inference

from docintel.api.app import create_app
from docintel.config import ROOT, Settings
from docintel.services.documents import DocumentService


@pytest.mark.parametrize("path_mode", ["absolute", "relative", "lexical_alias", "relative_cli"])
def test_legacy_migrate_adopt_backup_restore_keeps_prediction_review_and_owner(
    tmp_path, monkeypatch, path_mode
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
    destination = tmp_path / "owner-backup"
    restored = tmp_path / "restored"
    runtime = legacy
    if path_mode in {"relative", "relative_cli"}:
        monkeypatch.chdir(tmp_path)
        runtime = runtime.relative_to(tmp_path)
        destination = destination.relative_to(tmp_path)
        restored = restored.relative_to(tmp_path)
    elif path_mode == "lexical_alias":
        destination = source / ".." / destination.name
        restored = source / ".." / restored.name
    if path_mode == "relative_cli":
        for input_path, output_path, flags in [
            (runtime, destination, []),
            (destination, restored, ["--restore"]),
        ]:
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/backup_runtime.py"),
                    str(input_path),
                    str(output_path),
                    *flags,
                ],
                env={
                    **os.environ,
                    "PYTHONPATH": os.pathsep.join(
                        str(ROOT / part) for part in ("backend/src", "pipeline/src")
                    ),
                },
                check=True,
                capture_output=True,
                text=True,
            )
    else:
        backup_runtime.backup(runtime, destination)
        backup_runtime.restore(destination, restored)
    manifest = json.loads((destination / "backup.json").read_text(encoding="utf-8"))
    assert manifest["version"] == 1
    assert "documents.sqlite3" in manifest["sha256"]
    if os.name == "posix":
        for directory in (destination, restored):
            assert stat.S_IMODE(directory.stat().st_mode) == 0o700
        assert stat.S_IMODE((destination / "documents.sqlite3").stat().st_mode) == 0o600
        for relative in manifest["sha256"]:
            assert stat.S_IMODE((restored / relative).stat().st_mode) == 0o600
    with sqlite3.connect(restored / "documents.sqlite3") as database:
        assert database.execute("SELECT max(version) FROM schema_migrations").fetchone() == (2,)
        assert database.execute(
            "SELECT documents.owner_id = users.user_id FROM documents "
            "JOIN users ON users.username = 'alpha' WHERE document_id = ?",
            (document_id,),
        ).fetchone() == (1,)
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
