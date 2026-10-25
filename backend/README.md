# Backend

FastAPI composition ở `src/docintel/api/app.py`; canonical product contracts ở domain/documents.py, fixture contracts cũ ở domain/models.py. HTTP routes không chạy SQL hoặc native OCR trực tiếp: DocumentService điều phối transaction/use case; LocalInferenceWorker xử lý persisted queue; storage quản lý server-generated paths; adapter chuyển inference DTO sang domain.

Từ gốc repo: `uv sync --project backend --locked`, cài Tesseract 5 rồi chạy `scripts/fetch_ocr_models.py`. Bật provider tesseract và chạy `uv run --project backend --locked uvicorn docintel.api.app:app --host 127.0.0.1 --port 8000`. Một worker process cho mỗi runtime; process lock từ chối instance thứ hai.

DB/uploads/model ở runtime ngoài Git. Không đọc gold trong inference, không đổi machine prediction khi review và không export từ JSON client. Migration có version; từ chối DB mới hơn app. [Kiến trúc](../docs/product/architecture.md), [runbook](../docs/product/runbook.md), [contracts](../contracts/README.md).
