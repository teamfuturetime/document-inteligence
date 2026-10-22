# Kiến trúc hệ thống

```text
Browser → Nginx :3000 ─┬→ React SPA
                      └→ /api (same origin)
                            ↓
                 FastAPI Backend :8000
                 ├→ Auth/CSRF/ownership
                 ├→ Service → Repository → PostgreSQL
                 ├→ StorageService → uploads volume
                 └→ AI Service :8001
                     validation → PDF/image limits → preprocessing
                     → Tesseract vie → classification → extraction
```

Router chuyển đổi HTTP/Pydantic và ánh xạ lỗi. Application service sở hữu transaction; repository chỉ thao tác ORM/flush. AI Service độc lập với schema database. Frontend gọi `/api` qua Nginx nên cookie session không cần CORS khi chạy Compose.

## Quyết định bảo mật

- Mật khẩu băm bằng scrypt với salt ngẫu nhiên; không lưu mật khẩu rõ.
- Session ngẫu nhiên nằm trong cookie HttpOnly, SameSite=Lax; database chỉ lưu SHA-256 digest của token.
- Mọi thao tác ghi tài liệu yêu cầu CSRF token. Production phải đặt `SESSION_COOKIE_SECURE=true` và dùng TLS.
- Repository lọc `owner_id`; tài liệu của người khác trả 404 để không tiết lộ ID tồn tại.
- Client không nhận `file_path`. Preview kiểm tra quyền, đúng MIME, inline và `Cache-Control: private, no-store`.
- Storage key ngẫu nhiên; absolute path, traversal và symlink escape bị chặn.

## Transaction và trạng thái

Luồng hợp lệ chính: `uploaded → processing → processed → reviewed → confirmed`; xử lý lỗi thành `failed`, có thể retry. Không review/confirm trước khi xử lý và không xử lý lại bản đã xác nhận. Extraction có unique constraint theo document và được upsert.

Upload xóa file khi DB lỗi. Processing rollback dữ liệu dở dang rồi lưu trạng thái `failed`. Filesystem và PostgreSQL không có distributed transaction nên cleanup là best-effort.

## Triển khai

Compose có `db`, `ai_service`, `backend`, `frontend`; named volume cho PostgreSQL và uploads, health checks, migration trước Uvicorn, Tesseract `vie`, và Nginx SPA fallback.
