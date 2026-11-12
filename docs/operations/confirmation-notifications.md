# Thông báo xác nhận tài liệu local

Theo [ADR0009](../decisions/0009-confirmation-notifications.md), `POST /api/v1/documents/{id}/confirm` phát `document.confirmed` sau khi DB đã commit lần chuyển revision sang confirmed. Notification không chạy khi chỉ validate, lưu nháp, xác nhận lỗi hoặc retry revision đã confirmed. Slice này dành cho người vận hành local qua application log; chưa gửi email, Slack hay webhook.

## Cấu hình và quan sát

`.env.example` cung cấp `DOCINTEL_NOTIFICATION_MODE=log` và `DOCINTEL_NOTIFICATION_TIMEOUT_SECONDS=0.05`. Đặt mode `disabled` để không attempt gửi. Timeout lớn hơn 0, tối đa 1 giây; không phải deadline của transaction DB/OCR. Settings không chấp nhận mode provider chưa có.

Logger mặc định có thể chưa hiện INFO. Để quan sát notification, dùng cấu hình log local đã cung cấp (thay cho terminal backend trong README):

```sh
uv run --project backend --locked uvicorn docintel.api.app:app --host 127.0.0.1 --port 8000 --limit-concurrency 16 --log-config configs/logging-local.json
```

Giữ setup/models/provider/runtime theo README; không chạy hai backend/worker trên cùng DB. Sau khi xác nhận bản lưu hợp lệ trong UI, stderr có `INFO docintel.services.notifications business_event=document.confirmed`. Timeout/lỗi adapter tạo cảnh báo `notification_delivery_failed event=document.confirmed`, không exception details hoặc source. Request confirm vẫn trả DocumentDetail/HTTP 200 nếu business operation thành công. Log này chỉ cho biết sink local đã xử lý event; không phải bằng chứng đã gửi email hoặc người dùng đã đọc.
