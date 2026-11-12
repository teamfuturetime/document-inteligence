CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS documents(
    document_id TEXT PRIMARY KEY, document_type TEXT NOT NULL, filename TEXT NOT NULL,
    data_origin TEXT NOT NULL CHECK(data_origin IN ('synthetic','sample')),
    input_sha256 TEXT NOT NULL, image_width INTEGER NOT NULL, image_height INTEGER NOT NULL,
    created_at TEXT NOT NULL, latest_run_id TEXT NOT NULL,
    idempotency_key TEXT UNIQUE
);
CREATE TABLE IF NOT EXISTS runs(
    run_id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(document_id),
    status TEXT NOT NULL CHECK(status IN ('queued','running','succeeded','failed','unavailable')),
    created_at TEXT NOT NULL, finished_at TEXT, error_code TEXT, result_json TEXT
);
CREATE INDEX IF NOT EXISTS runs_document ON runs(document_id,created_at);
CREATE INDEX IF NOT EXISTS runs_queue ON runs(status,created_at);
CREATE TABLE IF NOT EXISTS revisions(
    run_id TEXT NOT NULL REFERENCES runs(run_id), revision INTEGER NOT NULL CHECK(revision > 0),
    review_status TEXT NOT NULL CHECK(review_status IN ('draft','confirmed')),
    fields_json TEXT NOT NULL, saved_at TEXT NOT NULL,
    PRIMARY KEY(run_id,revision)
);
CREATE TABLE IF NOT EXISTS events(
    event_id INTEGER PRIMARY KEY AUTOINCREMENT, document_id TEXT NOT NULL REFERENCES documents(document_id),
    run_id TEXT NOT NULL REFERENCES runs(run_id), revision INTEGER, action TEXT NOT NULL,
    occurred_at TEXT NOT NULL, changes_json TEXT NOT NULL
);
