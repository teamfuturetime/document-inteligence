"""Explicit SQLite upgrade primitives; populated runtimes require offline backup first."""

import sqlite3
from contextlib import closing
from importlib.resources import files
from pathlib import Path

SCHEMA_VERSION = 2


def version(connection: sqlite3.Connection) -> int:
    exists = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE name='schema_migrations'"
    ).fetchone()
    return (
        int(
            connection.execute("SELECT coalesce(max(version),0) FROM schema_migrations").fetchone()[
                0
            ]
        )
        if exists
        else 0
    )


def statements() -> list[str]:
    script = (
        files("docintel").joinpath("repositories/migrations/002_auth_ownership.sql").read_text()
    )
    return [statement.strip() for statement in script.split(";") if statement.strip()]


def upgrade_connection(connection: sqlite3.Connection) -> None:
    if connection.in_transaction:
        raise RuntimeError("Migration requires a connection outside a transaction")
    connection.execute("PRAGMA foreign_keys=OFF")
    try:
        connection.execute("BEGIN IMMEDIATE")
        current = version(connection)
        if current > SCHEMA_VERSION:
            raise RuntimeError("Database schema is newer than this application")
        if current == SCHEMA_VERSION:
            connection.rollback()
            return
        if current != 1:
            raise RuntimeError("Only schema 1 can be upgraded")
        for statement in statements():
            connection.execute(statement)
        if connection.execute("PRAGMA foreign_key_check").fetchall():
            raise RuntimeError("Migration foreign-key verification failed")
        connection.execute("INSERT INTO schema_migrations VALUES(2,datetime('now'))")
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.execute("PRAGMA foreign_keys=ON")


def upgrade_database(database: Path, backup_database: Path) -> None:
    if not database.is_file():
        raise ValueError("Existing database required")
    with closing(sqlite3.connect(database)) as connection:
        current = version(connection)
        if current != 1:
            raise RuntimeError("Expected schema 1; database unchanged")
        with backup_database.open("xb"):
            pass
        backup_database.chmod(0o600)
        with closing(sqlite3.connect(backup_database)) as target:
            connection.backup(target)
            if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RuntimeError("Backup integrity verification failed")
        upgrade_connection(connection)
