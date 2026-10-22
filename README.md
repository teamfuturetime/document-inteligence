# Document Intelligence cho biểu mẫu tiếng Việt

Ứng dụng mẫu xử lý PDF/ảnh tiếng Việt theo luồng upload → tiền xử lý → OCR →
phân loại theo luật → trích xuất → người dùng rà soát và xác nhận. Repository
hiện có backend FastAPI, AI service FastAPI, PostgreSQL và local file storage.
Frontend chưa có source code thực thi (thư mục chỉ có Dockerfile), vì vậy không
được đưa vào Compose ở trạng thái hiện tại.

## Kiến trúc và công nghệ

```text
Client → Backend API → Application Service → Repository → PostgreSQL
                     ├→ StorageService → local volume
                     └→ AI Service → preprocessing → Tesseract → rules
```

- Python 3.12, FastAPI, Pydantic, SQLAlchemy 2, Alembic, PostgreSQL 16.
- OpenCV, PyMuPDF và Tesseract OCR với gói ngôn ngữ `vie`.
- Pytest cho unit test. Chưa có E2E thực chạy trên toàn bộ container.

Thiết kế chi tiết: [docs/architecture.md](docs/architecture.md). API:
[docs/api.md](docs/api.md).

## Cấu trúc thực tế

```text
backend/app/{api,core,models,repositories,schemas,services}/
backend/migrations/             # schema Alembic
ai_service/{ocr,preprocessing,classification,extraction}/
ai_service/main.py              # GET /health, POST /process
tests/unit/                     # unit/API tests có mock
tests/integration/              # hiện chưa có test case
tests/e2e/                      # hiện chưa có test case
docs/
docker-compose.yml
```

## Cài đặt local

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt -r backend/requirements-dev.txt
pip install -r ai_service/requirements.txt
copy .env.example .env
```

Local cần PostgreSQL và Tesseract có language pack tiếng Việt. Khởi tạo DB và
chạy hai service (hai terminal):

```bash
cd backend
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# từ thư mục repository
uvicorn ai_service.main:app --reload --port 8001
```

Các biến quan trọng: `DATABASE_URL`, `AI_SERVICE_URL`, `OCR_ENGINE`,
`OCR_LANG`, `MAX_UPLOAD_SIZE_MB`, `STORAGE_PATH`, `DATA_RETENTION_DAYS`,
`CLASSIFICATION_REVIEW_THRESHOLD`. Xem toàn bộ mẫu ở `.env.example`.

## Docker

```bash
docker compose up --build
```

Compose khởi động `db`, `ai_service`, `backend`; backend tự chạy migration sau
khi PostgreSQL và AI service healthy. API ở `http://localhost:8000/docs` và AI
service ở `http://localhost:8001/health`. Source frontend chưa tồn tại nên chưa
có container frontend hợp lệ.

## API và kiểm thử

Backend cung cấp `/api/v1/documents` cho upload/list/detail/process/extraction/
review/confirm/delete. File tối đa mặc định 10 MB; chỉ PDF, PNG, JPEG có magic
bytes hợp lệ được nhận.

```powershell
$env:DEBUG='false'  # chỉ cần nếu máy đang có DEBUG=release
python -m pytest -q
python -m compileall -q backend ai_service tests
```

Dọn dữ liệu hết hạn bằng cron hoặc Task Scheduler:

```bash
cd backend
python -m app.retention_cli
```

## Trạng thái và giới hạn

- Confidence phân loại là heuristic 0–100, không phải xác suất/accuracy đã hiệu chuẩn.
- Chưa có dataset gán nhãn để đo accuracy, precision hoặc recall.
- Chưa có authentication/authorization; API chỉ phù hợp phát triển nội bộ và
  không được công bố Internet với dữ liệu thật.
- Local filesystem + DB dùng cơ chế bù trừ best-effort, không phải transaction phân tán.
- Chưa có frontend, rate limiting, antivirus, integration/E2E container test.
- Production cần reverse proxy giới hạn request body và TLS.

Nợ kỹ thuật được theo dõi tại [docs/technical-debt.md](docs/technical-debt.md),
kết quả đánh giá AI tại [docs/evaluation.md](docs/evaluation.md).
