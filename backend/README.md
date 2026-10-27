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

## Upload API

```bash
curl -X POST http://localhost:8000/api/v1/documents \
  -F 'file=@demo_documents/03_don_de_nghi.png;type=image/png'
```

Chọn đường dẫn tới tài liệu có thật trên máy. Endpoint nhận `multipart/form-data`
với trường bắt buộc `file`; trả `201` và metadata gồm `id`, `original_name`,
`mime_type`, `size_bytes`, `status`, `document_type`, `created_at`, `expires_at`.
Tên lưu là UUID để các upload trùng tên không ghi đè nhau. Lưu file bằng rename
nguyên tử, dọn file tạm khi ghi thất bại và xóa file đã lưu nếu transaction lỗi.

| API | Kết quả |
|---|---|
| `GET /api/v1/documents` | Danh sách metadata và tổng số tài liệu |
| `GET /api/v1/documents/{id}` | Metadata tài liệu vừa upload |
| `GET /api/v1/documents/{id}/content` | Nội dung gốc |

Lỗi dùng JSON `{"detail": "..."}`: `422` khi input không hợp lệ, `500` khi
không ghi được file, `503` khi database không lưu được metadata. Nếu bật API key,
thêm `-H 'X-API-Key: <giá trị đã cấu hình>'` vào lệnh curl.

## Validation

- Chỉ nhận PDF, PNG, JPG/JPEG; phần mở rộng không phân biệt chữ hoa/thường.
- Kiểm tra dung lượng trước khi giải mã; chỉ đọc tối đa giới hạn cộng 1 byte.
- So khớp chữ ký, phần mở rộng và MIME do client khai báo. MIME trống hoặc
  `application/octet-stream` được nhận diện bằng nội dung thực tế.
- PDF phải có cấu trúc đọc được, có trang, kết thúc đầy đủ và không yêu cầu
  mật khẩu; không nhận file mà trình đọc phải sửa cấu trúc.
- Ảnh phải qua cả kiểm tra cấu trúc và giải mã pixel, tối đa 40 triệu pixel.
- Từ chối file rỗng, tên rỗng, tên vượt 255 ký tự và ký tự điều khiển. Tên có
  đường dẫn được lấy basename cho cả dấu `/` và `\\`.
- Input bị từ chối không tạo metadata hoặc file trong thư mục lưu trữ.

## Kiểm thử và nghiệm thu tuần 1

```bash
# Toàn bộ dự án
python -m pytest

# Riêng nền tảng backend và Upload API
python -m pytest \
  tests/unit/test_config.py \
  tests/unit/test_database.py \
  tests/unit/test_document_repository.py \
  tests/unit/test_storage.py \
  tests/unit/test_file_validation.py \
  tests/integration/test_documents_api.py
```

Các test tự tạo PDF/PNG/JPEG thật trong bộ nhớ, dùng database SQLite và thư mục
lưu file tạm; không cần OCR hoặc PostgreSQL chạy bên ngoài. Integration test
chạy lifespan để kiểm tra tạo bảng, gọi upload, đọc metadata và tải lại đúng
nội dung đã lưu. Các trường hợp thất bại kiểm tra cả HTTP response lẫn việc
không còn metadata/file thừa; unit test mô phỏng lỗi ghi file, rename, refresh
và commit để kiểm tra rollback và dọn dẹp.

Nghiệm thu: `/health` trả `200`; migration chạy được; PDF/PNG/JPEG hợp lệ trả
`201`; input không hợp lệ trả `422`; metadata và nội dung lưu đọc lại được.
