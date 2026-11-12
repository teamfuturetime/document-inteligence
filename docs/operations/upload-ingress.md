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

## Từ chối và retry

| HTTP / code | Trường hợp |
| --- | --- |
| 400 / `INVALID_CONTENT_LENGTH` | Content-Length không phải 1–20 chữ số ASCII, lặp header, hoặc đi cùng Transfer-Encoding |
| 400 / `UPLOAD_LENGTH_MISMATCH` | Số byte ASGI thực nhận khác Content-Length |
| 400 / `UPLOAD_DISCONNECTED` | Server báo disconnect trước khi nhận đủ body; client đã đóng socket có thể không nhận response |
| 408 / `UPLOAD_TIMEOUT` | Hết tổng thời gian nhận, kể cả không gửi body hoặc gửi nhỏ giọt |
| 413 / `FILE_TOO_LARGE` | Content-Length hoặc tổng byte thực nhận vượt cap |
| 429 / `UPLOAD_BUSY` | Không còn slot upload; chưa đọc body |
| 429 / `QUEUE_FULL` | Nhận đủ body nhưng queue OCR đã đầy, giữ semantics hiện có |

Header Content-Length được kiểm tra trước khi đọc body; thiếu header vẫn được chấp nhận và kiểm byte thực tế (ví dụ chunked). Byte vượt cap bị từ chối trước khi nối vào buffer. Guard trả envelope lỗi hiện có với request ID; HTTP/1 thêm `Connection: close` để không tái sử dụng kết nối còn body chưa đọc. Lỗi parser/protocol và 503 do Uvicorn concurrency limit xảy ra trước app, có thể không dùng JSON envelope này.

Từ chối ở receive/admission không thêm document/run/event hoặc source/preview. DB và thư mục runtime rỗng có thể đã được khởi tạo khi app startup. Timeout, disconnect và cancellation trong lúc nhận giải phóng slot; các request bị từ chối không chiếm idempotency key. Khi tác vụ lưu đã bắt đầu sau body hoàn chỉnh, mất response không đồng nghĩa rollback: retry cùng `Idempotency-Key` và cùng ảnh/type/origin lấy lại document hiện có, kể cả OCR queue đầy. Nội dung khác cùng key vẫn 409. Retry lúc các slot receive đều bận có thể nhận `UPLOAD_BUSY`; thử lại sau, không bỏ admission để bypass budget.

## Ingress và giới hạn bộ nhớ

Đường chạy chuẩn bind `127.0.0.1`; Docker bind trong container nhưng Compose chỉ publish loopback. Nếu chạy Uvicorn trực tiếp, giữ `--host 127.0.0.1 --limit-concurrency 16` cùng một worker. Limit Uvicorn tính cả connection/task khác, nên client giữ connection cũng tiêu tốn capacity.

App không thể giới hạn allocation xảy ra trước ASGI `receive`: kernel, Uvicorn/parser hoặc proxy có thể đã buffer/chia chunk trước khi endpoint nhìn thấy. Deadline này cũng không bao gồm thời gian gửi header hoặc body đã bị proxy buffer trước app. Uvicorn concurrency limit giúp chặn thêm connection/task nhưng không phải header timeout, socket memory cap hay bộ bảo vệ public ingress. Chưa kiểm chứng reverse proxy; không suy ra cấu hình public từ đường chạy local.

Không coi `2 × 5 MiB` là trần RSS: còn buffer server, bản sao `bytearray` → `bytes`, decode PNG/JPEG và preview, thread/native process, DB và model. Giữ pixel/native deadline hiện có. Không tăng queue/slot tùy tiện để làm đẹp throughput.

## Kiểm chứng

`backend/tests/test_upload_ingress.py` dùng ASGI events để kiểm tra cả length giả mà HTTP parser có thể chặn trước app, nhiều chunk, đúng/vượt cap, không gửi hoặc trickle body, disconnect, cancellation khi nhận/lưu, slot reuse và idempotent retry khi queue đầy. Bộ tests sản phẩm hiện có vẫn kiểm tra upload đồng thời và cleanup sau queue reject.

Đo HTTP thật trên macOS/Linux (POSIX):

```sh
uv run --project backend --locked python scripts/check_upload_ingress.py --output runtime/verification/upload-ingress-new-run.json
```

Output phải là đường dẫn mới. Script mở server subprocess trên cổng loopback ngẫu nhiên với DB tạm; provider unconfigured, không bật OCR/model. Byte cap bằng mặc định 5 MiB, hai slot, receive timeout giảm còn 0,5 giây để thử lỗi nhanh, Uvicorn limit 16. Workload: khai báo quá lớn chưa gửi body, chunked quá lớn, hai upload nhỏ giọt và request thứ ba, disconnect, sau đó một request hoàn chỉnh để kiểm slot được dùng lại. Request cuối mong đợi `503 PROVIDER_UNAVAILABLE` vì không cấu hình OCR; không gọi đây là native OCR check.

Report ghi latency từng ca, RSS high-water của riêng server process, số asyncio tasks/slot, số document/file, môi trường và source hashes. Endpoint `/probe/metrics` chỉ tồn tại trong app đo của script, không thêm vào app sản phẩm. Đây là một lần đo workload giới hạn; không phải stress test, p95/SLA hoặc benchmark độ chính xác. Native OCR và browser workflow dùng các checks riêng trong README.
