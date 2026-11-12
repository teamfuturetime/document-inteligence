import hashlib
import os
import sqlite3
import subprocess
import sys

from test_auth_migration import legacy_database

from docintel.config import ROOT
from docintel.repositories.locking import RuntimeLock


def prepare_legacy(runtime):
    runtime.mkdir()
    database = runtime / "documents.sqlite3"
    with legacy_database(database) as connection:
        connection.execute(
            "UPDATE documents SET input_sha256=?", (hashlib.sha256(b"synthetic").hexdigest(),)
        )
    files = runtime / "documents"
    files.mkdir()
    (files / ("a" * 32 + ".source")).write_bytes(b"synthetic")
    (files / ("a" * 32 + ".preview")).write_bytes(b"synthetic-preview")


def command(runtime, *arguments):
    return subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/manage_auth.py"),
            "--runtime",
            str(runtime),
            *map(str, arguments),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=os.environ.copy(),
    )


def test_cli_migrates_legacy_only_after_complete_runtime_backup(tmp_path):
    runtime, backup = tmp_path / "runtime", tmp_path / "backup"
    prepare_legacy(runtime)
    result = command(runtime, "migrate", "--backup", backup)
    assert result.returncode == 0, result.stderr
    with sqlite3.connect(runtime / "documents.sqlite3") as db:
        assert db.execute("SELECT owner_id FROM documents").fetchone() == ("local",)
    with sqlite3.connect(backup / "documents.sqlite3") as db:
        assert db.execute("SELECT max(version) FROM schema_migrations").fetchone() == (1,)
    assert (backup / "documents" / ("a" * 32 + ".source")).read_bytes() == b"synthetic"


def test_cli_migration_refuses_a_running_worker(tmp_path):
    runtime, backup = tmp_path / "runtime", tmp_path / "backup"
    prepare_legacy(runtime)
    lock = RuntimeLock(runtime / "worker.lock")
    lock.acquire()
    try:
        assert command(runtime, "migrate", "--backup", backup).returncode != 0
    finally:
        lock.release()
    assert not backup.exists()
