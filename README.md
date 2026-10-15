# Vietnamese Document Intelligence — AI-02

MVP xử lý biểu mẫu tiếng Việt của nhóm **SE2026-T11 – Future Time**. Hệ thống
nhận PDF/JPG/JPEG/PNG, tăng chất lượng ảnh, OCR tiếng Việt, phân loại biểu mẫu,
trích xuất JSON, cho phép người dùng so sánh với bản gốc, chỉnh sửa và xác nhận.

## Chạy nhanh bằng Docker

Yêu cầu Docker Desktop với Docker Compose:

```bash
cp .env.example .env
docker compose up --build
```

Mở giao diện tại <http://localhost:5173>, OpenAPI tại
<http://localhost:8000/docs>, health check tại <http://localhost:8000/health>.
Compose dùng PostgreSQL và volume riêng cho database/file. OCR mặc định là
`mock`: không bịa nội dung và trả kết quả rỗng để có thể demo luồng an toàn.

## Chạy phát triển và kiểm thử

Backend (Python 3.12):

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r backend/requirements-dev.txt
.venv/bin/pytest
PYTHONPATH=backend:. .venv/bin/uvicorn app.main:app --reload
```

Frontend (Node 22):

```bash
cd frontend
npm ci
npm run dev
npm run build
```

Để dùng PaddleOCR thật, cài `backend/requirements-ocr.txt` và PaddlePaddle phù
hợp CPU/GPU, sau đó đặt `OCR_ENGINE=paddle`. Lần đầu model sẽ cần được tải.

## Chức năng đã có

- Upload an toàn với giới hạn dung lượng và kiểm tra magic bytes.
- PDF render, deskew, denoise, CLAHE và adaptive threshold bằng PyMuPDF/OpenCV.
- Adapter PaddleOCR tiếng Việt, text/bounding box chuẩn hóa và Unicode NFC.
- Rule-based classification/extraction có schema Pydantic và version để audit.
- API upload, search/filter, process, lấy file/kết quả, sửa và xác nhận.
- React UI responsive cho upload, preview, review và lịch sử.
- PostgreSQL/SQLite, retention 41 ngày, Docker healthcheck và 2 API workers.
- Unit, integration, E2E và security tests; metric CER/WER/field F1.

## Cấu trúc

```text
frontend/       React + TypeScript + Tailwind
backend/        FastAPI + SQLAlchemy + Alembic
ai_service/     preprocessing, OCR, classification, extraction, evaluation
tests/          unit, integration, e2e
docs/           architecture, API, database, security, performance, demo
scripts/        development và retention utilities
```

## Bảo mật và cấu hình

Không commit `.env`. Đặt `API_KEY` ở production để khóa API tài liệu bằng header
`X-API-Key`; với web public nên dùng identity-aware gateway thay cho secret trong
browser. Log không chứa OCR text/PII. Xem [docs/security.md](docs/security.md).

## Trạng thái và giới hạn

Toàn bộ automated test và frontend build chạy đạt trên môi trường phát triển.
Chưa có dataset/ground truth hoặc Paddle model weights nên repository **không
công bố số liệu accuracy**. Mock OCR chỉ phục vụ kiểm thử orchestration. Mục tiêu
421 concurrent users là thiết kế/kịch bản test, chưa phải benchmark thực nghiệm.

Git cấm khoảng trắng trong branch name, vì vậy nhánh triển khai sử dụng tên
không dấu, không khoảng trắng là `congtri`.

## Tài liệu

- [Kiến trúc](docs/architecture.md) · [Pipeline](docs/pipeline.md)
- [Database](docs/database.md) · [API](docs/api.md)
- [AI và đánh giá](docs/ai-models.md) · [Evaluation](docs/evaluation.md)
- [Hiệu năng](docs/performance.md) · [Demo](docs/demo.md)
- [Báo cáo đóng góp](docs/contribution-report.md)
