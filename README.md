# Vietnamese Document Intelligence — AI-02

Ứng dụng local cho hóa đơn tiếng Việt: upload → OCR thật → trích xuất năm
trường → review/chỉnh sửa → validation → tải JSON đã xác nhận.

## Trạng thái

Phần triển khai Phase 0–7 đã có trên nhánh cá nhân `personal/canhtung-main`.
Backend mặc định real; mock chỉ dùng khi đặt `VDI_MODE=mock`. Model Tesseract
vie/eng được pin commit/SHA-256. Không database, login hoặc cloud deployment.

Golden synthetic v1 gồm 30 hóa đơn độc lập, 18 dev/12 test. Lượt local trên
Tesseract 5.5.2 đạt macro exact match **0,9667** trên test (mục tiêu ≥ 0,85).
Đây là dataset nhỏ gồm ba template, chưa đại diện hóa đơn thực tế. Review
độc lập ground truth/PR và GitHub CI của các thay đổi mới còn pending.
Xem [evidence và trạng thái bàn giao](docs/completion.md).

## Chạy thử

macOS/Linux, Python ≥ 3.11, uv, Node theo `frontend/package.json`, Tesseract 5.
Chạy từ repository root:

```bash
uv sync --locked
.venv/bin/python -m document_pipeline.ocr_models --directory data/models/tessdata
.venv/bin/python -m uvicorn document_backend.main:app --host 127.0.0.1 --port 8000
```

Terminal khác:

```bash
cd frontend
npm ci
npm run dev
```

Mở http://127.0.0.1:5173/. Chọn `data/samples/synthetic-001.png` (hoặc JPG/PDF),
bấm **Trích xuất hóa đơn**, đối chiếu/sửa giá trị, bấm **Kiểm tra dữ liệu** rồi
**Xuất JSON đã xác nhận**. Sample `synthetic-002-missing.png` cần bổ sung tiền tệ.
Health real khi model/engine hợp lệ: `{"status":"ok","mode":"real","ocr_ready":true}`.
Thiếu engine/model trả 503 khi extract, không fallback mock.

Xem [demo và troubleshooting](docs/final-demo.md), [phát triển](docs/development.md),
[nhánh cá nhân](docs/personal-integration.md) và [CI](docs/ci.md).

## Kiểm tra

```bash
.venv/bin/python -m backend.export_schemas --check
.venv/bin/python -m pytest --run-ocr --tessdata-dir=data/models/tessdata -q
.venv/bin/python -m document_evaluation.cli --tessdata-dir data/models/tessdata --split test --output evaluation/reports/test.json --check
cd frontend
npm test
npm run build
npx playwright install chromium
npm run test:e2e
```

Pytest không có `--run-ocr` skip rõ các native integration tests. Browser E2E
chạy backend thật ở 18000 và Vite ở 15173, không reuse server đang mở.

## Phạm vi và cấu trúc

PNG/JPEG/PDF đúng một trang, tối đa 10 MiB/25M pixel, hóa đơn in synthetic.
Năm trường: số hóa đơn, ngày, bên bán, tổng tiền integer VND và tiền tệ.
Null khi missing/invalid/ambiguous; confidence heuristic có evidence, không
phải xác suất đã hiệu chuẩn. Chưa hỗ trợ handwritten, line items, multi-page,
nhiều cột hoặc nhãn/giá trị khác dòng; không tự sửa dấu sai từ OCR.

| Module | Vai trò |
| --- | --- |
| `frontend/` | React/TypeScript/Vite; preview, review, validation và JSON export |
| `backend/` | FastAPI; upload limits, pipeline deadline, health và validation |
| `pipeline/` | Preprocessing, Tesseract adapter, rules và bounded runner |
| `schemas/` | Pydantic contracts, JSON Schema và TypeScript generated types |
| `evaluation/` | Metrics, hash-verified dataset loader, CLI và regression |
| `data/` | Samples, golden synthetic/truth/manifest và generators |
| `docs/` | Kiến trúc, roadmap, giới hạn và evidence |
| `.github/` | CI, issue/PR templates |

Xem [kiến trúc](docs/architecture.md), [contract](docs/contracts.md),
[roadmap](docs/roadmap.md), [backlog](docs/issues.md),
[quy trình Git](docs/contributing.md). Main chung không được thay đổi tự động.
