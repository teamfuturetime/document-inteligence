# VT-042 - Specification và kế hoạch

Phạm Nhật Quang - 23001920 - SE2026-T11. Baseline: `db727496312087af6495aa12e7c9a52df3dfa230` trên `origin/nhatquang`. Ngày đối chiếu: 03/11/2026, sau `git fetch origin --prune`. Nhánh bài làm: `codex/bt3-vt042-async-retry`.

## Specification

OCR là tác vụ dài. Upload cần trả định danh tác vụ để UI theo dõi; retry sau khi mất phản hồi không được tạo thêm tài liệu/run/event upload. Lỗi cần sửa: hai request cùng vượt initial key lookup có thể tranh slot cuối, khiến retry bị trả `429` thay vì replay hoặc `409`.

- AC1: Upload hợp lệ trả 202 + document_id/run_id; GET đọc queued/running/terminal mà không chờ inference.
- AC2: Cùng key + bytes + schema + data_origin, kể cả request đồng thời hoặc mất ACK sau commit, giữ cùng IDs; đúng một document/run/uploaded event.
- AC3: Fingerprint khác với key cũ trả 409; key mới khi đầy trả 429; không có file/record/event thừa.
- AC4: OCR lỗi, storage lỗi và restart có kết quả xác định; retry upload không tự tạo run mới; reload đọc dữ liệu lưu.
- AC5: Giới hạn B byte inclusive: B-1/B được nhận, B+1 trả 413 không side effect.

Invariant: một key hợp lệ nhận diện tối đa một logical upload đã commit. Capacity chỉ hạn chế yêu cầu mới.

NFR: so sánh p95 với 4,0 giây ở 150 request đồng thời; báo riêng success/rejection và không đồng nhất admission với OCR completion. Một SQLite DB/worker, synthetic PNG; không thêm dependency/schema công khai; tests tách dữ liệu và không dựa vào sleep để đoán thời điểm chạy.

## Prompt và kế hoạch trước patch

Prompt: "Trên baseline db727496, sinh test theo VT-042 cho async upload và retry. Giữ SQLite/file thật; ép hai request cùng qua initial key miss bằng Barrier; kiểm IDs và số record/event/file, không chỉ status. Kiểm biên B-1/B/B+1 để thử mutation > thành >=. Chỉ đề xuất patch nhỏ sau khi lưu lần chạy red đúng nguyên nhân."

Kế hoạch: (1) audit remote và call path; (2) test-first ở `backend/tests/test_async_retry_vt042.py`; (3) lưu red rồi commit test/spec; (4) re-read key trong write transaction trước check_capacity ở `backend/src/docintel/services/documents.py`; (5) chạy green, mutation/restore, coverage, thứ tự test và tải TCP150; (6) đầy đủ checks backend/AI/contracts/data/frontend/native; (7) commit evidence, push branch, cập nhật PDF/link.

File ngoài hai file code/test: `homework/VT-042/README.md`, spec, AI log, runner và evidence. Không đổi public contracts, model/config/data hay source inference.

## Review kế hoạch theo code thực tế

1. Bác đề xuất thêm Celery/Redis/jobs schema: `services/worker.py` đã chạy thread nền; `services/documents.py::process_next` claim và persist run, `001_documents.sql` có UNIQUE idempotency_key. Chỉ sửa thứ tự quyết định admission.
2. Bác giả định async def/202 là background: congtri gọi process_document trước khi trả 202; minhthao await HTTP AI trong request; canhtung await threadpool extraction. Nhatquang tách persisted admission và worker. Audit chỉ dùng source implementation, không lấy test plan/data/reflection của VT-043/VT-045.
3. Sửa hai draft test yếu: W1 status-only thành replay IDs + DB/event/file cardinality; W2 happy path lặp thành conflicting fingerprint không thay đổi dữ liệu cũ. Một tài liệu lưu 2 files (source/preview), không phải 1.
4. Bác mutation tại queue boundary: pending >= capacity hiện đúng; phép đổi > thành >= phải đặt tại upload byte bound đang cho phép đúng B byte.

Review này được thực hiện bằng đọc diff/call path và thực thi; không ghi nhận approval của thành viên nhóm.
