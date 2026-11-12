# Cài, chạy, demo và phục hồi

## Native

[README gốc](../../README.md) là nguồn duy nhất cho runtime pins, setup, cấu hình, dev servers và checks. Dùng `python scripts/dev.py setup`, `models`, rồi `backend`/`frontend` ở hai terminal. Không copy chuỗi lệnh cũ từ báo cáo foundation. Backend đọc `.env` mẫu tesseract; inference không tải model hoặc fallback fixture. Chi tiết dưới đây tập trung demo/backup/triage, không định nghĩa một cách cài khác.

## Demo có thể lặp lại

1. Chọn hóa đơn, nguồn synthetic, ảnh `data/product/images/hoa_don_007.png`; xác nhận chính sách data rồi upload.
2. Đợi OCR xong; kiểm số hóa đơn 0041007, ngày 2026-10-08, đơn vị Giả Lập 107, tổng 1000000 và VND theo ảnh. Đây là dữ liệu mẫu, không hóa đơn thật.
3. Chọn trường để thấy evidence; thử xóa tên người bán, lưu nháp và reload: null phải được giữ; confirm bị chặn.
4. Điền lại theo ảnh, lưu, xác nhận và xuất JSON từ server. File có revision khớp màn hình; review thay đổi sau confirm trở lại draft.
5. Mở hai tab cùng một revision, lưu tab đầu rồi lưu tab thứ hai: 409 và UI cho đối chiếu, không tự mất edits.
6. Chạy OCR lại, chọn lịch sử run cũ: review cũ còn nhưng chỉ đọc. Export run cũ bị từ chối.
7. Thử đơn đề nghị `data/fixtures/images/fixture_001.png` trong workspace thật. Cùng ảnh synthetic có thể được OCR thật; không đồng nghĩa dùng predictions fixture.

```powershell
uv run --project backend --locked python scripts/verify_product.py
```

Lệnh này thực sự gọi Tesseract và HTTP workflow, fail nếu không có môi trường; không skip hoặc fallback. Nó dùng DB tạm, scripted review chỉ kiểm workflow, không được báo như accuracy AI.

## Backup và khôi phục

```powershell
uv run --project backend --locked python scripts/backup_runtime.py runtime/app runtime/backups/demo-001
uv run --project backend --locked python scripts/backup_runtime.py runtime/backups/demo-001 runtime/restored-app --restore
```

Destination phải là thư mục mới ngoài source. SQLite backup API tạo snapshot nhất quán; files nguồn/preview bất biến được copy và hash. Restore kiểm tất cả hashes trước khi copy, không đè runtime đang chạy. Trỏ DOCINTEL_RUNTIME_DIR vào thư mục vừa restore rồi khởi động app. Không có chính sách tự xóa uploads/review; người dùng bảo quản và dọn runtime sau khi backup. Không chạy cleanup lên thư mục nhóm bằng wildcard.

## Docker local

```powershell
docker compose up --build
docker compose down
```

Backend image cài Tesseract từ apt và fetch đúng model lock trong build, chạy user không phải root; named volume giữ SQLite/uploads sau `down`. Không dùng `down -v` nếu cần giữ dữ liệu. Hai cổng chỉ bind loopback. Cấu hình Docker cần được build/run trên máy có Engine; kiểm YAML không chứng minh container đã chạy.

## Phạm vi vận hành

Local/single-user, chưa có authentication hoặc tenant isolation. Không expose công khai. Không dùng hồ sơ thật; chỉ synthetic/sample có quyền. Không log source text/native stderr, không gửi dữ liệu sang API AI ngoài. Lỗi mất provider không tự đổi engine hoặc dùng fixture. Timeouts/limits không phải SLA đã đo cho mọi máy.

Upload mặc định có tổng receive deadline 30 giây và hai slot từ lúc nhận tới khi lưu; Uvicorn trong dev/Docker giới hạn 16 connection/task. Lỗi `UPLOAD_TIMEOUT`/`UPLOAD_BUSY` có thể thử lại với cùng idempotency key. [Budget, header/stream errors và giới hạn buffer trước ASGI](../operations/upload-ingress.md) phân biệt receive timeout với deadline OCR và queue SQLite.
