# Backend

Owner: thành viên 3 — Backend/API/Validation.

Package `document-backend` có FastAPI app factory, router `GET /health`,
`POST /api/v1/extract` (mock), error handlers và API/contract tests. Models nằm
ở package `document-contracts` trong `schemas/`, không phụ thuộc FastAPI.
Đã có upload validation và fixed mock response, chưa có OCR/extraction thật,
review validation service hoặc database.

Chạy từ root sau `uv sync --locked`:

```bash
.venv/bin/python -m uvicorn document_backend.main:app --host 127.0.0.1 --port 8000 --reload
.venv/bin/python -m pytest backend/tests -q
```

Health trả `mode=mock`, `ocr_ready=false`. Extract kiểm tra nội dung file rồi
trả hóa đơn mẫu cố định, không dựa vào tài liệu upload. Confidence là null.
Xem [mock demo](../docs/mock-demo.md) cho giới hạn, lỗi và ví dụ curl.
Xem [hướng dẫn local](../docs/development.md) và [contract](../docs/contracts.md).
