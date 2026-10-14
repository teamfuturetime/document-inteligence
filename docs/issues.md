# Backlog sẵn để tạo GitHub Issues

Đây là backlog local, chưa tạo issue trên GitHub. ID `P*-*` là mã kế hoạch,
không phải số issue GitHub. Khi publish issue, thay dependency bằng link thực.
Mỗi dòng là một issue độc lập; dùng title nguyên văn, đưa mục tiêu/test vào
template task, ghi owner và dependencies. Acceptance và test chi tiết bổ sung
từ [roadmap](roadmap.md) của phase tương ứng.

| ID / Title | Owner | Depends on | Acceptance / evidence tối thiểu |
| --- | --- | --- | --- |
| P0-01 — Initialize project overview and ignore rules | Lead | Repo audit | README nêu trạng thái; check ignore secrets/artifacts và giữ lockfile |
| P0-02 — Document MVP and monorepo architecture | Lead | P0-01 | Ownership/module boundary, MVP có giới hạn; review kiến trúc |
| P0-03 — Plan roadmap and issue dependencies | Lead | P0-02 | Mọi phase có owner/AC/test/commit; xác định việc song song |
| P0-04 — Add Git guide and issue/PR templates | Lead | P0-03 | Hướng dẫn staging/commit/PR; template có evidence và reviewer |
| P1-01 — Agree invoice MVP and acceptance targets | Lead + cả nhóm | P0-04 | Chốt loại hóa đơn, năm field, file limits, target; ghi quyết định |
| P1-02 — Define versioned schema and API/OCR contracts | Backend | P1-01 | Pydantic/JSON Schema, fixture success/missing/error, TS strategy; fixture tests |
| P1-03 — Add initial synthetic document samples | OCR + Extraction | P1-01 | PNG/JPG/PDF và ground truth; review chéo, không PII |
| P2-01 — Initialize FastAPI and Python packages | Backend + Lead | P1-02 | Health chạy được, dependency pins, cài package local; pytest |
| P2-02 — Initialize Vite React frontend | Frontend | P1-02 | API client, upload states; typecheck/build/Vitest |
| P2-03 — Implement explicit mock extraction demo | Backend + Frontend | P2-01, P2-02, P1-03 | Upload → fixture đúng schema, UI gắn nhãn mock; API + smoke tests |
| P2-04 — Add backend/frontend CI checks | Lead | P2-01, P2-02 | Workflow chạy tests/typecheck/build thực; lưu evidence run GitHub |
| P3-01 — Decode and preprocess supported documents | OCR | P2-01, P1-03 | Decode/transform, một trang, giới hạn; tests corrupt/PDF đa trang |
| P3-02 — Implement Vietnamese OCR adapter | OCR | P3-01, P1-02 | Text/token/box/confidence/version; integration engine thật và lỗi engine missing |
| P4-01 — Extract invoice fields with versioned rules | Extraction | P1-02, P2-01 | Mapping năm field/missing/ambiguity; unit tests OCR fixtures |
| P4-02 — Validate and normalize reviewed values | Backend | P1-02, P2-01 | Field errors, ISO/date calendar, VND integer; boundary tests |
| P4-03 — Connect API to the real OCR/extraction pipeline | Backend + Lead | P3-02, P4-01, P4-02 | Timeout/cleanup/error handling; real sample integration, không fallback mock |
| P5-01 — Preview documents and edit extracted fields | Frontend | P2-03 | PNG/JPG/PDF preview, editable Unicode values; interaction tests |
| P5-02 — Validate edits and export reviewed JSON | Frontend | P5-01, P4-02 | Block invalid/stale validation; export normalized data + provenance; tests |
| P6-01 — Build versioned golden dataset and manifest | OCR + Extraction | P1-03, P1-02 | 30 mẫu, fixed split/hash, reviewed ground truth; integrity checks |
| P6-02 — Implement reproducible field-level evaluation | Extraction | P4-03, P6-01 | Exact match/PRF/null policy/taxonomy + version report; hand-computed tests |
| P6-03 — Add pipeline golden regression tests | Extraction + Lead | P6-02 | Baseline report, threshold theo quyết định P1-01; repeatability checks |
| P7-01 — Verify end-to-end flow and fix integration defects | Lead + cả nhóm | P4-03, P5-02, P6-03 | Ba định dạng + lỗi + JSON; smoke evidence, mỗi bug issue/PR riêng |
| P7-02 — Document reproducible setup and final demo | Lead + cả nhóm | P7-01 | Người khác chạy theo docs; report thật, limitations, mock status rõ |

## Nhãn và milestones đề xuất

- Type: `feature`, `bug`, `documentation`, `test`, `chore`.
- Area: `frontend`, `backend`, `ocr`, `extraction`, `evaluation`, `integration`.
- Status: dùng GitHub Project hoặc checklist, không cần nhiều branch dài hạn.
- Milestones: Phase 0–7. Mỗi issue một assignee chính; người hỗ trợ là reviewer.

## Definition of ready / done

Ready: owner, dependencies, interface, acceptance và test evidence cần có rõ.
Done: acceptance được chứng minh, tests đã chạy, docs/status cập nhật,
PR được một người khác review, CI pass và merge theo quyền nhóm.
Commit local chưa đồng nghĩa issue Done trên GitHub.

P0-01–P0-04 được thực hiện local trên `chore/project-bootstrap`; chưa có PR,
review ngoài tác giả hoặc CI GitHub.

P1-01–P1-03 được thực hiện local trên `feat/phase1-contracts`, kế thừa bootstrap
chưa merge: ADR scope, contract/models/schema/fixtures/tests, samples synthetic
và manifest. Ground truth review độc lập còn pending; chưa có API/OCR service,
PR, CI run hoặc issue GitHub.

P2-01 hoàn thành local trên `feat/backend-skeleton`: workspace/package editable,
models shared độc lập backend, lockfile, FastAPI health và error handlers, tests
và hướng dẫn chạy. Pipeline/evaluation chỉ có package boundaries chưa có logic.
Backend skeleton đã push lên `origin/feat/backend-skeleton`, chưa merge hoặc
chạy CI GitHub.

P2-02 hoàn thành local trên `feat/frontend-skeleton`: React/TS/Vite, npm lockfile,
9 generated contracts, health API client/runtime validation, file selection,
trạng thái idle/loading/success/error và tests/build. Browser visual QA chưa
thực hiện do không có browser connector. P2-03–P2-04 và Phase 3 trở đi chưa
triển khai; upload/extraction/review/export chưa hoạt động.
