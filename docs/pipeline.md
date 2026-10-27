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
      → validate → PDF/image normalization + bounded candidates
      → Tesseract data (word confidence + coordinates)
      → layout reconstruction (page/block/line/table/columns)
      → rule classification → regex extraction → confidence assessment
  → lưu raw OCR + structured pages trong JSON sẵn có → status processed
  → PATCH review → status reviewed
  → POST confirm → status confirmed
```

Trạng thái lỗi AI là `failed`; backend trả 502 mà không lộ exception nội bộ.
Backend không retry tự động để tránh nhân tải OCR ngoài kiểm soát. Request ID được
trả qua header. Temporary file của AI service luôn được xóa trong `finally`.

Backend tạo `ocr_text_cleaned` khi serialize response và vẫn giữ `ocr_text` cùng
`ocr_text_raw` để tương thích/đối chiếu. `GET /documents/{id}` trả thêm `ocr_pages`;
các endpoint danh sách không mang layout payload lớn.

Retention dùng `expires_at` (UTC) làm nguồn sự thật. Chạy định kỳ:

```bash
cd backend
python -m app.retention_cli
```

Nếu xóa file lỗi, record được giữ để lần chạy sau thử lại. Cascade xóa extraction.
Giá trị ngày lưu giữ lấy từ `DATA_RETENTION_DAYS`, mặc định 30, không hardcode tham
số riêng của bài tập.
