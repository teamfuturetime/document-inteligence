"""Offline smoke assertions inside the disposable Compose project for issue #52."""

import hashlib
import json
import secrets
import shutil
import sqlite3
import time
from contextlib import closing
from importlib.resources import files
from pathlib import Path

from backup_runtime import backup, restore
from docintel.repositories.identity import IdentityRepository
from docintel.repositories.schema import version
from docintel.repositories.sqlite import DocumentRepository
from manage_auth import manage_user, migrate_runtime


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def table_rows(connection, table):
    return connection.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()


def main():
    runtime, state = Path("/app/runtime"), Path("/qa-state")
    assert runtime.is_dir() and state.is_dir()
    # Offline account only in this disposable volume, with no secret in argv or report.
    manage_user(runtime, "create-user", "dockerqa", secrets.token_urlsafe(24))
    identities = IdentityRepository(DocumentRepository(runtime / "documents.sqlite3"))
    token_hash = hashlib.sha256(secrets.token_bytes(32)).hexdigest()
    now = time.time()
    identities.create_session(
        token_hash,
        identities.user("dockerqa")["user_id"],
        secrets.token_urlsafe(24),
        now,
        now + 3600,
    )
    snapshot, restored = state / "snapshot", state / "restored"
    backup(runtime, snapshot)
    manifest = json.loads((snapshot / "backup.json").read_text())
    assert manifest["version"] == 1
    assert all(
        digest(snapshot / name) == value for name, value in manifest["sha256"].items()
    )
    restore(snapshot, restored)
    assert all(
        digest(restored / name) == value for name, value in manifest["sha256"].items()
    )
    with closing(sqlite3.connect(runtime / "documents.sqlite3")) as source:
        assert version(source) == 2
        with closing(sqlite3.connect(restored / "documents.sqlite3")) as target:
            assert target.execute("PRAGMA integrity_check").fetchone() == ("ok",)
            for table in (
                "documents",
                "runs",
                "revisions",
                "events",
                "users",
                "sessions",
            ):
                assert table_rows(source, table) == table_rows(target, table)
            assert target.execute("SELECT count(*) FROM sessions").fetchone() == (1,)
        assert (snapshot.stat().st_mode & 0o777) == 0o700
        assert (restored / "documents.sqlite3").stat().st_mode & 0o777 == 0o600
        # Construct a separate valid DB1 using the shipped migration schema and
        # synthetic records just produced by native OCR. Never downgrade a live DB.
        legacy = state / "legacy"
        legacy.mkdir()
        shutil.copytree(runtime / "documents", legacy / "documents")
        with closing(sqlite3.connect(legacy / "documents.sqlite3")) as old:
            old.executescript(
                files("docintel")
                .joinpath("repositories/migrations/001_documents.sql")
                .read_text()
            )
            old.execute("INSERT INTO schema_migrations VALUES(1,'synthetic-qa')")
            columns = "document_id,document_type,filename,data_origin,input_sha256,image_width,image_height,created_at,latest_run_id,idempotency_key"
            rows = source.execute(f"SELECT {columns} FROM documents").fetchall()
            old.executemany("INSERT INTO documents VALUES(?,?,?,?,?,?,?,?,?,?)", rows)
            for table in ("runs", "revisions", "events"):
                for row in table_rows(source, table):
                    placeholders = ",".join("?" for _ in row)
                    old.execute(f"INSERT INTO {table} VALUES({placeholders})", row)
            old.commit()
    migrate_runtime(legacy, state / "before-migration")
    with closing(sqlite3.connect(legacy / "documents.sqlite3")) as migrated:
        assert version(migrated) == 2
        assert migrated.execute(
            "SELECT DISTINCT owner_id FROM documents"
        ).fetchall() == [("local",)]
        assert migrated.execute(
            "SELECT is_active FROM users WHERE user_id='local'"
        ).fetchone() == (0,)
        with closing(sqlite3.connect(runtime / "documents.sqlite3")) as original:
            for table in ("runs", "revisions", "events"):
                assert table_rows(migrated, table) == table_rows(original, table)
    with closing(sqlite3.connect(state / "before-migration/documents.sqlite3")) as old:
        assert version(old) == 1
    manage_user(legacy, "create-user", "legacyqa", secrets.token_urlsafe(24))
    with closing(sqlite3.connect(legacy / "documents.sqlite3")) as migrated:
        assert migrated.execute(
            "SELECT DISTINCT owner_id FROM documents"
        ).fetchall() == [("local",)]
    for operation, source in ((backup, runtime), (restore, snapshot)):
        for destination in (snapshot, state / "dangling"):
            if destination.name == "dangling" and not destination.is_symlink():
                destination.symlink_to(state / "missing", target_is_directory=True)
            try:
                operation(source, destination)
            except FileExistsError:
                pass
            else:
                raise AssertionError("Existing destination was accepted")
            assert not (state / "missing").exists()
    corrupt = state / "corrupt"
    shutil.copytree(snapshot, corrupt)
    (corrupt / "documents.sqlite3").write_bytes(b"synthetic corruption")
    try:
        restore(corrupt, state / "rejected")
    except ValueError:
        pass
    else:
        raise AssertionError("Corrupted backup accepted")
    assert not (state / "rejected").exists()
    print(
        json.dumps(
            {
                "status": "passed",
                "checks": [
                    "schema2",
                    "snapshot_hashes",
                    "restored_tables_assets_auth",
                    "private_modes",
                    "db1_backup_migration",
                    "legacy_remains_local",
                    "destination_leaf_guards",
                    "corrupted_backup_rejected",
                ],
            }
        )
    )


if __name__ == "__main__":
    main()
