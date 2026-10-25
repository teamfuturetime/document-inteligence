import sqlite3
from contextlib import closing, contextmanager
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path


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
            exists = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
            ).fetchone()
            if (
                exists
                and (
                    connection.execute("SELECT max(version) FROM schema_migrations").fetchone()[0]
                    or 0
                )
                > 1
            ):
                raise RuntimeError("Database schema is newer than this application")
            connection.execute("PRAGMA journal_mode=WAL")
            script = (
                files("docintel")
                .joinpath("repositories/migrations/001_documents.sql")
                .read_text(encoding="utf-8")
            )
            connection.executescript(script)
            connection.execute("INSERT OR IGNORE INTO schema_migrations VALUES(1,?)", (now(),))
            connection.commit()

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
