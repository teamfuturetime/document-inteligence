"""Hash-consistent tampering must not turn an incomplete snapshot into a valid backup."""

import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
from contextlib import closing

import pytest
from test_auth_cli import prepare_legacy

from docintel.config import ROOT
from docintel.storage.backup import BackupVerificationError, sha256, verify_backup


@pytest.fixture
def helper():
    spec = importlib.util.spec_from_file_location(
        "backup_helper", ROOT / "scripts/backup_runtime.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def valid_backup(tmp_path, helper):
    runtime = tmp_path / "runtime"
    prepare_legacy(runtime)
    destination = tmp_path / "backup"
    helper.backup(runtime, destination)
    return destination


def tree(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def rehash(source):
    p = source / "backup.json"
    manifest = json.loads(p.read_text())
    manifest["sha256"]["documents.sqlite3"] = sha256(source / "documents.sqlite3")
    p.write_text(json.dumps(manifest))


@pytest.mark.parametrize(
    "tamper,code",
    [
        ("not_sqlite", "SNAPSHOT_UNREADABLE"),
        ("future", "SCHEMA_UNSUPPORTED"),
        ("missing_table", "SNAPSHOT_UNREADABLE"),
        ("foreign_key", "DATABASE_REFERENCES"),
        ("latest_run", "DATABASE_REFERENCES"),
        ("source_hash", "SOURCE_HASH_MISMATCH"),
        ("remove_preview", "ASSET_MISSING"),
        ("missing_source", "FILE_INTEGRITY"),
        ("outside_manifest", "MANIFEST_INVALID"),
        ("wal", "DATABASE_NOT_OFFLINE"),
    ],
)
def test_rehashed_invalid_snapshots_fail_before_destination_creation(
    valid_backup, helper, tmp_path, tamper, code
):
    source = valid_backup
    database = source / "documents.sqlite3"
    if tamper == "not_sqlite":
        database.write_bytes(b"PRIVATE_CANARY not a database")
    elif tamper in {"future", "missing_table", "foreign_key", "latest_run", "source_hash"}:
        with closing(sqlite3.connect(database)) as db, db:
            if tamper == "future":
                db.execute("INSERT INTO schema_migrations VALUES(9,'future')")
            elif tamper == "missing_table":
                db.execute("DROP TABLE events")
            elif tamper == "foreign_key":
                db.execute("UPDATE runs SET document_id='missing'")
            elif tamper == "latest_run":
                db.execute("UPDATE documents SET latest_run_id='missing'")
            else:
                db.execute("UPDATE documents SET input_sha256=?", ("0" * 64,))
    elif tamper == "remove_preview":
        p = source / "backup.json"
        manifest = json.loads(p.read_text())
        manifest["sha256"].pop("documents/" + "a" * 32 + ".preview")
        p.write_text(json.dumps(manifest))
    elif tamper == "missing_source":
        (source / "documents" / ("a" * 32 + ".source")).unlink()
    elif tamper == "outside_manifest":
        p = source / "backup.json"
        manifest = json.loads(p.read_text())
        manifest["sha256"]["../outside"] = "0" * 64
        p.write_text(json.dumps(manifest))
    else:
        (source / "documents.sqlite3-wal").write_bytes(b"pending")
    rehash(source)
    before = tree(source)
    destination = tmp_path / "must not exist"
    with pytest.raises(BackupVerificationError) as failed:
        helper.restore(source, destination)
    assert failed.value.code == code
    assert "PRIVATE_CANARY" not in str(failed.value)
    assert str(tmp_path) not in str(failed.value)
    assert not destination.exists() and tree(source) == before


def test_schema1_verification_is_readonly(valid_backup):
    before = tree(valid_backup)
    assert verify_backup(valid_backup).schema_version == 1
    assert tree(valid_backup) == before
    with closing(
        sqlite3.connect(
            (valid_backup / "documents.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True
        )
    ) as db:
        assert db.execute("SELECT max(version) FROM schema_migrations").fetchone() == (1,)


def test_cli_verify_reports_only_safe_status(valid_backup):
    def run():
        return subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/backup_runtime.py"),
                str(valid_backup),
                "--verify-backup",
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=20,
            env={
                **os.environ,
                "PYTHONPATH": os.pathsep.join(
                    str(ROOT / p) for p in ("backend/src", "pipeline/src")
                ),
            },
        )

    before = tree(valid_backup)
    result = run()
    assert result.returncode == 0 and not result.stderr
    assert json.loads(result.stdout) == {
        "report_version": 1,
        "status": "verified",
        "schema_version": 1,
    }
    assert tree(valid_backup) == before
    (valid_backup / "documents.sqlite3").write_bytes(b"PRIVATE_CANARY")
    rehash(valid_backup)
    before = tree(valid_backup)
    failed = run()
    assert failed.returncode == 2 and not failed.stderr
    assert json.loads(failed.stdout)["code"] == "SNAPSHOT_UNREADABLE"
    assert "PRIVATE_CANARY" not in failed.stdout and str(valid_backup) not in failed.stdout
    assert tree(valid_backup) == before
