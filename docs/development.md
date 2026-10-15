# Phát triển local

Chạy từ root repository trên macOS/Linux. Python ≥ 3.11, uv; đã kiểm tra
Python 3.13.14. Frontend Node 26.5.0/npm 11.17.0; engines trong package.json.
Backend chạy loopback, không database hoặc cloud service.

```bash
uv sync --locked
.venv/bin/python -m document_pipeline.ocr_models --directory data/models/tessdata
.venv/bin/python -m uvicorn document_backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Cần Tesseract 5 trên PATH. Model installer cần mạng lần đầu; model đã pin được
lưu trong data/models đã ignore, không thay model hệ thống. Model/hash lỗi thì
OCR không sẵn sàng. Backend real mặc định; `VDI_MODE=mock` chọn fixed fixture
rõ ràng, không suy từ upload. `VDI_TESSDATA_DIR` override model directory.

```bash
curl --fail http://127.0.0.1:8000/health
# Terminal khác:
cd frontend
npm ci
npm run dev
```

Vite 5173 proxy /health và /api tới 8000; tùy chọn VDI_BACKEND_URL đổi target
cho dev/tests. Production hosting cần reverse proxy cùng origin; chưa deploy.

## Ranh giới package

Workspace uv gồm contracts/backend/pipeline/evaluation, src layout, editable.
Models từ `document_contracts.models`, không chỉnh sys.path hoặc sửa generated
schema/TS bằng tay. Root không phải service. Lockfiles là nguồn versions;
không commit .venv/node_modules/uploads/model binaries/runtime reports.

```text
backend → pipeline → contracts
evaluation → pipeline + contracts
frontend → HTTP + generated JSON Schema/TS
```

API: /health; POST /api/v1/extract multipart một file; POST /api/v1/validate
raw reviewed strings/null. Swagger ở /docs. Extract dùng process group riêng,
30s processing deadline và 30s nhận upload riêng; timeout dừng toàn bộ child
processes. Upload không được lưu. Error envelope không chứa raw exception/path.

Xem [real pipeline](real-pipeline.md), [preprocessing](preprocessing.md),
[OCR](ocr.md), [extraction](extraction.md), [validation](review-validation.md),
[review/export](review-export.md) và [evaluation](evaluation.md).

## Kiểm tra

```bash
.venv/bin/python -m backend.export_schemas --check
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest --run-ocr --tessdata-dir=data/models/tessdata -q
```

Lệnh đầu pytest không yêu cầu engine; native integration skip rõ. Lệnh sau
bắt buộc model/engine, gồm API thật và golden regression. Thiếu prerequisites
sẽ fail. Frontend: npm test; npm run build; npx playwright install chromium;
npm run test:e2e. Playwright tự chạy/dừng server test ở 18000/15173, không
reuse hoặc dừng server của bạn. Xem [evidence cuối](completion.md).
