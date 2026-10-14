# Vietnamese Document Intelligence — AI-02

Ứng dụng web phục vụ nhóm 5 người: upload hóa đơn tiếng Việt, OCR, trích xuất
dữ liệu có cấu trúc, review/chỉnh sửa, validation và xuất JSON.

## Trạng thái

Phase 0 và baseline Phase 1 đã hoàn thành local: cấu trúc, tài liệu, quyết định
MVP, Pydantic contracts v1.0.0, JSON Schema/fixtures và mẫu synthetic.
P2-01 đã có Python workspace/lockfile và FastAPI skeleton với `GET /health`.
Chưa có frontend, upload API, OCR, extraction service hoặc CI GitHub.
Fixtures mock là dữ liệu kiểm thử, chưa phải luồng upload/demo hoạt động.
Review nhóm/PR và golden dataset vẫn chưa hoàn thành.

## Phạm vi MVP đề xuất

- Hóa đơn bán hàng tổng hợp dạng in; một tài liệu mỗi lần.
- PNG/JPG và PDF một trang; dữ liệu hoàn toàn synthetic.
- Trích xuất số hóa đơn, ngày, tên bên bán, tổng tiền và tiền tệ VND.
- Mỗi trường có giá trị, confidence và nguồn OCR; không tìm thấy thì trả null.
- Review trên trình duyệt, sửa giá trị, validation và tải JSON đã xác nhận.
- Golden dataset có ground truth, đánh giá từng trường, taxonomy lỗi,
  version cấu hình và hướng dẫn tái lập.

Chưa đưa vào MVP: chữ viết tay, bảng chi tiết sản phẩm, PDF nhiều trang,
biểu mẫu tùy ý, database, authentication, microservices và cloud.

## Bắt đầu

1. Đọc [kiến trúc và MVP](docs/architecture.md), [quyết định phạm vi](docs/decisions/001-invoice-mvp.md)
   và [contract v1.0.0](docs/contracts.md).
2. Đọc [roadmap](docs/roadmap.md) và [backlog issue](docs/issues.md).
3. Làm theo [quy trình Git và task đầu tiên](docs/contributing.md).

Chạy backend và kiểm tra từ root repository:

```bash
uv sync --locked
.venv/bin/python -m backend.export_schemas --check
.venv/bin/python -m pytest -q
.venv/bin/python -m uvicorn document_backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Python ≥ 3.11 và uv. Xem `http://127.0.0.1:8000/docs` hoặc gọi `/health`:
`{"status":"ok","mode":"mock","ocr_ready":false}`.
Chi tiết đóng gói, cài dependencies và trạng thái endpoint tại
[hướng dẫn phát triển](docs/development.md). Frontend/mock upload demo chưa có.

## Cấu trúc

| Thư mục | Vai trò |
| --- | --- |
| `frontend/` | React + TypeScript + Vite; upload, preview, review, export |
| `backend/` | FastAPI, Pydantic; HTTP API, điều phối và validation |
| `pipeline/` | Python; preprocessing, adapter OCR và extraction độc lập |
| `schemas/` | JSON Schema/fixtures dùng chung, quản lý phiên bản contract |
| `evaluation/` | CLI evaluation, metrics và taxonomy lỗi |
| `data/` | Mẫu synthetic, ground truth, manifest và chia tập |
| `docs/` | Kiến trúc, kế hoạch và hướng dẫn cộng tác |
| `.github/` | Template issue và pull request |

Tests đặt trong `frontend/src/`, `backend/tests/`, `pipeline/tests/` và
`evaluation/tests/` khi triển khai. Không tạo package rỗng giả là code hoạt động.
