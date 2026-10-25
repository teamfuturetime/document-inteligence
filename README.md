# AI-02 · Document Intelligence cho biểu mẫu tiếng Việt

Sản phẩm local **0.2.0 trên nhatquang**: tải ảnh → OCR thật → trích xuất có evidence → sửa/lưu nháp → xác nhận → xuất JSON từ backend. Hỗ trợ hóa đơn header/tổng tiền (5 trường) và đơn đề nghị đánh máy (7 trường). Chỉ dùng synthetic/sample hợp lệ.

| Phần | Implementation |
| --- | --- |
| OCR | Tesseract 5 vie+eng, models pin SHA256, native process có timeout; không fallback mock |
| Extraction/confidence | Nhãn/multiline/candidates, raw/normalized/evidence riêng, abstain; confidence heuristic chưa calibrated |
| Upload/storage | PNG/JPG một trang, kiểm format thật/bytes/pixels, preview chuẩn EXIF |
| Persistence/worker | SQLite migrations, queue bounded, immutable runs, restart recovery và process lock |
| Review | Draft cho missing/invalid, giữ xóa-null, kiểm revision trong transaction, stale trả 409 |
| Confirm/export | JSON từ latest persisted confirmed revision; không tin approved/final JSON client |
| Frontend | Đối chiếu ảnh/evidence, form edit, dirty-state guard, conflict compare, pagination/history |
| Evidence | 150 synthetic parent documents, splits/hashes, field metrics, errors, model/config/source versions |
| Fixture cũ | Catalogue riêng, chỉ khi bật explicit; không phải model benchmark |

Kết quả thực và pending checks: [báo cáo triển khai](docs/reports/product-verification-2026-10-24.md). Không suy chất lượng tài liệu thật hoặc khả năng public deployment từ tests/synthetic scores.

## Cài và chạy native

Runtime pins: Python 3.14.5, uv 0.12.22, Node 24.16.x, npm 11.13.x. Cần Tesseract 5 từ nguồn chính thức; không cần GPU hoặc API key.

```powershell
uv sync --project backend --locked
npm --prefix frontend ci
uv run --project backend --locked python scripts/fetch_ocr_models.py
```

Model helper tải khoảng 4.7 MB vie+eng đã pin vào runtime ngoài Git, không tải trong inference. Settings tìm Tesseract trên PATH hoặc vị trí Windows chuẩn; có thể override DOCINTEL_TESSERACT_EXECUTABLE bằng đường dẫn cài thật.

Nếu chưa có `.env`, sao chép `.env.example`. Nếu đã có, giữ các cấu hình riêng và chỉ đổi provider thành tesseract; không ghi đè secrets. Hoặc dùng biến trong terminal backend:

```powershell
$env:DOCINTEL_PROVIDER_MODE='tesseract'
uv run --project backend --locked uvicorn docintel.api.app:app --host 127.0.0.1 --port 8000
```

Terminal frontend:

```powershell
npm --prefix frontend run dev
```

Mở [ứng dụng](http://localhost:5173), chọn **Xử lý tài liệu**; [API docs](http://127.0.0.1:8000/docs). Dùng ảnh `data/product/images/hoa_don_007.png` để demo. Chạy một worker process cho mỗi runtime DB. Health chỉ xác nhận tiến trình; xem capabilities.ocr_ready trước upload.

Mặc định: 5 MiB, 16M pixels, một trang, deadline 30 giây, tối đa 5 queued/running runs. Chưa hỗ trợ PDF, chữ viết tay, line items, nhiều trang hoặc tài khoản. Fixture catalogue cần provider fixture, không tự bật khi OCR lỗi.

## Cấu trúc

```text
frontend/src/features/documents/     Upload/list/review/source/history/export UI
backend/src/docintel/
  api/                              HTTP routes, errors/request ID
  domain/                           Nguồn chuẩn contracts và validation
  services/                         Use cases, revisions/export, persisted worker
  repositories/                     SQLite transactions, migrations, worker lock
  storage/                          Source/preview bất biến, cleanup khi upload lỗi
  adapters/                         Pipeline → public domain; fixture adapter riêng
  evaluation/                       Metrics offline, không thuộc inference
pipeline/src/document_pipeline/     Image worker → OCR → extraction → confidence
contracts/                          Generated JSON Schema/OpenAPI/examples
configs/                            Config có version và mục đích rõ
data/                               Synthetic images/labels/manifests
scripts/                            Verify, evaluate, fetch models, backup/restore
docs/                               Requirements/ADR/architecture/runbook/reports
runtime/                            DB/uploads/models/cache/local reports; ignored
```

[Kiến trúc](docs/product/architecture.md), [runbook và demo](docs/product/runbook.md), [handoff tích hợp nhóm](docs/product/integration-handoff.md), [nguồn kế thừa](docs/ml/source-lineage.md). Public contracts sinh từ backend domain; không sửa generated files hoặc tạo schema frontend độc lập.

## Kiểm tra

```powershell
uv run --project backend --locked ruff check backend scripts pipeline
uv run --project backend --locked ruff format --check backend scripts pipeline
uv run --project backend --locked pytest backend/tests pipeline/tests -q
uv run --project backend --locked python scripts/generate_contracts.py --check
uv run --project backend --locked python scripts/check_data.py
uv run --project backend --locked python scripts/evaluate_fixtures.py
uv run --project backend --locked python scripts/check_repository.py
uv run --project backend --locked python scripts/verify_product.py
npm --prefix frontend run contracts:check
npm --prefix frontend run typecheck
npm --prefix frontend run lint
npm --prefix frontend run format:check
npm --prefix frontend test
npm --prefix frontend run build
```

Unit/component tests có doubles rõ ràng. verify_product thực sự chạy OCR và HTTP workflow, thiếu môi trường thì fail. Fixture evaluator chỉ kiểm công thức. Đánh giá model dùng prediction trước review:

```powershell
uv run --project backend --locked python scripts/evaluate_model.py --split development --output runtime/evaluation/dev-new-run
```

Output phải là thư mục mới; không ghi đè report cũ. Chọn policy trên development/validation, giữ test độc lập. [Dataset card](data/product/README.md), [protocol](docs/ml/evaluation-protocol.md) và [confidence](docs/ml/confidence-policy.md) nêu support/exclusions và giới hạn.

Đổi schema/API: chạy generate_contracts.py rồi `npm --prefix frontend run contracts:generate`; cập nhật versions/examples/tests/docs. Đổi data/model/rules/config phải cập nhật hashes và evidence, không sửa gold theo prediction.

## Vận hành và Git

`docker compose up --build` dựng backend/OCR cùng frontend, bind loopback, named volume giữ DB/uploads sau `docker compose down`. Không dùng `down -v` nếu cần dữ liệu. Docker và remote Actions phải kiểm riêng, không suy từ YAML. [Runbook](docs/product/runbook.md) có backup/restore kiểm hash và không ghi đè thư mục cũ.

Local/single-user, chưa có auth/multi-tenant; không expose công khai hoặc dùng hồ sơ thật. `.env`, DB/uploads/models/cache ở ngoài Git. Đọc [AGENTS](AGENTS.md), [scope](docs/requirements/scope.md), [contracts](contracts/README.md) và ADR trước khi sửa.

Lượt 24/10 triển khai cả sản phẩm trên nhatquang theo yêu cầu mới; chưa push/merge main hoặc đổi phần việc nhánh khác. [Foundation verification](docs/reports/foundation-verification.md) là snapshot lịch sử; [ADR 0007](docs/adr/0007-product-on-nhatquang.md) ghi phạm vi mới. [Kế hoạch 10 tuần](docs/planning/team-delivery-plan-2026-10-20.md) giữ cho nhóm tham chiếu. Người dùng tự review/commit/push.
