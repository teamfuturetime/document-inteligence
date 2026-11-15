# Issue #10 — Notification sau transaction confirm

> Nhánh hiện hành: `feat/10-confirmation-notifications-30`. Theo yêu cầu người dùng, lịch sử được tổ chức thành 30 mốc có thay đổi thực. Bản ghi bên dưới giữ nguồn kiểm chứng ban đầu; phần cuối ghi đối chiếu nhánh mới.

Nhánh `feat/10-confirmation-notifications`, base `main@0868cf6`, implementation `76ac46e` (code ở `61b03ab`, kèm cấu hình log/runbook). Không phụ thuộc hoặc đưa 40 commits của PR #16 vào nhánh này. Đây là kết quả local, chưa review/merge/push, chưa gửi dịch vụ bên ngoài.

## Hành vi và hợp đồng

Theo [ADR0009](../decisions/0009-confirmation-notifications.md), receipt `document.confirmed` được trả sau khi transaction chuyển revision draft → confirmed đã commit. HTTP adapter gửi một lần tới local logging sink với timeout cooperative mặc định 50 ms. Không phát cho validate/save/failed confirm hoặc retry revision đã confirmed. Lỗi/timeout sender không đổi HTTP 200/DocumentDetail, trạng thái confirmed, history hay export. Caller cancellation propagate, dữ liệu đã commit vẫn còn.

Payload chỉ có ID tài liệu, run, revision và event name; stable event ID suy từ name/run/revision. Log sink chỉ ghi tên event; cảnh báo lỗi không chứa exception details. Không email/webhook recipient, không đổi public schema, generated types, DB schema hoặc pipeline. Best-effort có thể mất event giữa commit/send, downstream có thể nhận trùng khi adapter tự retry; không outbox/durable/exactly-once. [Runbook](../operations/confirmation-notifications.md) có disabled mode, cấu hình INFO và giới hạn adapter.

Lineage: tham chiếu notification seam trong `feat/vt046-validation-notification@31a18bb`, không copy app/schema hoặc giả rằng source stateless đã có persisted confirmation. Submission refs, tác giả và báo cáo gốc giữ nguyên.

## Kiểm chứng đã chạy

Tests viết trước implementation: lượt đầu collection fail vì module chưa tồn tại; sau implementation đã đối chiếu mapping với cả summary `review_status` và nested review theo contract hiện có, không sửa production expectations để che regression.

| Check | Kết quả |
| --- | --- |
| Ruff lint + format check | PASS, 66 Python files |
| `pytest backend/tests pipeline/tests -q` | PASS, 118 tests: 103 baseline main + 15 notification tests |
| Focused notification + existing product workflow | PASS, 28 tests |
| `scripts/generate_contracts.py --check` | PASS, 25 contracts, không drift public API |
| `scripts/check_data.py` | PASS, 6 fixture + 150 independent parent product samples |
| Frozen evaluator regression | PASS, replay predictions đã pin, không inference mới |
| Fixture evaluator | PASS, contract check; output `runtime/checks/issue10-fixture.json` |
| Frontend contracts/types/lint/format/test/build | PASS, 12 component tests |
| Native `scripts/verify_product.py` | PASS, 14 checks với Tesseract 5.5.2, đúng vie/eng model lock |
| Chrome E2E invoice | PASS, 1 test: upload/OCR/null/reload/edit/CAS409/confirm/export |
| Local logging configuration smoke check | PASS, ghi đúng `business_event=document.confirmed` |
| Repository/docs + diff whitespace | PASS |

Notification tests dùng SQLite thật và doubles chỉ cho OCR/sender: sender có thể mở writer khác và đọc confirmed state; exact response giữ nguyên khi send success/error/timeout; rollback/stale/invalid/missing không gửi; concurrent/retry chỉ một transition; cancel trong khi send không rollback và không để delivery task tách rời; retry sau restart không redeliver; logging không chứa payload/exception; disabled mode và invalid settings.

Native run dùng `DOCINTEL_TESSERACT_EXECUTABLE` trỏ vào binary ignored `runtime/tools/tesseract/bin/tesseract`, bật `logging.config.dictConfig` từ `configs/logging-local.json`; thực tế thấy các dòng event trong workflow invoice/application. [Native evidence](../evidence/confirmation-notifications-native-2026-11-12.json) và [source hashes/check summary](../evidence/confirmation-notifications-2026-11-12.json) pin implementation. Native metadata có thể `git_dirty=true` vì local artefacts cũ; không thay dataset/model/gold. Commit báo cáo cuối không sửa code đã kiểm chứng.

Môi trường: macOS 13.5 arm64, Python 3.14.5, Node 24.18.0/npm 11.16.0 khác pin repo 24.16.x/11.13.x. Playwright bundled Chromium không hỗ trợ macOS 13; E2E dùng Chrome 157 qua config trong runtime, không đổi test/config CI. Docker và email/webhook provider không được chạy. Remote Product CI và review của thành viên khác còn pending.

## Đối chiếu nhánh 30 commit

Nhánh `feat/10-confirmation-notifications-30` xuất phát từ `main@0868cf6`, gồm 30 commit riêng của issue #10 sau commit báo cáo này. Giữ nguyên nhánh 4 commit ban đầu `feat/10-confirmation-notifications@0b55f61`; không backdate, không commit rỗng, không push hoặc merge.

Các mốc gồm hợp đồng sự kiện và receipt bất biến; logging sink; cách ly exception, timeout và cancellation; cấu hình mode/deadline; receipt sau commit; tích hợp HTTP; từng nhóm regression scenario; logging config, runbook, lineage và evidence. Kiểm thử phù hợp được chạy khi thêm từng mốc.

Đối chiếu tại implementation `b4c4805`: toàn bộ backend/src, backend/tests, pipeline, scripts, frontend, configs, env sample, dependency metadata/lock và generated contracts giống byte-for-byte với nhánh ban đầu `0b55f61`. Không mở rộng tính năng hay thay đổi behavior chỉ để thêm commit. Ruff lint/format, 118 backend/pipeline tests và 25 generated contracts đã chạy lại và đạt trên nhánh mới. Các kết quả frontend 12 tests, native 14 checks và Chrome E2E 1 test ở bản ghi ban đầu tiếp tục là evidence của mã không đổi; không tuyên bố đã chạy lại các checks đó trên SHA mới.

[Đối chiếu source nhánh mới](../evidence/confirmation-notifications-30-2026-11-12.json) ghi implementation SHA, base và source hashes. Commit cuối chỉ bổ sung báo cáo/evidence; không đổi code sau kiểm chứng. Các giới hạn best-effort/logging only, môi trường Node/npm/Chrome và remote review/CI pending vẫn như mô tả phía trên.
