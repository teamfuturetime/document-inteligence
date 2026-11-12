# Thông báo xác nhận tài liệu local

Theo [ADR0009](../decisions/0009-confirmation-notifications.md), `POST /api/v1/documents/{id}/confirm` phát `document.confirmed` sau khi DB đã commit lần chuyển revision sang confirmed. Notification không chạy khi chỉ validate, lưu nháp, xác nhận lỗi hoặc retry revision đã confirmed. Slice này dành cho người vận hành local qua application log; chưa gửi email, Slack hay webhook.

## Cấu hình và quan sát

`.env.example` cung cấp `DOCINTEL_NOTIFICATION_MODE=log` và `DOCINTEL_NOTIFICATION_TIMEOUT_SECONDS=0.05`. Đặt mode `disabled` để không attempt gửi. Timeout lớn hơn 0, tối đa 1 giây; không phải deadline của transaction DB/OCR. Settings không chấp nhận mode provider chưa có.

Logger mặc định có thể chưa hiện INFO. Để quan sát notification, dùng cấu hình log local đã cung cấp (thay cho terminal backend trong README):

```sh
uv run --project backend --locked uvicorn docintel.api.app:app --host 127.0.0.1 --port 8000 --limit-concurrency 16 --log-config configs/logging-local.json
```

Giữ setup/models/provider/runtime theo README; không chạy hai backend/worker trên cùng DB. Sau khi xác nhận bản lưu hợp lệ trong UI, stderr có `INFO docintel.services.notifications business_event=document.confirmed`. Timeout/lỗi adapter tạo cảnh báo `notification_delivery_failed event=document.confirmed`, không exception details hoặc source. Request confirm vẫn trả DocumentDetail/HTTP 200 nếu business operation thành công. Log này chỉ cho biết sink local đã xử lý event; không phải bằng chứng đã gửi email hoặc người dùng đã đọc.

## Adapter và dữ liệu

`application.state.confirmation_notifier` là seam async `send(DocumentConfirmed)`. App startup chọn logging sink. Receipt nội bộ bất biến gồm `document_id`, `run_id`, `revision`, `name`; `event_id` suy từ name/run/revision. Không có invoice number, filename, image/OCR/review fields, source text hoặc địa chỉ người nhận. Logging sink chỉ ghi tên event.

Endpoint gọi `DocumentService.confirm_with_notice` trong threadpool, nhận detail + receipt sau commit, rồi mới gửi. API nội bộ synchronous `DocumentService.confirm` vẫn trả DocumentDetail và không tự gửi notification; caller ngoài HTTP muốn delivery phải dùng receipt và dispatcher rõ ràng. Không đăng ký adapter thực gửi dịch vụ bên ngoài nếu chưa được giao.

Adapter phải async/cooperative: không block event loop, không nuốt cancellation, không tự tạo task gửi ngầm. Timeout/caller cancellation dừng await hiện tại; không có retry/detached task trong dispatcher. Deadline không thể cưỡng chế một adapter cố tình block hoặc bỏ qua cancellation; provider production cần thiết kế isolation riêng.

## Best-effort và recovery

Đây không phải durable outbox: crash/cancel giữa commit và send có thể mất event. Adapter có thể đã nhận trước khi báo lỗi/timeout, hoặc tự gửi trùng. Stable event ID chỉ giúp downstream deduplicate, không cam kết exactly-once. Retry confirm sau lỗi gửi hoặc restart thấy revision đã confirmed và không gửi lại. DB history vẫn chỉ có một `confirmed` event cho transition đó; trạng thái notification không được giả là persisted/delivered.

Vì DB đã commit, client hủy request trong lúc gửi không rollback confirmation. Reload/retry cùng run/revision để lấy trạng thái persisted; không tự tạo draft mới hoặc chạy lại OCR để gửi notification. Nếu cần retry/replay/durable delivery, tạo thiết kế ADR riêng, migration/retention và quyền provider trước khi triển khai.

## Kiểm chứng và nguồn

`backend/tests/test_confirmation_notifications.py` kiểm response mapping chính xác, DB commit trước send, rollback/stale/invalid không gửi, concurrent/retry chỉ notify transition, timeout/exception, caller cancellation, restart, disabled mode, logging không chứa payload và cấu hình invalid.

Nguồn tham chiếu: `feat/vt046-validation-notification@31a18bb`, `backend/src/document_backend/services/notifications.py`, `backend/experiments/README.md`. Nguồn là stateless `review.validated`, không có DB/recipient provider. Bản port docintel gắn receipt sau transaction, giữ toàn bộ submission refs/report/authorship gốc, không nhập production app thứ hai.

[Báo cáo kiểm chứng local](../reports/confirmation-notifications-2026-11-12.md) ghi kết quả thực tế, exact source hashes, native evidence và giới hạn môi trường.
