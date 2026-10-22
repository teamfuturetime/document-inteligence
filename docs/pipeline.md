# Pipeline xử lý tài liệu

```text
POST /api/v1/documents
  → kiểm tra extension/MIME
  → ghi chunk + giới hạn dung lượng
  → kiểm tra magic bytes
  → lưu storage key + metadata (uploaded)

POST /api/v1/documents/{id}/process
  → status processing
  → AI /process
      → validate → PDF/image preprocessing → Tesseract OCR
      → rule classification → regex extraction → confidence assessment
  → lưu OCR/extraction → status processed
  → PATCH review → status reviewed
  → POST confirm → status confirmed
```

Trạng thái lỗi AI là `failed`; backend trả 502 mà không lộ exception nội bộ.
Backend không retry tự động để tránh nhân tải OCR ngoài kiểm soát. Request ID được
trả qua header. Temporary file của AI service luôn được xóa trong `finally`.

Retention dùng `expires_at` (UTC) làm nguồn sự thật. Chạy định kỳ:

```bash
cd backend
python -m app.retention_cli
```

Nếu xóa file lỗi, record được giữ để lần chạy sau thử lại. Cascade xóa extraction.
Giá trị ngày lưu giữ lấy từ `DATA_RETENTION_DAYS`, mặc định 30, không hardcode tham
số riêng của bài tập.
