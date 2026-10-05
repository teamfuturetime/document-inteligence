# Backlog local

Các ID BL là local, chưa là GitHub issue. Owners theo [roles](../team/roles.md) đều TBD. Không đặt ngày/quality threshold giả.

| ID/mốc | Scope và acceptance criteria cụ thể | Requirements | Dependencies |
| --- | --- | --- | --- |
| BL-001 / Scope | Chốt loại đơn/hóa đơn, field definitions/required/aliases/format, giới hạn đầu vào và quyết định mở với nhóm/giảng viên; ADR+schema+traceability cập nhật; tên/deadline/quyền ghi thật khi biết | MVP-02/05, DATA-01, ENG-02 | Foundation |
| BL-002 / Baseline | Spike ít nhất các engine khả thi trên mẫu Việt được phép; ghi runtime/package/weights/nguồn, lỗi dấu/layout và tài nguyên; kết luận lựa chọn theo evidence, không threshold bịa | MVP-01, EVD-03/04 | BL-001 |
| BL-003 / Baseline | Adapter OCR thật sau Protocol, spans/text/score/coord/metadata; tests unavailable/failure/timeout/no fallback, predictions lưu có hashes, không đọc gold | MVP-01, EVD-04 | BL-002 |
| BL-004 / Baseline | Extraction rules nhãn/vị trí/ghép dòng, nhiều candidates/abstain/evidence; không hard-code ID/gold, tests mapping/unsupported/missing; benchmark baseline input rõ | MVP-02/03, EVD-02/03 | BL-001/003 |
| BL-005 / MVP | Upload PNG/JPG kiểm bytes/pixel/page/magic/path; SQLite + migrations/rollback và Document/run persistence; runtime ngoài Git; recovery/idempotency/run status có tests | MVP-01/02, DATA-01, ENG-01 | BL-001; phối hợp BL-003, UI không cần chờ AI xong |
| BL-006 / MVP | UI edit/clear/save, revisions/events, stale409/mất mạng/retry; prediction immutable, reviewed-null giữ xóa, edit confirmed mất confirm, re-OCR không ghi đè; tests API/UI | MVP-04/05 | BL-001/005; contract UI phát triển song song BL-004 |
| BL-007 / MVP | Confirm backend latest/persisted/valid và export đúng revision; không tin approved/JSON client; errors/stale/required-unreadable và E2E upload→review→export | MVP-05/06 | BL-006 |
| BL-008 / Evidence | Dataset card/nguồn quyền, nhiều layouts/quality theo scope, gold đối chiếu ảnh/review chéo; parent/content/checksum split audit; version, không inference gold; quy mô có lý do | DATA-01, EVD-01/04 | BL-001; cùng tiến hành BL-002/004 |
| BL-009 / Evidence | Config chốt + test độc lập, model predictions trước review + run manifest/hash/lock, per-field/support/micro/macro/document/abstain và taxonomy; báo giới hạn/latency nếu đo; lệnh manual benchmark thật | EVD-01/02/03/04 | BL-003/004/008 |
| BL-010 / Evidence | Chọn confidence policy trên validation, method/signals/threshold version cố định trước test; bucket support/accuracy, calibration chỉ khi có phương pháp/data; UI giải thích unknown/heuristic | MVP-03, EVD-02/04 | BL-009 baseline; validation của BL-008 |
| BL-011 / Optional experiment | Chỉ thử VLM nếu baseline errors có hypothesis và policy/budget cho phép; snapshot/prompt/hash/timeout/abstain/schema, so baseline cùng phép đo, ghi cost/repro hạn chế | MVP-02/03, EVD-02/04 | BL-009; quyết định thử nghiệm explicit |
| BL-012 / Delivery | Chạy demo luồng thật, README/report giới hạn/evidence đúng nguồn, verify cài mới/container/remote CI, review bàn giao và báo cáo theo rubric thực tế nếu được cung cấp | ENG-01/02/03/04, MVP-01..06 | BL-007/009/010; BL-011 không bắt buộc |

Ưu tiên sau nền: BL-001 → BL-002, BL-008 → BL-003 → BL-004; upload/UI có thể phát triển song song trên contract đã chốt. Readiness và acceptance phải được issue cụ thể hóa theo scope, không dùng số file/dòng code thay DoD.
