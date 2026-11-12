# Giới hạn tiếp nhận upload — issue #8

Áp dụng cho `POST /api/v1/documents` của nền local/single-user, theo [ADR0008](../decisions/0008-primary-invoice-platform.md). API backend 0.2.1 giữ nguyên body ảnh raw, idempotency key, dữ liệu và schema export 1.0.0. OpenAPI/types được sinh lại để mô tả thêm lỗi 400/408.

## Budget

| Lớp | Mặc định | Cấu hình/phạm vi |
| --- | --- | --- |
| Body nhận vào | 5 MiB (5.242.880 bytes) | `DOCINTEL_MAX_UPLOAD_BYTES`, tối đa 20 MiB; kiểm cả khai báo và byte thực tế |
| Tổng thời gian nhận body | 30 giây | `DOCINTEL_UPLOAD_RECEIVE_TIMEOUT_SECONDS`, lớn hơn 0 và tối đa 120; không reset khi có chunk mới |
| Upload đang nhận/tiền xử lý/lưu | 2 | `DOCINTEL_MAX_CONCURRENT_UPLOADS`, 1–8 mỗi app process; lấy slot ngay, không có hàng đợi chờ slot |
| Connection/task HTTP server | 16 | Uvicorn `--limit-concurrency 16` trong `scripts/dev.py backend` và Docker CMD |
| OCR queue | 5 pending/running | `DOCINTEL_MAX_PENDING_RUNS`, budget SQLite hiện có, độc lập với slot upload |
| Decode/OCR | 16M pixels, một trang; pipeline 30 giây | Giữ budget hiện có; receive timeout không bao gồm tiền xử lý/lưu/OCR |

Deadline bắt đầu khi endpoint hợp lệ bắt đầu đọc body, sau khi có slot. Slot được giữ tới khi tiền xử lý và transaction upload kết thúc, kể cả client hủy request trong lúc thread đang lưu. Shutdown chờ các tác vụ upload đã nhận đủ body trước khi đóng worker. Không nhân số process/workers: nền hiện có một SQLite worker và runtime lock.
