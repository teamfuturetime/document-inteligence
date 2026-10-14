# Backend

Owner: thành viên 3 — Backend/API/Validation.

Package `document-backend` có FastAPI app factory, router `GET /health`,
error handlers và API/contract tests trong `tests/`. Pydantic models nguồn nằm
ở package `document-contracts` trong `schemas/`, không phụ thuộc FastAPI.
Chưa có upload/extraction, review validation service hoặc database.

Chạy từ root sau `uv sync --locked`:

```bash
.venv/bin/python -m uvicorn document_backend.main:app --host 127.0.0.1 --port 8000 --reload
.venv/bin/python -m pytest backend/tests -q
```

Health trả `mode=mock`, `ocr_ready=false`; chưa có demo extraction hoạt động.
Xem [hướng dẫn local](../docs/development.md) và [contract](../docs/contracts.md).
