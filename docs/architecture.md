# Kiến trúc hiện tại

## Thành phần và phụ thuộc

```text
HTTP client
   │
   ▼
Backend Router ──► Document/Upload Service ──► Repository ──► PostgreSQL
                              │
                              ├──► StorageService ──► uploads volume
                              └──► AI Service /process
                                         │
                                         ▼
                       validation → preprocessing → OCR
                       → classification → extraction → JSON
```

Router chỉ chuyển đổi HTTP/Pydantic và ánh xạ lỗi. Application service điều phối
use case và sở hữu commit/rollback. Repository chỉ thao tác ORM/flush. AI service
không import model hoặc schema database của backend. Đây là phân tầng và tách
biệt mối quan tâm theo Lecture 04; dependency đi từ tầng cao xuống abstraction
nhỏ, dễ thay trong test.

## Quyết định chính

- `file_path` hiện lưu storage key ngẫu nhiên, không lưu path do client cung cấp.
  Storage root được resolve một lần; absolute path, traversal và symlink escape bị chặn.
- Upload ghi từng chunk 1 MiB và dừng ngay khi vượt `MAX_UPLOAD_SIZE_MB`.
- `expires_at` là nguồn sự thật duy nhất cho retention và luôn là UTC aware ở
  Python. Cleanup xóa quan hệ con qua cascade, có thể chạy lại khi file không tồn tại.
- Confidence của classifier ghi rõ `confidence_type=heuristic`, cùng raw score,
  matched rules và `needs_review`; hòa điểm trả `unknown`.
- Tesseract + `vie` là OCR mặc định duy nhất được cài trong image. Paddle chỉ có
  thể dùng khi người vận hành tự cài dependency; không quảng bá là fallback sẵn có.

## Transaction và lỗi

Service commit ở cuối mỗi thay đổi logic. Upload xóa file nếu DB flush/commit lỗi.
Processing rollback thay đổi dở dang và chuyển trạng thái sang `failed`. Filesystem
và PostgreSQL không hỗ trợ atomic transaction chung; cleanup vì vậy dùng bù trừ
best-effort và log metadata không chứa OCR text/PII.

Mỗi HTTP response có `X-Request-ID`. Exception không dự kiến trả thông báo chung;
log không ghi nội dung tài liệu. Request validation trả 400/413; lỗi AI upstream trả 502.

## Deploy

Compose thực tế gồm `db`, `ai_service`, `backend`, named volume cho PostgreSQL và
uploads, health check và dependency condition. Backend chạy Alembic trước Uvicorn.
Frontend chưa có source/package manifest nên không nằm trong Compose.

## Liên hệ nguyên lý môn học

- Lecture 04: ranh giới Router → Service → Repository → Database; AI service độc lập;
  contract HTTP và typed schema rõ ràng.
- Lecture 05: hàm có một trách nhiệm, validation tập trung, không commit rải rác,
  cấu hình qua environment, lỗi/log nhất quán, test cho boundary và security case.
