# Phát triển Python local

Yêu cầu: Python ≥ 3.11 và uv. Chạy các lệnh từ root repository.
Workspace root không phải một service; nó điều phối bốn package có thể cài
editable: contracts trong `schemas/`, backend, pipeline, evaluation.

```bash
uv sync --locked
.venv/bin/python -m backend.export_schemas --check
.venv/bin/python -m pytest -q
```

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

Tham khảo [uv workspaces](https://docs.astral.sh/uv/concepts/projects/workspaces/)
và [locking/sync](https://docs.astral.sh/uv/concepts/projects/sync/).
