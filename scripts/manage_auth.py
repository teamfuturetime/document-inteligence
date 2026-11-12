"""Offline account/migration administration. Never accept passwords via argv or print secrets."""

import argparse
import sqlite3
from contextlib import closing
from pathlib import Path

from backup_runtime import backup
from docintel.repositories.locking import RuntimeLock
from docintel.repositories.schema import upgrade_connection, version


def migrate_runtime(runtime: Path, destination: Path):
    if destination.resolve().is_relative_to(runtime.resolve()):
        raise ValueError("Backup must be outside runtime")
    database = runtime / "documents.sqlite3"
    if not database.is_file():
        raise ValueError("Existing runtime required")
    lock = RuntimeLock(runtime / "worker.lock")
    lock.acquire()
    try:
        with closing(sqlite3.connect(database)) as connection:
            if version(connection) != 1:
                raise RuntimeError("Expected schema 1; no migration performed")
            backup(runtime, destination)
            upgrade_connection(connection)
    finally:
        lock.release()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    migrate = commands.add_parser("migrate")
    migrate.add_argument("--backup", type=Path, required=True)
    args = parser.parse_args()
    migrate_runtime(args.runtime, args.backup)
    print("Migration verified; previous runtime preserved in backup.")


if __name__ == "__main__":
    main()
