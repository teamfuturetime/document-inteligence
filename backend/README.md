# Backend – Tuần 1

FastAPI quản lý metadata bằng SQLAlchemy/Pydantic và lưu tài liệu gốc trên ổ đĩa.
Các lệnh dưới đây chạy tại **thư mục gốc repository** với Python 3.12.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements-dev.txt
# Khi chưa có .env; giữ cấu hình riêng nếu đã có file này.
cp -n .env.local.example .env
PYTHONPATH=backend:. uvicorn app.main:app --reload
```

- Swagger: <http://localhost:8000/docs>.
- Kiểm tra ứng dụng: `GET /health`.
- SQLite mặc định: `./documents.db`; PostgreSQL dùng `DATABASE_URL=postgresql+psycopg://user:password@host:5432/documents`.
- File gốc: `STORAGE_DIR=./uploads`; giới hạn `MAX_UPLOAD_MB=15` MiB, phải lớn hơn 0.
- `OCR_ENGINE=mock` cho phép kiểm tra upload mà không cần cài Tesseract.
- Nếu đặt `API_KEY`, gửi header `X-API-Key` khi gọi `/api/v1/documents`.

## Cấu trúc

| Thư mục | Trách nhiệm |
|---|---|
| `app/main.py` | Ứng dụng, lifespan, CORS và health check |
| `app/core/` | Cấu hình môi trường, database, logging và API key |
| `app/models/` | Model SQLAlchemy |
| `app/schemas/` | Schema Pydantic |
| `app/repositories/` | Truy vấn và transaction |
| `app/api/` | HTTP endpoints |
| `app/services/` | Validation và lưu file |
| `migrations/` | Migration database bằng Alembic |
| `../tests/` | Unit, integration và end-to-end tests |
