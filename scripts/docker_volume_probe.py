"""Offline smoke assertions inside the disposable Compose project for issue #52."""

import hashlib
import json
import secrets
import shutil
import sqlite3
import subprocess
import sys
import time
from contextlib import closing
from importlib.resources import files
from pathlib import Path

from backup_runtime import backup, restore
from docintel.repositories.identity import IdentityRepository
from docintel.repositories.schema import version
from docintel.repositories.sqlite import DocumentRepository
from docintel.storage.backup import BackupVerificationError, verify_backup
from manage_auth import adopt_local, manage_user, migrate_runtime


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def table_rows(connection, table):
    return connection.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()


def fingerprints(directory):
    return {
        path.relative_to(directory).as_posix(): digest(path)
        for path in directory.rglob("*")
        if path.is_file()
    }


def rehash_database(snapshot):
    manifest = json.loads((snapshot / "backup.json").read_text())
    manifest["sha256"]["documents.sqlite3"] = digest(snapshot / "documents.sqlite3")
    (snapshot / "backup.json").write_text(json.dumps(manifest), encoding="utf-8")


def verifier_probes(snapshot, state):
    """Exercise merged verifier with rehashed malformed copies, never the source DB."""
    before = fingerprints(snapshot)
    schema = verify_backup(snapshot).schema_version
    results = []
    cases = {
        "missing_filename": (
            "ALTER TABLE documents DROP COLUMN filename",
            "SNAPSHOT_UNREADABLE",
        ),
        "missing_result": (
            "ALTER TABLE runs DROP COLUMN result_json",
            "SNAPSHOT_UNREADABLE",
        ),
        "missing_revisions": ("DELETE FROM revisions", "DATABASE_REFERENCES"),
        "missing_event_revision": (
            "UPDATE events SET revision=999999 WHERE revision IS NOT NULL",
            "DATABASE_REFERENCES",
        ),
        "cross_document_event": (
            (
                "UPDATE events SET document_id=(SELECT document_id FROM documents "
                "WHERE document_id!=events.document_id LIMIT 1) WHERE event_id="
                "(SELECT event_id FROM events LIMIT 1)"
            ),
            "DATABASE_REFERENCES",
        ),
    }
    for name, (sql, code) in cases.items():
        broken, destination = state / name, state / (name + "-rejected")
        shutil.copytree(snapshot, broken)
        with closing(sqlite3.connect(broken / "documents.sqlite3")) as db, db:
            db.execute(sql)
            assert db.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
            assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        rehash_database(broken)
        unchanged = fingerprints(broken)
        for operation in (
            verify_backup,
            lambda source, dest=destination: restore(source, dest),
        ):
            try:
                operation(broken)
            except BackupVerificationError as error:
                assert error.code == code
            else:
                raise AssertionError("Malformed snapshot accepted: " + name)
        cli = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).with_name("backup_runtime.py")),
                str(broken),
                "--verify-backup",
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        assert cli.returncode == 2 and not cli.stderr
        assert json.loads(cli.stdout) == {
            "report_version": 1,
            "status": "error",
            "code": code,
        }
        assert not destination.exists() and fingerprints(broken) == unchanged
        results.append(
            {
                "case": name,
                "code": code,
                "cli_exit": cli.returncode,
                "integrity_fk_clean": True,
                "rehash": True,
                "destination_absent": True,
                "snapshot_unchanged": True,
            }
        )
    extra = state / "extra-columns"
    shutil.copytree(snapshot, extra)
    with closing(sqlite3.connect(extra / "documents.sqlite3")) as db, db:
        db.execute("ALTER TABLE documents ADD COLUMN qa_extension TEXT")
    rehash_database(extra)
    assert verify_backup(extra).schema_version == schema
    restore(extra, state / "extra-columns-restored")
    for status in ("queued", "failed"):
        positive = state / (status + "-no-revision")
        shutil.copytree(snapshot, positive)
        with closing(sqlite3.connect(positive / "documents.sqlite3")) as db, db:
            run_id = db.execute(
                "SELECT run_id FROM runs ORDER BY created_at DESC LIMIT 1"
            ).fetchone()[0]
            db.execute("DELETE FROM events WHERE run_id=?", (run_id,))
            db.execute("DELETE FROM revisions WHERE run_id=?", (run_id,))
            db.execute(
                "UPDATE runs SET status=?, result_json=NULL WHERE run_id=?",
                (status, run_id),
            )
        rehash_database(positive)
        assert verify_backup(positive).schema_version == schema
        restore(positive, state / (status + "-restored"))
    assert fingerprints(snapshot) == before
    return {
        "negative_cases": results,
        "positive_cases": [
            "schema" + str(schema),
            "extra_columns",
            "queued_no_revision",
            "failed_no_revision",
        ],
    }


def main():
    runtime, state = Path("/app/runtime"), Path("/qa-state")
    assert runtime.is_dir() and state.is_dir()
    # Offline account only in this disposable volume, with no secret in argv or report.
    credentials = {
        name: secrets.token_urlsafe(24) for name in ("dockerqa", "foreignqa")
    }
    for name, password in credentials.items():
        manage_user(runtime, "create-user", name, password)
    secret_file = state / "http-auth.json"
    secret_file.write_text(json.dumps(credentials), encoding="utf-8")
    secret_file.chmod(0o600)
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
    source_before = fingerprints(runtime)
    backup(runtime, snapshot)
    assert verify_backup(snapshot).schema_version == 2
    verifier = verifier_probes(snapshot, state)
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
    assert verify_backup(state / "before-migration").schema_version == 1
    assert verify_backup(snapshot).schema_version == 2
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
    # A separate owned runtime proves session restore over HTTP without changing
    # local-owner source documents. Credentials stay in the disposable private volume.
    owned_source = state / "owned-source"
    restore(snapshot, owned_source)
    adopt_local(owned_source, "dockerqa", state / "before-adoption")
    backup(owned_source, state / "owned-snapshot")
    restore(state / "owned-snapshot", state / "restored-session")
    with (
        closing(sqlite3.connect(owned_source / "documents.sqlite3")) as original,
        closing(
            sqlite3.connect(state / "restored-session/documents.sqlite3")
        ) as target,
    ):
        for table in ("documents", "runs", "revisions", "events", "users", "sessions"):
            assert table_rows(original, table) == table_rows(target, table)
        assert target.execute(
            "SELECT count(*) FROM documents WHERE owner_id='local'"
        ).fetchone() == (0,)
    assert fingerprints(runtime) == source_before
    print(
        json.dumps(
            {
                "status": "passed",
                "verifier": verifier,
                "snapshot_sha256": digest(snapshot / "documents.sqlite3"),
                "source_unchanged": True,
                "checks": [
                    "schema2",
                    "snapshot_hashes",
                    "restored_tables_assets_auth",
                    "private_modes",
                    "db1_backup_migration",
                    "legacy_remains_local",
                    "destination_leaf_guards",
                    "corrupted_backup_rejected",
                    "merged_verifier_rehashed_negatives",
                    "owned_snapshot_auth_preserved",
                ],
            }
        )
    )


if __name__ == "__main__":
    main()
