import hashlib
import os
import sqlite3
import subprocess
import sys

from test_auth_migration import legacy_database

from docintel.config import ROOT
from docintel.repositories.identity import IdentityRepository
from docintel.repositories.locking import RuntimeLock
from docintel.repositories.sqlite import DocumentRepository
from docintel.security import new_token, token_digest, verify_password


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


def test_offline_account_commands_do_not_expose_hashes_or_tokens(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    import manage_auth

    runtime = tmp_path / "runtime"
    manage_auth.manage_user(runtime, "create-user", "alpha", "synthetic-password-123")
    users = manage_auth.manage_user(runtime, "list-users")
    assert len(users) == 1 and set(users[0]) == {"user_id", "username", "is_active"}
    identities = IdentityRepository(DocumentRepository(runtime / "documents.sqlite3"))
    raw = new_token()
    identities.create_session(token_digest(raw), users[0]["user_id"], new_token(), 10, 100)
    manage_auth.manage_user(runtime, "reset-password", "alpha", "new-synthetic-password-456")
    assert identities.active_session(token_digest(raw), 20) is None
    assert verify_password("new-synthetic-password-456", identities.user("alpha")["password_hash"])
    manage_auth.manage_user(runtime, "disable-user", "alpha")
    assert manage_auth.manage_user(runtime, "list-users")[0]["is_active"] == 0


def test_account_administration_refuses_a_running_application(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    import manage_auth

    runtime = tmp_path / "runtime"
    lock = RuntimeLock(runtime / "app.lock")
    lock.acquire()
    try:
        import pytest

        with pytest.raises(RuntimeError):
            manage_auth.manage_user(runtime, "create-user", "alpha", "synthetic-password-123")
    finally:
        lock.release()


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
