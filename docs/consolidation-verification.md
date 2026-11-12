# Consolidation verification

## Baseline trước sửa production

Ngày 2026-11-12; nguồn Git nhatquang `a03ea309ada1480e537cb7de8936ad0d52d53698`, main `94c5101b94a43f1b0e2814d1cdfeee4139289673`. Worktree riêng, không copy `.env`/uploads/DB từ workspace cũ. Native data đều synthetic. Python3.14.5, Tesseract5.5.2, Pillow12.3.0, Pydantic2.13.5 trên macOS ARM64.

| Lệnh / kiểm tra | Kết quả |
|---|---|
| uv sync --project backend --locked | Cài sạch đúng backend/uv.lock; không đổi lock |
| pytest backend/tests pipeline/tests -q | 74 passed, 7.00s trên source snapshot chính xác SHA |
| ruff check / format --check | Pass, 59 files formatted |
| scripts/generate_contracts.py --check | 25 artifacts đạt |
| scripts/check_data.py | 6 fixture samples + 150 independent product parents đạt |
| scripts/fetch_ocr_models.py | vie/eng tải từ revision pin, SHA256 verified; runtime ignored |
| scripts/verify_product.py | 14 native HTTP checks đạt: upload/idempotency/OCR/evidence/draft/null/CAS409/confirm validation/export/reprocess/history/restart, cả invoice và đơn đề nghị |
| scripts/evaluate_model.py --split test --output runtime/audit/baseline-test | 30 mẫu; 176/176 present fields đúng; không đọc gold trong inference; score synthetic không đại diện ảnh thật |

[Baseline JSON](evidence/consolidation-baseline.json) lưu engine/model/config/source fingerprints và lệnh. Báo cáo gốc Windows Tesseract5.4 nằm tại evaluation/runs/2026-10-24-test-frozen; không overwrite và không coi hai engine là cùng một run.

## Checks sau consolidation

Checkout sạch riêng tại **a1ba2c6cf311a28cc5a717f096450159a9348423**, tạo bằng `git worktree add --detach`; không copy venv, node_modules, .env, models hoặc DB cũ. Chạy đúng README với Python3 (alias hệ điều hành), uv0.11.25 của host, Node24.16.0/npm11.13.0, Python backend3.14.5 và Tesseract5.5.2/macOS ARM64. Dependencies lấy theo lockfiles; Node/npm thử nghiệm được đặt riêng, không thay global toolchain. Sau đó chuẩn bị uv 0.12.22 riêng theo đúng pin README/CI và kiểm tra lại check/ocr/e2e trên cùng commit; kết quả giữ nguyên pass. Không nâng toolchain toàn máy.

| Lệnh từ root checkout sạch | Kết quả quan sát |
|---|---|
| python3 scripts/dev.py setup | Pass; tạo venv/node_modules mới, .env mẫu khi chưa có; không sửa tracked files |
| python3 scripts/dev.py models | Pass; vie531275 bytes + eng4113088 bytes; SHA256/revision pin verified |
| python3 scripts/dev.py check | **103 pytest passed /9.24s**, **12 Vitest passed /3 files**; Python lint/format, schema25 artifacts, data6 fixtures+150parents, frontend contracts/typecheck/lint/format/build đều pass |
| scripts/check_evaluation_regression.py (trong check) | Replay 30 frozen native predictions của Windows5.4: mọi metric/errors/support khớp baseline và hashes/membership/gold; **không inference mới** |
| python3 scripts/dev.py ocr | **14 native HTTP checks pass**; invoice+đơn đề nghị, missing/null/invalid confirm, CAS409, history/SQLite restart/export đều được chạy |
| python3 scripts/dev.py e2e | **1 Chromium test passed /5.7s**; backend/DB tạm và Vite riêng; actual OCR/evidence, null-save-reload, scripted edit, stale409, confirm, downloaded JSON đúng revision và immutable prediction |
| evaluate_model.py --split test --output runtime/evaluation/consolidation-clean | Native 30 test samples: hoa_don15 documents **73/73 present**; don_de_nghi15 documents **103/103 present**. Tổng176/176, absent2/unreadable2. Không đổi rules/gold/config để đạt số này |
| git status --porcelain trong checkout sạch sau kiểm chứng | Rỗng; metadata native benchmark **git_dirty=false** ở đúng a1ba2c6 |

[Verification JSON](evidence/consolidation-verification.json) lưu command outcomes, native checks, engine/model/config/source hashes và per-schema metrics. `git diff a03ea30 -- backend/src pipeline/src contracts data backend/uv.lock` rỗng: không đổi implementation inference/domain, data/gold/contracts hoặc Python lock. Frontend runtime components giữ nguyên; chỉ thêm browser-test dependency/config và test.

## Commit hoàn chỉnh

- `4f6617d`: audit16 nhánh, baseline/ADR/inventory và chỉ mục bài tập.
- `0063693`: port24 test retry VT-042 nguyên blob13e32f0; Source-Commit và Co-authored-by thật.
- `94fe00f`: native browser E2E + dedicated disposable runtime, pinned Playwright.
- `aae7b2a`: một README/dev entry point và docs hiện hành; evaluator regression.
- `a1ba2c6`: CI5 jobs+aggregate gate, 5 tests success/failure/skipped/cancelled/missing; templates và gói GitHub local.
- Commit docs bàn giao sau a1ba2c6 chỉ cập nhật kết quả/link tài liệu, không đổi code đã nghiệm thu.

## Còn giới hạn / chưa chạy

- Workflow mới trên GitHub/Ubuntu chưa chạy vì **chưa được duyệt push**. Exact-SHA CI xanh của nhatquang baseline vẫn ghi trong snapshot, không thay evidence cho workflow mới.
- Docker CLI/Engine không có, chưa build/run containers. Không suy Docker đạt từ compose.yaml.
- npm audit trên lockfile báo **10 moderate, 0 high/critical**, tập trung ESLint/typescript-eslint/minimatch dev tooling; CONS-06 đã chuẩn bị triage. Không chạy audit fix --force hoặc hạ runtime/dependency để làm xanh.
- Minhthao checkout đối chiếu còn1 path portability test fail; không sửa hoặc nhập storage đó. Auth/PostgreSQL thật, PDF/multi-page, VLM/API và autosave/notification port chưa nằm trong nghiệm thu nền local này.
- Native score chỉ trên synthetic layouts biết trước, không phải bảo đảm accuracy hóa đơn thật. Scripted review trong E2E không dùng như dự đoán AI.

## GitHub và bảo toàn

Chỉ fetch không prune và API GET; main94c5101 vẫn unprotected, PR#1 vẫn mở, chưa có issue mới. Không push/merge/đổi default branch/quyền/xóa refs. [Gói duyệt](../.github/consolidation/README.md) có body PR, 8 labels, 3 milestones, 9 Issues và protection cần `Product checks` xuất hiện trước khi bật. Submission refs và output BT3 local nguyên trạng. Original workspace vẫn personal/canhtung-solo; nhánh consolidation nằm trong worktree riêng.
