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
    manifest_bytes: bytes


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_backup(source: Path) -> VerifiedBackup:
    """Offline/stable tree required; never open SQLite through application repositories."""
    try:
        source = source.resolve()
        manifest_bytes = (source / "backup.json").read_bytes()
        manifest = json.loads(manifest_bytes.decode("utf-8"))
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
            # Validate fields used by supported snapshots, without dumping rows or auth state.
            db.execute("SELECT run_id,document_id,status FROM runs LIMIT 0")
            db.execute("SELECT run_id,revision,review_status,fields_json FROM revisions LIMIT 0")
            db.execute("SELECT document_id,run_id,revision,action FROM events LIMIT 0")
            if version == 2:
                db.execute("SELECT owner_id FROM documents LIMIT 0")
                db.execute("SELECT user_id,username,password_hash,is_active FROM users LIMIT 0")
                db.execute("SELECT token_hash,user_id,csrf_token,expires_at FROM sessions LIMIT 0")
                db.execute("SELECT id,window_start,attempts FROM login_budget LIMIT 0")
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
        return VerifiedBackup(version, tuple(validated), manifest_bytes)
    except BackupVerificationError:
        raise
    except (sqlite3.Error, OSError, ValueError, UnicodeError) as exc:
        raise BackupVerificationError("SNAPSHOT_UNREADABLE") from exc
