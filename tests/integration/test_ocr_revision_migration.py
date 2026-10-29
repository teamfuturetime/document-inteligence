"""Exercise the actual Alembic chain against persisted pre-autosave rows."""
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.core.config import get_settings


def test_ocr_revision_migration_backfills_and_preserves_ocr(tmp_path, monkeypatch):
    database_url = f"sqlite:///{(tmp_path / 'migration.db').as_posix()}"
    monkeypatch.setattr(get_settings(), "DATABASE_URL", database_url)
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).resolve().parents[2] / "backend" / "migrations"))
    command.upgrade(config, "0003")
    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.execute(text("""
                INSERT INTO documents
                    (id, filename, content_type, file_size, file_path, status,
                     ocr_text, ocr_text_corrected, created_at, updated_at)
                VALUES ('before-autosave', 'legacy.pdf', 'application/pdf', 1,
                        'legacy.pdf', 'reviewed', 'RAW OCR', 'Human correction',
                        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """))

        command.upgrade(config, "head")
        with engine.connect() as connection:
            row = connection.execute(text("SELECT ocr_revision, ocr_text, ocr_text_corrected FROM documents")).one()
            assert tuple(row) == (0, "RAW OCR", "Human correction")
        column = next(column for column in inspect(engine).get_columns("documents") if column["name"] == "ocr_revision")
        assert column["nullable"] is False
        assert column["default"] is not None

        # A direct INSERT without ORM defaults must also receive revision zero.
        with engine.begin() as connection:
            connection.execute(text("""
                INSERT INTO documents
                    (id, filename, content_type, file_size, file_path, status,
                     created_at, updated_at)
                VALUES ('after-autosave', 'new.pdf', 'application/pdf', 1,
                        'new.pdf', 'uploaded', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """))
            assert connection.execute(text("SELECT ocr_revision FROM documents WHERE id='after-autosave'")).scalar_one() == 0

        command.downgrade(config, "0003")
        assert "ocr_revision" not in {column["name"] for column in inspect(engine).get_columns("documents")}
        with engine.connect() as connection:
            assert tuple(connection.execute(text("SELECT ocr_text, ocr_text_corrected FROM documents WHERE id='before-autosave'")).one()) == ("RAW OCR", "Human correction")
        command.upgrade(config, "head")
        with engine.connect() as connection:
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0004"
    finally:
        engine.dispose()
