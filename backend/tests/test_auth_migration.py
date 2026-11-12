import sqlite3
from importlib.resources import files

import pytest

from docintel.repositories import schema


def legacy_database(path):
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys=ON")
    connection.executescript(
        files("docintel").joinpath("repositories/migrations/001_documents.sql").read_text()
    )
    connection.execute("INSERT INTO schema_migrations VALUES(1,'legacy')")
    connection.execute(
        "INSERT INTO documents VALUES(?,?,?,?,?,?,?,?,?,?)",
        (
            "a" * 32,
            "hoa_don",
            "synthetic.png",
            "synthetic",
            "hash",
            10,
            10,
            "created",
            "run",
            "retry",
        ),
    )
    connection.execute(
        "INSERT INTO runs(run_id,document_id,status,created_at) VALUES('run',?,'queued','created')",
        ("a" * 32,),
    )
    connection.commit()
    return connection


def test_sql_migration_preserves_legacy_relations_and_seals_local_owner(tmp_path):
    with legacy_database(tmp_path / "old.sqlite3") as connection:
        connection.execute("PRAGMA foreign_keys=OFF")
        connection.executescript(
            files("docintel").joinpath("repositories/migrations/002_auth_ownership.sql").read_text()
        )
        connection.execute("PRAGMA foreign_keys=ON")
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connection.execute("SELECT owner_id,idempotency_key FROM documents").fetchone() == (
            "local",
            "retry",
        )
        assert connection.execute(
            "SELECT is_active FROM users WHERE user_id='local'"
        ).fetchone() == (0,)
        assert connection.execute("SELECT count(*) FROM runs").fetchone() == (1,)


def test_upgrade_backs_up_real_sqlite_before_owner_migration(tmp_path):
    database, backup = tmp_path / "old.sqlite3", tmp_path / "backup.sqlite3"
    legacy_database(database).close()
    schema.upgrade_database(database, backup)
    with sqlite3.connect(database) as upgraded, sqlite3.connect(backup) as original:
        assert schema.version(upgraded) == 2
        assert schema.version(original) == 1
        assert original.execute("SELECT count(*) FROM documents").fetchone() == (1,)
        assert upgraded.execute("SELECT count(*) FROM runs").fetchone() == (1,)


def test_failed_upgrade_rolls_back_ddl_and_keeps_backup(tmp_path, monkeypatch):
    database, backup = tmp_path / "old.sqlite3", tmp_path / "backup.sqlite3"
    legacy_database(database).close()
    original = schema.statements
    monkeypatch.setattr(schema, "statements", lambda: original() + ["INVALID SQL"])
    with pytest.raises(sqlite3.OperationalError):
        schema.upgrade_database(database, backup)
    with sqlite3.connect(database) as connection:
        assert schema.version(connection) == 1
        assert connection.execute("SELECT count(*) FROM documents").fetchone() == (1,)
        assert not connection.execute("SELECT 1 FROM sqlite_master WHERE name='users'").fetchone()
    assert backup.is_file()


def test_existing_backup_is_never_overwritten(tmp_path):
    database, backup = tmp_path / "old.sqlite3", tmp_path / "backup.sqlite3"
    legacy_database(database).close()
    backup.write_bytes(b"preserve")
    with pytest.raises(FileExistsError):
        schema.upgrade_database(database, backup)
    assert backup.read_bytes() == b"preserve"
