# Phát triển Python local

Yêu cầu: Python ≥ 3.11 và uv. Chạy các lệnh từ root repository.
Workspace root không phải một service; nó điều phối bốn package có thể cài
editable: contracts trong `schemas/`, backend, pipeline, evaluation.

```bash
uv sync --locked
.venv/bin/python -m backend.export_schemas --check
.venv/bin/python -m pytest -q
```

## Chạy backend skeleton

```bash
.venv/bin/python -m uvicorn document_backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Mở `http://127.0.0.1:8000/docs` để xem endpoint đã triển khai. Ở terminal khác:

```bash
curl --fail http://127.0.0.1:8000/health
```

Kết quả: `{"status":"ok","mode":"mock","ocr_ready":false}`.
`status=ok` chỉ là service đang hoạt động, không phải OCR readiness. Skeleton
đã có `/api/v1/extract` với fixed mock demo; `/api/v1/validate` vẫn nhận 404.
Upload kiểm tra file thật rồi trả dữ liệu mẫu, chưa chạy OCR. Giới hạn/deadline
đã áp dụng và phần chưa triển khai xem [mock demo](mock-demo.md).

`create_app()` tạo app độc lập cho mỗi test. Router health tách khỏi app factory;
models dùng chung không import FastAPI. Handler RequestValidationError dùng
422 `invalid_request` theo contract, lỗi server dùng 500 `internal_error`, không
echo input/exception cho client. Các test request validation dùng route test-only;
chúng không xuất hiện trong server thật hoặc OpenAPI.
404/405 cho route/method không tồn tại vẫn là lỗi routing mặc định của FastAPI;
envelope contract áp dụng cho lỗi xử lý/validation của endpoint đã khai báo.

FastAPI/Uvicorn chỉ được khai báo trong package backend; HTTPX2 chỉ thuộc dev
group phục vụ TestClient. Dependencies transitive được ghi hash/version trong
`uv.lock`. Kiểm thử schema/export không đổi contract v1.0.0.

`uv.lock` là nguồn phiên bản dependencies cho workspace. `--locked` báo lỗi
nếu lockfile không còn khớp pyproject thay vì âm thầm resolve bản khác. Không
commit `.venv/`, build artifacts hay uploads. Khi thay dependency, cập nhật
pyproject + lockfile cùng atomic change, review diff và kiểm tra lại.

Package sử dụng src-layout để phát hiện thiếu cài đặt thay vì vô tình import
được do đang đứng ở repository root. Các lệnh export/test Phase 1 vẫn chạy
được từ root sau `uv sync`; shim `backend.app.models.contracts` giữ import cũ,
code mới import trực tiếp `document_contracts.models`.

Dependency direction:

```text
document-backend → document-pipeline → document-contracts
       └──────────────────────────────→ document-contracts
document-evaluation → document-pipeline + document-contracts
```

Pipeline hiện có preprocessing chạy trong subprocess; xem [preprocessing.md](preprocessing.md)
để thử PNG/JPEG/PDF và đọc metadata. Chưa có OCR, extraction,
metrics hoặc CLI chạy evaluation. Package import thành công không có nghĩa
chức năng AI đã được thực hiện. `data/requirements-samples.txt` là công cụ tạo
mẫu tùy chọn, không phải dependency server. Không cần font/generator để dùng
fixtures đã commit.

## Evidence P2-01

Đã kiểm tra ngày 2026-10-14 trên macOS ARM64, Python 3.13.14:

- `python -m pytest -q`: 65 tests pass, không warning.
- `python -m backend.export_schemas --check`: 9 schema không drift.
- Cài theo lockfile trong bản sao source với `.venv` mới: thành công; 8 API
  tests và schema check pass trong môi trường đó.
- Uvicorn chạy trên loopback; `GET /health` qua HTTP thực trả 200 và payload
  đúng contract. Server đã được dừng sau smoke check.

Đây là verification local, chưa phải GitHub CI, deployment hay test OCR thật.

## Frontend P2-02

Trong terminal riêng chạy `cd frontend`, `npm ci`, `npm run dev`. Backend vẫn
chạy cổng 8000, Vite chạy 5173 và proxy `/health` để không cần CORS cho dev.
`npm test` hiện chạy 30 Vitest cases; `npm run build` kiểm tra 9 generated contracts,
typecheck và tạo static assets. Xem [frontend README](../frontend/README.md).

UI hiện upload tài liệu và hiển thị fixed mock response, chưa xử lý OCR.
HTTP smoke check proxy đã pass; visual QA trình duyệt chưa thực hiện vì phiên
làm việc không có browser connector. Chưa chạy GitHub CI hoặc deploy website.

## Evidence P2-03

Backend/data 85 tests pass không warning; frontend 30 tests pass; schema drift,
generated TS, typecheck và build pass. HTTP smoke test qua Vite proxy cho PNG,
JPG và PDF trả 200/mock; file giả trả 415 đúng contract. Server tạm đã được
dừng sau kiểm tra. Xem [mock-demo.md](mock-demo.md) để chạy lại và hiểu giới hạn.

Tham khảo [uv workspaces](https://docs.astral.sh/uv/concepts/projects/workspaces/)
và [locking/sync](https://docs.astral.sh/uv/concepts/projects/sync/);
[FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/)
và [error handling](https://fastapi.tiangolo.com/tutorial/handling-errors/).
