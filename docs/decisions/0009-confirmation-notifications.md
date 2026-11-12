# ADR0009 — Best-effort notification sau xác nhận đã commit

Status: triển khai local theo yêu cầu người dùng cho issue #10 (CONS-07); chưa review/merge. Nền là main@0868cf6, độc lập PR #16 của issue #8.

## Quyết định

Sự kiện `document.confirmed` chỉ phát khi transaction chuyển revision từ draft sang confirmed đã commit. Không phát cho validate đơn thuần, save draft, confirm lỗi/stale, hoặc retry revision đã confirmed. Receipt nội bộ chỉ chứa document/run ID, revision và event name; ID sự kiện ổn định suy từ run/revision để adapter tương lai có thể deduplicate. Không đưa ảnh, tên file, trường OCR/review, source text, invoice number hoặc exception details vào payload/log.

Recipient của slice này là người vận hành ứng dụng local qua logging sink, cùng hướng seam của VT-046; không email, Slack, webhook hoặc provider ngoài. Mặc định mode `log`, có thể tắt bằng `DOCINTEL_NOTIFICATION_MODE=disabled`. Muốn quan sát log cần cấu hình logger `docintel.services.notifications` ở INFO và handler thích hợp. Adapter async được gắn trên app state, phải không block event loop và tuân thủ cancellation. Không gọi dịch vụ bên ngoài trong task này.

Endpoint confirm giữ HTTP 200 và DocumentDetail cũ. Nhận kết quả transaction trong threadpool, rồi mới attempt gửi một lần trong request với deadline cooperative mặc định 50 ms (`DOCINTEL_NOTIFICATION_TIMEOUT_SECONDS`, lớn hơn 0 và tối đa 1 giây). Timeout/exception của sender chỉ tạo cảnh báo cố định; không rollback, retry transaction hoặc đổi response. Caller cancellation tiếp tục propagate sau commit, không giả rằng đã rollback. Không detached delivery tasks hoặc hàng đợi RAM tăng không giới hạn.

## Delivery và giới hạn

Best-effort, không phải outbox/durable delivery: process có thể chết giữa commit và send; caller có thể hủy trước/sau send; adapter có thể đã nhận event dù sender báo lỗi/timeout. Retry confirm đã persisted không gửi lại. Có thể mất event, downstream có thể nhận trùng nếu adapter tự retry; event ID không phải cam kết exactly-once. Nếu cần reliable delivery phải có ADR/outbox/retention/migration riêng.

Không hook bên trong transaction; không bọc lỗi notification trong nhánh đánh dấu OCR failed. Không sửa schema DB hoặc public product/export model, không đưa delivery status vào response business.

## Lineage và nghiệm thu

Tham chiếu `feat/vt046-validation-notification@31a18bb`, `backend/src/document_backend/services/notifications.py` và `backend/experiments/README.md`: nguồn đó là stateless `review.validated`, logging seam và cooperative deadline. Slice này viết adapter cho persisted docintel, không copy app/response schemas hoặc tuyên bố source đã có production persistence. Giữ nguyên submission refs, tác giả và báo cáo gốc.

Tests viết trước implementation: exact response mapping; sender quan sát DB đã confirmed; không gửi khi rollback/422/409/404; retry và concurrent confirm chỉ tạo một event; provider exception/timeout/cancel giữ transaction; dữ liệu nhạy cảm không có trong payload/log; disabled mode; restart persisted export. Kiểm tra backend/contracts/frontend, native OCR và browser theo AGENTS.md trước bàn giao.
