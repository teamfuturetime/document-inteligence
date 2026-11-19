import sqlite3
from contextlib import closing, contextmanager
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path

from docintel.repositories.schema import SCHEMA_VERSION, upgrade_connection, version


def now() -> str:
    return datetime.now(UTC).isoformat()


class DocumentRepository:
    """Short-lived connections; each business write holds a single SQLite transaction."""

    def __init__(self, path: Path):
        self.path = path

    def connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def initialize(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as connection:
            current = version(connection)
            if current > SCHEMA_VERSION:
                raise RuntimeError("Database schema is newer than this application")
            existing = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE name='documents'"
            ).fetchone()
            if current < SCHEMA_VERSION and existing:
                if connection.execute("SELECT count(*) FROM documents").fetchone()[0]:
                    raise RuntimeError(
                        "Populated legacy database requires offline backup and migration"
                    )
            connection.execute("PRAGMA journal_mode=WAL")
            if current == 0:
                existing = connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE name='documents'"
                ).fetchone()
                if existing and connection.execute("SELECT count(*) FROM documents").fetchone()[0]:
                    raise RuntimeError("Unversioned populated database requires manual recovery")
                script = (
                    files("docintel")
                    .joinpath("repositories/migrations/001_documents.sql")
                    .read_text()
                )
                connection.executescript(script)
                connection.execute("INSERT OR IGNORE INTO schema_migrations VALUES(1,?)", (now(),))
                connection.commit()
            if version(connection) == 1:
                if connection.execute("SELECT count(*) FROM documents").fetchone()[0]:
                    raise RuntimeError("Populated schema 1 requires offline backup and migration")
                upgrade_connection(connection)
        self.path.chmod(0o600)

    @contextmanager
    def transaction(self, *, write: bool = False):
        connection = self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()
