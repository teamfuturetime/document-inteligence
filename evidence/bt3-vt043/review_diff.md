# Báo cáo kỹ thuật VT-043

Ngày kiểm chứng: **29/10/2026**, Asia/Bangkok. Phạm vi: Automatic OCR Draft Saving with Concurrency Control. Baseline `997da9fe1cf617dcf4ec53fe5ed2ce2d5a4469ee`; nhánh riêng `bt3-vt043-autosave`.

## Kết luận trong phạm vi đã chạy

Autosave, stale-write rejection, persistence, security regressions và mutation **PASS** trong môi trường được ghi nhận. Backend regression cuối: **172 PASS, 1 SKIP**; test symlink bị bỏ qua vì Windows không cho tạo symlink. Frontend **52/52 PASS**, TypeScript, ESLint, production build và coverage **PASS**; output cuối nằm trong `frontend_test.log`. Không tuyên bố đã chạy browser E2E hoặc PostgreSQL.

Lần HTTP performance cuối đạt p95 ≤ 2.500 ms: P-01 **1.834,90 ms**, 80/80 HTTP 200; P-02 **1.306,35 ms**, 1 HTTP 200 và 79 HTTP 409 đúng kỳ vọng. Fresh database Session xác nhận đúng nội dung winner, revision 1 và OCR gốc không đổi. Lần đo trước có một transport ReadError, được giữ nguyên và đánh dấu FAILED; xem [performance_review.md](performance_review.md) cho cả ba run, thay đổi chính sách kết nối và giới hạn suy luận nguyên nhân.

## Thay đổi implementation

- `backend/app/models/document.py`, `schemas/documents.py`, `migrations/versions/0004_ocr_revision.py`: revision non-null mặc định 0; API trả revision; request phải có strict integer `expected_revision` từ 0 đến 2.147.483.647. Client cũ không truyền revision nhận 422 và cần cập nhật.
- `backend/app/repositories/documents.py`: một SQL UPDATE có điều kiện id/owner/revision/trạng thái cho phép/OCR tồn tại; tăng revision và lưu correction trong cùng statement. Không ghi đè OCR gốc, không có read-then-write không được bảo vệ.
- `backend/app/services/documents.py`: trả conflict khi conditional update không đổi row; chụp snapshot response trước khi commit và chỉ trả thành công sau commit. Rollback khi commit thất bại; giữ mapping lỗi API đang có.
- `frontend/src/components/OCRTextCard.tsx`: debounce 800 ms, serialize request, snapshot nội dung từng lần gửi, giữ phần đang gõ khi request cũ thành công, giữ draft khi 409/500/offline/ack sai. Không gửi khi readOnly hoặc unmount; chỉ hiển thị đã lưu cho nội dung server xác nhận.
- `frontend/src/pages/DocumentDetailPage.tsx`, `api/client.ts`, `types/index.ts`: truyền revision, bảo vệ instance theo document, bỏ response revision cũ/cùng revision đã được load; khóa confirm khi còn thay đổi/chưa có acknowledgement và khóa OCR trong action. Confirm/reopen/export vẫn được regression test.
- `frontend/src/utils/ocrDrafts.ts`, `contexts/AuthContext.tsx`: phục hồi bản nháp trong tab sau SPA navigation/reload với expected revision ban đầu; thông báo đây là bản chưa được xác nhận. Draft confirmed vẫn đọc/copy được. Logout cảnh báo trước khi xóa bản nháp; logout lỗi giữ draft; đổi account xóa draft account trước. Không lưu token/password trong draft.
- `frontend/package.json`, lockfile, `eslint.config.js`, `vite.config.ts`: quality gates và V8 coverage bằng dependencies phát triển. `.gitignore` loại local test tools/cache/venv và cho phép lưu evidence logs. Không thêm dependency runtime.

## Test, harness và traceability

| AC / rủi ro | Case và test file | Code được bảo vệ | Evidence | Commit |
|---|---|---|---|---|
| AC-01: debounce, không cần nút lưu | FT-01/02/03, `frontend/src/components/OCRTextCard.autosave.test.tsx`; page autosave | OCRTextCard; page/client/types | `frontend_fail_before_patch.log`, `frontend_test.log`, `frontend_flaky_review.log` | Frontend `f0babc9` |
| AC-02: stale write/multi-client | CT-01/02/03, `tests/integration/test_ocr_autosave.py`; stale API test trong `test_document_review.py`; repository guards | Atomic conditional update, schema revision, migration | `concurrency_test.log`, `backend_regression.log`, `performance_results.json` | Backend `d7828e6`; verification commit thêm CT/harness |
| AC-03: auth, CSRF, owner, trạng thái, validation | `test_auth_ownership.py`, `test_document_review.py`, `tests/unit/test_document_repository.py`; FT-09 | Giữ dependencies/auth; guard trong SQL; reject blank/invalid revision | `backend_regression.log`, `backend_revision_bound_before.log`, `backend_revision_bound_after.log`, `frontend_test.log` | Backend `d7828e6`; frontend `f0babc9` |
| AC-04: durable correction, OCR gốc/export/confirm/reopen | `test_ocr_correction_persists_without_modifying_raw`, `test_confirm_locks_review_reopen_and_export_reviewed_values`, migration/backfill test, response snapshot test | Transaction/snapshot, correction riêng với raw, migration 0004 | `backend_regression.log`, `backend_response_snapshot.log`, `coverage.json`, CT/P final DB state | Backend `d7828e6`; verification commit |
| AC-05: 409/500/offline/new typing/stale response/unmount | FT-04–10; recovery/navigation/confirmed-response tests trong page; AuthContext privacy tests; API contract tests | Draft state/storage, response snapshot/revision guard, logout cleanup | `frontend_test.log`, `frontend_equal_revision_fail_before_patch.log`, `frontend_flaky_review.log` | Frontend `f0babc9` |
| Validation mutation bắt buộc | `test_ocr_correction_rejects_whitespace` và `scripts/ocr_validation_mutation.py` | Blank validator | `mutation.diff`, `mutation_before.log`, `mutation_fail.log`, `mutation_restored.log`, `mutation_results.json` | Backend `d7828e6`; verification commit |
| 80 concurrent HTTP operations, p95 | P-01/P-02, `scripts/ocr_autosave_performance.py`, `scripts/ocr_autosave_support.py`; 4 corruption tests trong CT file | Full authenticated HTTP stack và report accuracy | `performance_results.json`, `performance_summary.md`, `performance_review.md`, `performance_harness_*` | Verification commit thêm harness/evidence |

Các tệp test cũ được điều chỉnh theo contract revision: `tests/unit/test_ocr_text.py`, `frontend/src/components/OCRTextCard.test.tsx`; các tests bổ sung nằm trong `frontend/src/api/client.test.ts`, `components/OCRTextCard.autosave.test.tsx`, `pages/DocumentDetailPage.test.tsx`, `contexts/AuthContext.test.tsx`, `tests/integration/test_ocr_revision_migration.py`. Tên và hash commit cụ thể được tra bằng `git log --oneline bt3-vt043-autosave` hoặc `git log -- <file>`; verification commit là commit thêm chính báo cáo này.

## Mutation và coverage

Mutation thực sự sửa file schema tạm thời, không chỉ mock validator. Test whitespace PASS trước mutation, FAIL với HTTP 200 thay vì 422 khi bỏ validator, rồi PASS sau restore. `source_restored_byte_for_byte=true`; SHA256 source khôi phục nằm trong `mutation_results.json`. Deliberate bug không nằm trong source cuối; `mutation.diff` chỉ là artifact thí nghiệm.

Backend sáu module liên quan: line **85,51%** (484/566), branch **76,00%** (76/100), coverage kết hợp line/branch mà công cụ hiển thị là 84,08%. Không nhầm số kết hợp với line coverage. Frontend: line **98,24%**, statements **83,83%**, branch **82,62%**. Số liệu riêng trong [coverage.txt](coverage.txt) và `frontend_coverage/coverage-summary.json`; JSX dày trên một dòng làm physical line coverage cao hơn statement coverage. Xem các nhánh thiếu và regression đề xuất trong `coverage.txt`.

## Flaky review

1. **Debounce/timing/asynchronous completion:** fake timers, kiểm tra trước/sau mốc 800 ms, deferred promises điều khiển thứ tự response; assertions dựa trên editor/status/disabled controls. Không dùng sleep thực. Lặp riêng nhóm timing/navigation năm lần, **31 × 5 = 155 test executions PASS**, lưu `frontend_flaky_review.log`.
2. **Shared DB/transaction order/scheduling:** file SQLite riêng mỗi test, WAL, Session riêng mỗi request, Barrier timeout hữu hạn trước CAS, không giả định winner. Sau workers hoàn tất mới mở Session kiểm tra persisted state. CT-01/02/03 đã chạy năm lần liên tiếp: **15/15 PASS** trong `concurrency_test.log`. Bốn negative harness tests được thêm sau lần lặp này và PASS trong final backend suite.
3. **Transport:** một run tải có ReadError được giữ là FAILED. Chính sách mỗi request mở TCP mới loại việc tái dùng socket đăng nhập đã idle khỏi lần đo cuối; không dùng retry để che lỗi. Nguyên nhân chính xác của ReadError chưa được chứng minh.

## Tính toàn vẹn evidence và Git

Logs là output thực thi thật. `backend_initial.log` là lần regression rộng sau khi các test mới đã được thêm, không phải suite nguyên bản tại baseline. `test_fail_before_patch.log` sao chép output regression trước backend patch; `test_pass_after_patch.log` tổng hợp output PASS cuối có nguồn rõ ràng. Giữ cả lỗi test và lỗi gọi công cụ coverage để phân biệt bug implementation với lỗi thao tác AI. Các log được chuẩn hóa UTF-8, bỏ ANSI; credential xuất hiện trong repr fixture được redact, không sửa kết quả hay số liệu đo.

`minhthao` giữ nguyên baseline; không push, merge hay tạo PR. Hai file untracked ban đầu (`ocr-review.patch` và file tên bắt đầu `how 75a0feb`) không được chỉnh sửa/stage. Evidence không chứa `.env`, password hoặc session cookie thật. Xem README để tái hiện toàn bộ kiểm chứng.

## PENDING / giới hạn trước khi nộp

- **PENDING:** critical journey trên trình duyệt thật Login → Document Detail → Edit → Autosave → Reload → Confirm. Repo không có browser E2E framework; chưa thêm framework lớn. Test jsdom/API không thay thế kết quả browser.
- **NOT VERIFIED:** migration/concurrency/performance PostgreSQL, môi trường backend pin gốc, mạng từ xa, tải kéo dài và hiệu năng OCR engine. Chỉ có SQLite WAL và môi trường phiên bản ghi nhận.
- **SKIPPED:** một unit test symlink vì quyền Windows. Còn warning từ AnyIO/pytest và Starlette/httpx do version môi trường, không sửa dependency ứng dụng ngoài phạm vi.
- Bản nháp browser có vòng đời tab, không bảo đảm tồn tại khi đóng tab/xóa storage. Khi storage hết quota/bị chặn, UI cảnh báo copy trước điều hướng. Conflict giữ draft và cần người dùng đối chiếu; không có automatic text merge.
- Áp dụng migration 0004 lên database triển khai sau khi sao lưu; client ngoài frontend này cần gửi expected_revision. Chưa sửa database thật hoặc triển khai lên remote.

Các yêu cầu chức năng bắt buộc đạt trong phạm vi kiểm chứng; các mục PENDING/NOT VERIFIED ở trên chưa được coi là hoàn tất.
