"""Consistent SQLite backup plus immutable source images; restore only into a new directory."""

import argparse
import hashlib
import json
import shutil
import sqlite3
from contextlib import closing
from pathlib import Path

from docintel.storage.local import LocalDocumentStorage


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def backup(runtime: Path, destination: Path):
    if not (runtime / "documents.sqlite3").is_file():
        raise ValueError("Runtime database not found")
    destination.mkdir(parents=True, exist_ok=False)
    database = destination / "documents.sqlite3"
    with (
        closing(sqlite3.connect(runtime / "documents.sqlite3")) as source,
        closing(sqlite3.connect(database)) as target,
    ):
        source.backup(target)
        rows = target.execute(
            "SELECT document_id,input_sha256 FROM documents"
        ).fetchall()
    storage = LocalDocumentStorage(runtime / "documents")
    target_storage = LocalDocumentStorage(destination / "documents")
    records = {"documents.sqlite3": sha256(database)}
    for document_id, expected in rows:
        if sha256(storage.path(document_id, "source")) != expected:
            raise ValueError("Source integrity check failed")
        for kind in ("source", "preview"):
            target = target_storage.path(document_id, kind)
            shutil.copyfile(storage.path(document_id, kind), target)
            records[target.relative_to(destination).as_posix()] = sha256(target)
    (destination / "backup.json").write_text(
        json.dumps({"version": 1, "sha256": records}, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def restore(source: Path, destination: Path):
    manifest = json.loads((source / "backup.json").read_text(encoding="utf-8"))
    validated = []
    for relative, expected in manifest["sha256"].items():
        path = (source / relative).resolve()
        if not path.is_relative_to(source.resolve()) or sha256(path) != expected:
            raise ValueError("Backup integrity or path check failed")
        target = (destination / relative).resolve()
        if not target.is_relative_to(destination.resolve()):
            raise ValueError("Restore path outside target")
        validated.append((path, target))
    destination.mkdir(parents=True, exist_ok=False)
    for path, target in validated:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--restore", action="store_true")
    args = parser.parse_args()
    if args.destination.resolve().is_relative_to(args.source.resolve()):
        parser.error("Destination must be outside source directory")
    (restore if args.restore else backup)(args.source, args.destination)
    print("Restore verified" if args.restore else "Backup verified")


if __name__ == "__main__":
    main()
