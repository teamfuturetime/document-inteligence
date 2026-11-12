# Repository audit — 2026-11-12

Scope: toàn bộ 16 nhánh remote sau fetch không prune, local branches/graph, source snapshots độc lập, GitHub REST đọc mới. Working tree ban đầu personal/canhtung-solo sạch tracked; `output/` BT3 untracked được giữ nguyên. Không đọc/copy `.env` hay dữ liệu upload thật. Worktree riêng cho consolidation; không ghi lên GitHub.

## Ý định và thực tế

Mục tiêu người dùng: một nền OCR hóa đơn local một người dùng (đã xác nhận qua lựa chọn trong phiên), một README và GitHub Flow. Auth/multi-user là giai đoạn sau. Không mặc định dùng solo và không bỏ đơn sinh viên/CCCD.

Thực tế: main 94c5101 chỉ README, 16 remote branches, 5 hướng implementation không cùng contracts. Không Issue/milestone; PR #1 nhatquang→main mở, PR #2 autosave→minhthao closed/merged. Main protection API 404, rulesets rỗng với quyền đọc admin. Hai workflows được Actions API liệt kê không chứng minh main có workflow; phải đọc tree và check-runs đúng SHA. [Inventory](branch-inventory.md) và [snapshot](evidence/github-snapshot.json) chứa SHA/CI/quan hệ cụ thể.

## Đối chiếu bằng source (không chấm bằng số commit/README)

Ký hiệu: **Code** = đã đọc mã; **Offline** = đã chạy test local với doubles/SQLite; **Native** = OCR thật được chạy riêng; **Remote** = CI thành công đúng head SHA; **Chưa** = chưa chạy trong đợt khảo sát. Test counts giữa các implementation không phải thước đo xếp hạng chất lượng.

| Trục | nhatquang a03ea30 | canhtung-main 61a31ab / solo c884a0b | minhthao 760ccdc | congtri 66074f4 | tuannguyen 5206769 |
|---|---|---|---|---|---|
| Upload formats | Code/API: PNG/JPEG 1 trang, 5MiB/16M pixels; PDF bị từ chối | Core PNG/JPEG/PDF 1 trang 10MiB/25M pixels; solo thêm app riêng, không persistence | Code: PDF/PNG/JPG/WebP/BMP/TIFF, multi-page; 10MB | Code: PDF/PNG/JPEG, 15MB; preprocess PDF từng trang | OCR CLI PNG/JPEG; không upload workflow |
| OCR/preprocess/limits | Subprocess image worker + native OCR vie+eng pinned hash; shared 30s deadline, bounded queue, không fallback | Core/solo: native pinned models, process deadline; OCR.space/VLM adapters chỉ solo, không suy từ mock | Tesseract/Paddle optional; multi-attempt/per-page OCR; backend gọi AI service qua HTTP timeout; chưa chứng minh total CPU budget | Native timeout45s/page; pipeline đồng bộ dù route trả202; PDF không có toàn-request budget đã chứng minh | Native CLI/model metadata; chưa nối extraction/API |
| Invoice schema/evidence/validation | 5 fields canonical; raw/normalized/evidence riêng; explicit null, strict requests, draft/final | Core 5 fields Pydantic schemas; evidence; solo 2 schemas/VLM validation, nguồn chuẩn khác | Dynamic fields theo classifier (invoice/CCCD/application); reviewed fields khác raw; OCR correction CAS | Invoice customer/payment_recipient/total_amount/date khác canonical; source_text/boxes; confirm không giống final invoice schema | Strict sales_invoice + normalization/policy, chưa HTTP |
| Review→confirm→export | SQLite latest revision/run; server validates persisted state; export không tin client final JSON | Core browser export từ validated values, không DB; solo server validate/export nhưng state do client gửi | Persisted review/confirmed export, reopen; auth integration tests | Review/confirm DB; export phía client từ extraction, thiếu chuẩn latest revision CAS | Chưa full UI/API workflow |
| Persistence/conflicts/autosave | SQLite migrations, immutable runs, restart/backup/lock, transaction revision CAS; save draft thủ công | Core/solo không persistence; browser state, không autosave server | PostgreSQL/Alembic; tests SQLite; OCR autosave expected_revision, nhưng không cùng field contract Quang | SQLAlchemy PostgreSQL/SQLite; state claims và transaction; không versioned review history như Quang | Chưa persistence |
| Auth | Không; loopback/single-user | Không | Sessions HttpOnly + CSRF + ownership có mã/tests | Shared API key tùy chọn; UI chưa gửi key | Không |
| UI/CI/eval | React evidence/review/history; offline+native/contract tests; CI a03ea30 xanh; dataset150, stored native predictions | Hai apps ở solo; CI exact heads xanh; core30 invoices/solo dataset riêng; không chuyển metric chéo | React dashboard/autosave; không workflow ở tip; extraction/auth tests có doubles | React UI; backend/frontend CI tip xanh (mock OCR); evaluation formulas, chưa golden benchmark đủ | Frontend landing + fixture benchmark; không VLM thật đã xác minh |

Evidence source cụ thể trên từng SHA: nhatquang `backend/src/docintel/{api/documents.py,services/documents.py,repositories/sqlite.py}`, `pipeline/src/document_pipeline/{service.py,image_worker.py,tesseract.py}`, `backend/tests/test_product.py`; Tùng `backend/src/document_backend/api/extract.py`, `schemas/src/document_contracts/models.py`, `solo/backend/src/ai02_solo`; Thao `backend/app/{api/auth.py,services/documents.py,repositories/documents.py}`, `ai_service/ocr/engine.py`, `tests/integration/test_auth_ownership.py`; Trí `backend/app/api/documents.py`, `ai_service/ocr/engines.py`, `tests/e2e/test_document_workflow.py`; Tuấn `backend/app/{services/pipeline.py,providers/tesseract.py}`. Đường dẫn ngoài nền chọn được truy cập bằng `git show <SHA>:<path>`, không copy toàn ứng dụng vào archive.

## Kiểm thử đối chiếu đã chạy trước thay đổi

| Checkout / lệnh | Kết quả thực tế | Phạm vi |
|---|---|---|
| nhatquang: uv sync --project backend --locked; pytest backend/tests pipeline/tests -q | 74 passed /7.00s; Python3.14.5. ruff/format đạt; contracts25, data6 fixtures+150parents đạt | Offline doubles; không gọi đây là OCR thật |
| canhtung-main: uv sync --locked; pytest -q; backend.export_schemas --check | 253 passed,14 skipped /11.34s; schema check đạt; Python3.14.5 | Native integration không bật nên skip; không dùng để nói OCR đạt |
| congtri: venv Python3.12.11 + requirements-dev; pytest -q | 99 tests hoàn tất exit0, dependency warnings | SQLite/mock pipeline; native chưa chạy đợt này |
| minhthao: venv Python3.12.11 + backend/requirements.txt + requirements-dev + ai_service/requirements.txt; pytest -q | 295 passed,1 failed /23.53s | Test storage Windows absolute path trên macOS: FileNotFoundError thay StorageSecurityError. Auth/ownership tests có trong suite; không chứng minh PostgreSQL thật |

Môi trường chỉ cài test-dev+AI requirements ban đầu thiếu SQLAlchemy ở minhthao; bổ sung đúng backend requirements rồi chạy toàn suite, không sửa test hay implementation để che lỗi. Đây là setup gap, khác lỗi storage còn lại. Archive snapshots không có `.git` làm evaluator fixture cần `git rev-parse` fail; chuyển sang worktree thật, không kết luận đó là lỗi evaluator. npm lần đầu bị sandbox DNS và runtime26 không đúng pin24; chuẩn bị runtime riêng/cài đúng và ghi kết quả tiếp tại [verification](consolidation-verification.md).

## Quyết định và hạn chế

Chọn nhatquang theo [ADR](decisions/0008-primary-invoice-platform.md): phù hợp local, có domain persisted authority và native CPU không cần service/secret. Chưa tích hợp auth, PDF, autosave từ nhánh khác; không nói chúng đã mất hoặc đã port. [Migration](consolidation-plan.md), [bài tập](../homework/README.md), [lịch sử/lineage](ml/source-lineage.md).

UI của nền chọn có fix polling retry và upload retry ở a03ea30; không merge ngược UI VT-042 cũ. Hai production retry files giống VT-042 là bằng chứng nội dung được giữ nhưng không giả nhận commit ancestry. Không đổi dataset/ground truth/model/config/threshold để làm checks xanh. Native/API/browser/live evaluation/clean install kết quả cuối được ghi riêng với runtime+SHA, không mang số 0.9667 của core Tùng sang nền này.

## Kết luận sau clean verification

Nền chọn tại a1ba2c6 đã được cài từ checkout sạch và đạt103 backend/pipeline tests,12 component tests,14 native HTTP checks và1 Chromium E2E. [Verification](consolidation-verification.md) ghi kết quả/per-schema metrics/commit chính xác. Solo chỉ đối chiếu code và exact-head remote CI trong đợt này, không chạy lại VLM/OCR.space thật và không coi adapter/mock là live provider. Main/PR#1 được API GET xác minh lần cuối vẫn94c5101/unprotected và a03ea30/open. Chưa ghi lên GitHub.
