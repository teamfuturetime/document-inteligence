"""Consistent SQLite backup plus immutable source images; restore only into a new directory."""

import argparse
import hashlib
import json
import shutil
import sqlite3
from contextlib import closing
from pathlib import Path

from docintel.storage.backup import BackupVerificationError, verify_backup
from docintel.storage.local import LocalDocumentStorage
from docintel.storage.publication import (
    new_destination,
    publish_directory,
    staging_directory,
    sync_files,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def backup(runtime: Path, destination: Path):
    runtime, destination = runtime.resolve(), new_destination(destination)
    if destination.is_relative_to(runtime):
        raise ValueError("Destination must be outside source directory")
    if not (runtime / "documents.sqlite3").is_file():
        raise ValueError("Runtime database not found")
    with staging_directory(destination) as staged:
        write_backup(runtime, staged)
        verify_backup(staged)
        sync_files(staged)
        publish_directory(staged, destination)


def write_backup(runtime: Path, destination: Path):
    destination.mkdir(parents=True, exist_ok=False, mode=0o700)
    database = destination / "documents.sqlite3"
    source_database = runtime / "documents.sqlite3"
    locations = {source_database, source_database.resolve()}
    if any(Path(str(location) + "-journal").exists() for location in locations):
        raise ValueError("Runtime requires SQLite recovery before backup")
    resolved_database = source_database.resolve()
    if (
        source_database != resolved_database
        and Path(str(source_database) + "-wal").exists()
    ):
        # A WAL named after an alias has platform-dependent SQLite VFS semantics.
        # Require explicit recovery instead of guessing which image is authoritative.
        raise ValueError(
            "Runtime requires SQLite recovery at the requested database location"
        )
    uri = resolved_database.as_uri() + "?mode=ro"
    # Stable/offline tree: avoid creating WAL/shm for a checkpointed database,
    # but never ignore existing WAL commits when taking a SQLite API snapshot.
    if not any(Path(str(location) + "-wal").exists() for location in locations):
        uri += "&immutable=1"
    with (
        closing(sqlite3.connect(uri, uri=True)) as source,
        closing(sqlite3.connect(database)) as target,
    ):
        source.backup(target)
        database.chmod(0o600)
        rows = target.execute(
            "SELECT document_id,input_sha256 FROM documents"
        ).fetchall()
    if rows and not (runtime / "documents").is_dir():
        raise ValueError("Source assets are missing")
    storage = LocalDocumentStorage(runtime / "documents") if rows else None
    target_storage = LocalDocumentStorage(destination / "documents")
    records = {"documents.sqlite3": sha256(database)}
    for document_id, expected in rows:
        if sha256(storage.path(document_id, "source")) != expected:
            raise ValueError("Source integrity check failed")
        for kind in ("source", "preview"):
            target = target_storage.path(document_id, kind)
            shutil.copyfile(storage.path(document_id, kind), target)
            target.chmod(0o600)
            records[target.relative_to(destination).as_posix()] = sha256(target)
    (destination / "backup.json").write_text(
        json.dumps({"version": 1, "sha256": records}, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (destination / "backup.json").chmod(0o600)


def restore(source: Path, destination: Path):
    source, destination = source.resolve(), new_destination(destination)
    verified = verify_backup(source)
    validated = []
    for relative, path in verified.entries:
        target = (destination / relative).resolve()
        if not target.is_relative_to(destination):
            raise BackupVerificationError("RESTORE_PATH_OUTSIDE")
        validated.append((path, target))
    destination.mkdir(parents=True, exist_ok=False, mode=0o700)
    for path, target in validated:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        target.chmod(0o600)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path, nargs="?")
    parser.add_argument("--verify-backup", action="store_true")
    parser.add_argument(
        "--json", action="store_true", help="Versioned verify-backup report"
    )
    parser.add_argument("--restore", action="store_true")
    args = parser.parse_args()
    if args.verify_backup:
        if args.destination is not None or args.restore:
            parser.error("verify-backup takes only a source")
        try:
            verified = verify_backup(args.source)
            report = {
                "report_version": 1,
                "status": "verified",
                "schema_version": verified.schema_version,
            }
        except BackupVerificationError as exc:
            report = {"report_version": 1, "status": "error", "code": exc.code}
        print(
            json.dumps(report)
            if args.json
            else "Backup verification: "
            + report["status"]
            + (" / " + report["code"] if "code" in report else "")
        )
        return 0 if report["status"] == "verified" else 2
    if args.destination is None or args.json:
        parser.error(
            "backup/restore requires a destination; --json is for verify-backup"
        )
    if args.destination.resolve().is_relative_to(args.source.resolve()):
        parser.error("Destination must be outside source directory")
    (restore if args.restore else backup)(args.source, args.destination)
    print("Restore verified" if args.restore else "Backup verified")


if __name__ == "__main__":
    raise SystemExit(main())
