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
chưa có `/api/v1/extract` hoặc `/api/v1/validate`; gọi chúng hiện nhận 404.
Trạng thái mock không có nghĩa luồng extraction demo đã hoạt động.
Không có file upload, giới hạn decode hoặc deadline pipeline nào được thực thi
trong task health này; những phần đó thuộc các endpoint/pipeline tiếp theo.

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

Pipeline/evaluation hiện chỉ có package boundaries, chưa có OCR, extraction,
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

Tham khảo [uv workspaces](https://docs.astral.sh/uv/concepts/projects/workspaces/)
và [locking/sync](https://docs.astral.sh/uv/concepts/projects/sync/);
[FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/)
và [error handling](https://fastapi.tiangolo.com/tutorial/handling-errors/).
