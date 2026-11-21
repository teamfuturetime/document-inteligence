"""Read-only manifest-v1 and SQLite snapshot verification shared by offline helpers."""

import hashlib
import json
import re
import sqlite3
import time
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


class BackupVerificationError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(f"Invalid backup manifest/integrity or snapshot: {code}")


@dataclass(frozen=True)
class VerifiedBackup:
    schema_version: int
    entries: tuple[tuple[str, Path], ...]


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_runtime_columns(db, version):
    # Columns required by migrations 001/002 and runtime readers/writers. Project
    # only these columns: extensions remain compatible; never initialize the source.
    required = {
        "schema_migrations": "version,applied_at",
        "documents": "document_id,document_type,filename,data_origin,input_sha256,"
        "image_width,image_height,created_at,latest_run_id,idempotency_key",
        "runs": "run_id,document_id,status,created_at,finished_at,error_code,result_json",
        "revisions": "run_id,revision,review_status,fields_json,saved_at",
        "events": "event_id,document_id,run_id,revision,action,occurred_at,changes_json",
    }
    if version == 2:
        required["documents"] += ",owner_id"
        required.update(
            {
                "users": "user_id,username,password_hash,is_active,created_at",
                "sessions": "token_hash,user_id,csrf_token,expires_at,created_at",
                "login_budget": "id,window_start,attempts",
            }
        )
    for table, columns in required.items():
        db.execute(f"SELECT {columns} FROM {table} LIMIT 0")


def verify_backup(source: Path) -> VerifiedBackup:
    """Offline/stable tree required; never open SQLite through application repositories."""
    try:
        source = source.resolve()
        manifest = json.loads((source / "backup.json").read_text(encoding="utf-8"))
        if (
            not isinstance(manifest, dict)
            or type(manifest.get("version")) is not int
            or manifest["version"] != 1
            or not isinstance(manifest.get("sha256"), dict)
            or "documents.sqlite3" not in manifest["sha256"]
        ):
            raise BackupVerificationError("MANIFEST_INVALID")
        records = manifest["sha256"]
        validated = []
        for relative, expected in records.items():
            if (
                not isinstance(relative, str)
                or not relative
                or "\\" in relative
                or ":" in relative
                or PurePosixPath(relative).is_absolute()
                or ".." in PurePosixPath(relative).parts
                or PurePosixPath(relative).as_posix() != relative
                or not isinstance(expected, str)
                or re.fullmatch(r"[0-9a-f]{64}", expected) is None
            ):
                raise BackupVerificationError("MANIFEST_INVALID")
            path = (source / relative).resolve()
            if not path.is_relative_to(source) or not path.is_file() or sha256(path) != expected:
                raise BackupVerificationError("FILE_INTEGRITY")
            validated.append((relative, path))
        database = source / "documents.sqlite3"
        if any(
            Path(str(location) + suffix).exists()
            for location in {database, database.resolve()}
            for suffix in ("-wal", "-journal")
        ):
            raise BackupVerificationError("DATABASE_NOT_OFFLINE")
        deadline = time.monotonic() + 10
        with closing(
            sqlite3.connect(
                database.resolve().as_uri() + "?mode=ro&immutable=1", uri=True, timeout=1
            )
        ) as db:
            db.set_progress_handler(lambda: int(time.monotonic() >= deadline), 1000)
            db.execute("PRAGMA query_only=ON")
            db.execute("PRAGMA trusted_schema=OFF")
            if db.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                raise BackupVerificationError("DATABASE_INTEGRITY")
            if db.execute("PRAGMA foreign_key_check").fetchone() is not None:
                raise BackupVerificationError("DATABASE_REFERENCES")
            version = db.execute("SELECT max(version) FROM schema_migrations").fetchone()[0]
            if type(version) is not int or version not in {1, 2}:
                raise BackupVerificationError("SCHEMA_UNSUPPORTED")
            check_runtime_columns(db, version)
            for document_id, input_hash, latest_run_id in db.execute(
                "SELECT document_id,input_sha256,latest_run_id FROM documents"
            ):
                if (
                    not isinstance(document_id, str)
                    or re.fullmatch(r"[0-9a-f]{32}", document_id) is None
                    or not isinstance(input_hash, str)
                    or re.fullmatch(r"[0-9a-f]{64}", input_hash) is None
                ):
                    raise BackupVerificationError("DOCUMENT_INVALID")
                if (
                    db.execute(
                        "SELECT 1 FROM runs WHERE run_id=? AND document_id=?",
                        (latest_run_id, document_id),
                    ).fetchone()
                    is None
                ):
                    raise BackupVerificationError("DATABASE_REFERENCES")
                for kind in ("source", "preview"):
                    key = f"documents/{document_id}.{kind}"
                    if key not in records:
                        raise BackupVerificationError("ASSET_MISSING")
                if records[f"documents/{document_id}.source"] != input_hash:
                    raise BackupVerificationError("SOURCE_HASH_MISMATCH")
        return VerifiedBackup(version, tuple(validated))
    except BackupVerificationError:
        raise
    except (sqlite3.Error, OSError, ValueError, UnicodeError) as exc:
        raise BackupVerificationError("SNAPSHOT_UNREADABLE") from exc
