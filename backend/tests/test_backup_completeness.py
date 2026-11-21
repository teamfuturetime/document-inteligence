"""Rehashed, structurally valid SQLite must still retain runtime columns and review records."""

import json
import os
import shutil
import sqlite3
import subprocess
import sys
from contextlib import closing
from importlib.resources import files

import pytest
from fastapi.testclient import TestClient
from test_backup_verify import helper as helper
from test_backup_verify import rehash, tree
from test_product import image_bytes, inference

from docintel.api.app import create_app
from docintel.config import ROOT, Settings
from docintel.services.documents import DocumentService
from docintel.storage.backup import BackupVerificationError, verify_backup


@pytest.fixture(params=[1, 2])
def confirmed_backup(request, tmp_path, monkeypatch, helper):
    runtime = tmp_path / "runtime"
    settings = Settings(_env_file=None, runtime_dir=runtime, provider_mode="fixture")
    monkeypatch.setattr(DocumentService, "ensure_ready", lambda _: {})
    with TestClient(create_app(settings, start_worker=False)) as api:
        service = api.app.state.documents
        monkeypatch.setattr(service.pipeline, "run", inference)
        uploaded = api.post(
            "/api/v1/documents?document_type=hoa_don&data_origin=synthetic",
            content=image_bytes(),
        )
        assert uploaded.status_code == 202
        document = uploaded.json()
        run_id = document["run"]["run_id"]
        path = "/api/v1/documents/" + document["document_id"]
        assert service.process_next()
        saved = api.put(
            path + "/review",
            json={"run_id": run_id, "expected_revision": 1, "fields": {}},
        )
        assert saved.status_code == 200
        assert (
            api.post(path + "/confirm", json={"run_id": run_id, "expected_revision": 2}).status_code
            == 200
        )
        expected = api.get(path).json()
        exported = api.get(path + "/export", params={"run_id": run_id, "revision": 2})
        assert exported.status_code == 200
    version = request.param
    if version == 1:
        legacy = tmp_path / "legacy"
        legacy.mkdir()
        shutil.copytree(runtime / "documents", legacy / "documents")
        with closing(sqlite3.connect(legacy / "documents.sqlite3")) as db, db:
            db.executescript(
                files("docintel").joinpath("repositories/migrations/001_documents.sql").read_text()
            )
            db.execute("INSERT INTO schema_migrations VALUES(1,'historical')")
            db.execute("ATTACH DATABASE ? AS original", (str(runtime / "documents.sqlite3"),))
            for table in ("documents", "runs", "revisions", "events"):
                columns = ",".join(row[1] for row in db.execute(f"PRAGMA table_info({table})"))
                db.execute(f"INSERT INTO {table}({columns}) SELECT {columns} FROM original.{table}")
        runtime = legacy
    source = tmp_path / "backup"
    helper.backup(runtime, source)
    return source, version, path, run_id, expected, exported.json()


def cli(source):
    return subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/backup_runtime.py"),
            str(source),
            "--verify-backup",
            "--json",
        ],
        env={
            **os.environ,
            "PYTHONPATH": os.pathsep.join(str(ROOT / p) for p in ("backend/src", "pipeline/src")),
        },
        capture_output=True,
        text=True,
        timeout=20,
    )


def rejected(source, helper, tmp_path, code):
    before = tree(source)
    with pytest.raises(BackupVerificationError) as failure:
        verify_backup(source)
    assert failure.value.code == code
    destination = tmp_path / "must-not-exist"
    with pytest.raises(BackupVerificationError):
        helper.restore(source, destination)
    report = cli(source)
    assert report.returncode == 2 and not report.stderr
    assert json.loads(report.stdout) == {"report_version": 1, "status": "error", "code": code}
    assert str(tmp_path) not in report.stdout and "PRIVATE_CANARY" not in report.stdout
    assert not destination.exists() and tree(source) == before


@pytest.mark.parametrize(
    "table,column",
    [
        ("documents", "filename"),
        ("runs", "result_json"),
        ("events", "occurred_at"),
        ("revisions", "saved_at"),
    ],
)
def test_missing_runtime_column_is_rejected_after_rehash(
    confirmed_backup, helper, tmp_path, table, column
):
    source, *_ = confirmed_backup
    with closing(sqlite3.connect(source / "documents.sqlite3")) as db, db:
        db.execute(f"ALTER TABLE {table} DROP COLUMN {column}")
        assert db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
    rehash(source)
    rejected(source, helper, tmp_path, "SNAPSHOT_UNREADABLE")


def test_extra_columns_and_confirmed_records_are_preserved(confirmed_backup, helper, tmp_path):
    source, version, path, run_id, expected, exported = confirmed_backup
    with closing(sqlite3.connect(source / "documents.sqlite3")) as db, db:
        db.execute("ALTER TABLE documents ADD COLUMN extension TEXT")
    rehash(source)
    before = tree(source)
    assert verify_backup(source).schema_version == version
    assert cli(source).returncode == 0
    destination = tmp_path / "restored"
    helper.restore(source, destination)
    assert tree(source) == before
    with closing(sqlite3.connect(destination / "documents.sqlite3")) as db:
        assert db.execute("SELECT max(version) FROM schema_migrations").fetchone() == (version,)
        assert db.execute("SELECT count(*) FROM revisions").fetchone() == (2,)
    if version == 2:
        settings = Settings(_env_file=None, runtime_dir=destination, provider_mode="fixture")
        with TestClient(create_app(settings, start_worker=False)) as api:
            assert api.get(path).json() == expected
            result = api.get(path + "/export", params={"run_id": run_id, "revision": 2})
            assert result.status_code == 200
            actual = result.json()
            actual.pop("exported_at")
            exported.pop("exported_at")
            assert actual == exported


@pytest.mark.parametrize("confirmed_backup", [2], indirect=True)
@pytest.mark.parametrize(
    "table,column",
    [
        ("users", "created_at"),
        ("sessions", "created_at"),
        ("login_budget", "window_start"),
    ],
)
def test_missing_auth_column_is_rejected(confirmed_backup, helper, tmp_path, table, column):
    source, *_ = confirmed_backup
    with closing(sqlite3.connect(source / "documents.sqlite3")) as db, db:
        db.execute(f"ALTER TABLE {table} DROP COLUMN {column}")
    rehash(source)
    rejected(source, helper, tmp_path, "SNAPSHOT_UNREADABLE")
