# Backend

FastAPI app factory, GET /health, POST /api/v1/extract thật và
POST /api/v1/validate. Contracts trong document-contracts, pipeline độc lập HTTP.

Từ root: `uv sync --locked`, cài model theo [OCR guide](../docs/ocr.md),
chạy `.venv/bin/python -m uvicorn document_backend.main:app --host 127.0.0.1 --port 8000`.
Real mặc định; VDI_MODE=mock chọn fixture có nhãn rõ. Không fallback mock.

Xem [development](../docs/development.md), [real pipeline](../docs/real-pipeline.md),
[validation](../docs/review-validation.md), [contract](../docs/contracts.md).
