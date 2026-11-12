# Kiểm chứng foundation — AI-02

Ngày kiểm chứng: 05/10/2026, Asia/Saigon (UTC+7). Đây là báo cáo nền cục bộ; chưa benchmark mô hình hay hoàn thành MVP. Các bảng lệnh sẽ được cập nhật từ lượt chạy cuối, không suy từ việc có file.

## Những gì đã tạo/sửa

Giữ Git/remote/nhánh hiện có, mở rộng README ban đầu. Tạo backend FastAPI modular, Settings, Pydantic contracts strict, normalization/validation/reviewed-null rule, adapters explicit fixture, API health/capabilities/schemas/catalogue/ảnh và lỗi có request ID. Tạo React/TypeScript giới thiệu/đối chiếu read-only, API client/types sinh, states loading/error/empty và banner/disabled actions. Tạo 6 PNG synthetic/gold/predictions/OCR spans, generator và manifest checksums ảnh/nhãn; evaluator counts/micro/macro/document/abstain và run manifest. Bổ sung lockfiles thật, Dockerfiles/Compose, CI, forms/PR/CODEOWNERS.example, đầy đủ docs/ADR/backlog/test plan/onboarding.

## Quyết định áp dụng

React/TS/Vite + FastAPI/Pydantic, uv/npm, Python3.14.5/Node24.16.0, monorepo modular, đơn đề nghị typed 7 fields một trang: đã áp dụng cho scaffold, **PROVISIONAL** cho sản phẩm cuối. Models backend source of truth, generated OpenAPI/JSON Schema/frontend types và fixture explicit: FOUNDATION_REQUIRED. Chỉ synthetic/sample: COURSE_REQUIRED. SQLite mới dự kiến MVP, không DB workflow. [Decision log](../adr/README.md).

## Feature status

| Feature | Thực tế | Phạm vi chứng minh |
| --- | --- | --- |
| health/capabilities/schemas | Chạy thật | Tiến trình/domain metadata, ocr_ready false |
| normalization/validation | Chạy thật | Schema mẫu, NFC/zero/calendar/cross-field/draft/final |
| contracts/export examples | Chạy thật schema/check; export minh họa | Không có persisted export service |
| UI catalogue/ảnh/evidence | Fixture | Source và predictions viết sẵn, chỉ xem |
| fixture evaluator | Chạy thật evaluator trên fixture | Không OCR/model quality |
| OCR/extraction/provider/calibration | Chưa triển khai/chưa đo | Interface/strategy/backlog |
| Upload/SQLite/review/edit/save/confirm/export workflow | Chưa triển khai | Contract/đặc tả, buttons disabled |
| CI GitHub | Cấu hình local | Chưa có run remote |
| Container | Dockerfile/Compose local | Chưa build/run; thiếu Docker CLI |

## Lệnh và kết quả

Lượt cuối: **14/14 checks local PASS**, **40 tests backend + 4 tests frontend PASS**. Chạy bằng `uv run --project backend --locked python scripts/verify_foundation.py`; script dừng ngay khi failure, không che exit code. Record máy đọc được tại `runtime/verification-local.json` (ngoài Git). Thời gian dưới đây đổi từ UTC sang Asia/Saigon, ngày 05/10/2026.

| Lệnh thực tế tương đương | Kết quả | Giờ UTC+7 |
| --- | --- | --- |
| `uv run --project backend --locked python -m ruff check backend scripts` | PASS | 18:26:28 |
| `uv run --project backend --locked python -m ruff format --check backend scripts` | PASS | 18:26:28 |
| `uv run --project backend --locked python -m pytest backend/tests -q` | PASS | 18:26:28 |
| `uv run --project backend --locked python scripts/generate_contracts.py --check` | PASS | 18:26:29 |
| `uv run --project backend --locked python scripts/check_data.py` | PASS | 18:26:30 |
| `uv run --project backend --locked python scripts/evaluate_fixtures.py` | PASS | 18:26:30 |
| `uv run --project backend --locked python scripts/check_repository.py` | PASS | 18:26:31 |
| `npm --prefix frontend ci` | PASS | 18:26:31 |
| `npm --prefix frontend run contracts:check` | PASS | 18:26:36 |
| `npm --prefix frontend run typecheck` | PASS | 18:26:44 |
| `npm --prefix frontend run lint` | PASS | 18:26:46 |
| `npm --prefix frontend run format:check` | PASS | 18:27:07 |
| `npm --prefix frontend run test` | PASS | 18:27:08 |
| `npm --prefix frontend run build` | PASS | 18:27:36 |

Setup/generation trước lượt cuối, cùng ngày: `uv lock --project backend`, `uv sync --project backend --locked`, cài dependencies npm bằng công cụ sinh lock thật, `generate_fixtures.py`, `generate_examples.py`, `generate_contracts.py`, `npm --prefix frontend run contracts:generate` đều hoàn tất. Đọc refs Actions qua `git ls-remote` và remote default main thành công; không ghi remote.

`docker compose version`: **BLOCKED**, PowerShell báo không tìm thấy docker. YAML/Compose cấu trúc local đã parse/kiểm tra bind loopback trong repository check; Docker build/run/config CLI và CI remote vẫn chưa xác minh. `git diff --check`: PASS; `.env`, venv, node_modules và runtime được Git ignore.

## Kiểm tra ảnh và UI

Đã mở cả 6 PNG: dấu Việt rõ, không thấy tràn/đè nội dung; mã đầu 0 giữ nguyên; sample003 có hai dòng nội dung; sample004 faculty trống; sample005 ngày 31/02/2005 nhìn thấy; sample006 mã bị che và gold unreadable/null. Coding agent đối chiếu nguồn/nhãn; **chưa có reviewer thứ hai của nhóm**. Generator/font không đổi layout ở lượt sinh cuối, checksums ghi trong manifest. Browser smoke đã mở trang giới thiệu và catalogue fixture_001 qua backend thật: ảnh tải được, bảy field hiển thị, provenance/banner rõ, inputs read-only, confidence chưa đo, Lưu nháp/Xác nhận/Xuất JSON disabled và chọn field có vùng evidence giả lập. Đây là kiểm tra runtime UI tại viewport trình duyệt mặc định, không E2E AI/MVP hoặc audit accessibility đầy đủ.

## Failures đã xử lý

- Lần cài đầu dùng --locked trước khi lock tồn tại: fail; sinh lock thật bằng uv lock, rồi frozen sync.
- Console Windows cp1252 làm print tiếng Việt/đường dẫn Unicode fail sau khi tạo artifacts: chuyển success diagnostics ASCII, không đổi dữ liệu UTF-8; dùng PYTHONUTF8 trong verifier/CI.
- Frontend lượt đầu có optional evidence_span_ids và ESLint thiếu global URL: đã sửa access optional/global, chạy lại type/lint/tests/build.
- Frozen npm install lần đầu bị EPERM vì Vite dev server đang giữ native rolldown DLL. Dừng đúng process Vite do agent mở rồi chạy lại frozen install; lượt cuối PASS, không dùng quyền Administrator hay che lỗi.
- Cảnh báo TestClient của dependency mới cần httpx2: chuyển dev dependency sang httpx2 đã pin và regenerate lock, không suppress warning.

## Giới hạn và việc chưa kiểm chứng

Không OCR/VLM thật, không quality claim/calibration/latency/user study; seed không đủ golden benchmark hoặc test độc lập. Chưa chạy native Linux/macOS/WSL2, Docker hoặc Actions remote; parse YAML không đồng nghĩa container/CI run. Upload security mới config/test plan, chưa enforcement runtime vì chưa có upload. Chưa persistence/revision service, final export example không có người xác nhận thật. License/nhân sự/handles/deadline/budget/scope cuối TBD.

## Bốn GitHub evidence

| Evidence | Trạng thái |
| --- | --- |
| Golden dataset | Dataset card/format/6 seed/provenance/checksums; chưa benchmark dataset hoàn chỉnh/review chéo |
| Field-level metrics | Evaluator + tests + fixture report; model benchmark **chưa đo** |
| Error taxonomy | Mã ổn định + record synthetic minh họa; chưa thống kê model |
| Model/config versioning | Config/RunManifest/versions/hashes/git dirty/locks/hardware và run fixture; real OCR weights/model snapshots chưa có |

## Remote

Đã đọc remote/default main, giữ remote và nhánh nhatquang. Không commit/push, mở issue/PR/mời người hoặc đổi settings/visibility. Templates/workflow/CODEOWNERS.example local, chưa Actions run/ruleset/review setting; xem [github-setup](../governance/github-setup.md). Accounts/license/kênh bảo mật cần người có quyền xác nhận, không bịa.

## Năm việc tiếp theo

1. BL-001 chốt scope/field definitions/input và các quyết định mở.
2. BL-002 spike OCR Việt có model/package/nguồn/quyền và errors thật.
3. BL-008 mở rộng sample/gold được phép, review chéo và split parent độc lập.
4. BL-003 tích hợp OCR thật, giữ spans/metadata/errors, không mock fallback.
5. BL-004 extraction baseline nhãn/vị trí/multiline/abstain có predictions/version để benchmark.

Acceptance/dependencies tại [backlog](../planning/backlog.md). Review/upload có thể phát triển song song sau contract đã chốt; không đợi AI xong mới thống nhất API/UI.
