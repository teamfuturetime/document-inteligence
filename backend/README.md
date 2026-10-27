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

## Database và migration

Chạy migration trước khi khởi động trên database mới:

```bash
alembic upgrade head
alembic current
```

Ứng dụng vẫn tự tạo bảng khi khởi động để hỗ trợ demo cục bộ. Nếu database đã
được tạo bởi ứng dụng, đối chiếu schema với model trước khi chạy
`alembic stamp head` để ghi nhận phiên bản mà không tạo lại bảng; sau đó dùng
`alembic check` để xác nhận không còn khác biệt.
Không chạy migration ban đầu trên các bảng đã tồn tại.

Model `Document` lưu ID UUID, tên gốc, tên lưu duy nhất, MIME thực tế, số byte,
trạng thái `uploaded`, thời điểm tạo và hạn lưu 41 ngày. `DocumentCreate` kiểm tra
metadata trước khi ghi; `DocumentRead` chỉ trả metadata công khai. Transaction
thất bại được rollback để session có thể dùng cho request tiếp theo.
