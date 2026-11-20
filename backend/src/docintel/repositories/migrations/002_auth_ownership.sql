CREATE TABLE users(
    user_id TEXT PRIMARY KEY, username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL, is_active INTEGER NOT NULL CHECK(is_active IN (0,1)),
    created_at TEXT NOT NULL
);
INSERT INTO users VALUES('local','__local__','disabled',0,'legacy-local-principal');
CREATE TABLE sessions(
    token_hash TEXT PRIMARY KEY CHECK(length(token_hash)=64),
    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    csrf_token TEXT NOT NULL, expires_at REAL NOT NULL, created_at REAL NOT NULL
);
CREATE INDEX sessions_user ON sessions(user_id);
CREATE INDEX sessions_expiry ON sessions(expires_at);
CREATE TABLE login_budget(
    id INTEGER PRIMARY KEY CHECK(id=1), window_start REAL NOT NULL,
    attempts INTEGER NOT NULL CHECK(attempts>=0)
);
CREATE TABLE documents_v2(
    document_id TEXT PRIMARY KEY, document_type TEXT NOT NULL, filename TEXT NOT NULL,
    data_origin TEXT NOT NULL CHECK(data_origin IN ('synthetic','sample')),
    input_sha256 TEXT NOT NULL, image_width INTEGER NOT NULL, image_height INTEGER NOT NULL,
    created_at TEXT NOT NULL, latest_run_id TEXT NOT NULL, idempotency_key TEXT,
    owner_id TEXT NOT NULL DEFAULT 'local' REFERENCES users(user_id),
    UNIQUE(owner_id,idempotency_key)
);
INSERT INTO documents_v2 SELECT document_id,document_type,filename,data_origin,input_sha256,
    image_width,image_height,created_at,latest_run_id,idempotency_key,'local' FROM documents;
DROP TABLE documents;
ALTER TABLE documents_v2 RENAME TO documents;
CREATE INDEX documents_owner ON documents(owner_id,created_at);
