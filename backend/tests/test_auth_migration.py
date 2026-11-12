import sqlite3
from importlib.resources import files


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
