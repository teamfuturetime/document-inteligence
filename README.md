# Document Intelligence cho biểu mẫu tiếng Việt

Ứng dụng full-stack xử lý PDF/ảnh theo luồng tải lên → OCR Tesseract tiếng Việt → phân loại/trích xuất theo luật → người dùng rà soát → xác nhận. Hệ thống gồm React, FastAPI, AI Service, PostgreSQL và lưu trữ file riêng tư.

## Tính năng

- Đăng ký, đăng nhập, đăng xuất bằng session HttpOnly; CSRF token bảo vệ thao tác ghi.
- Mỗi người dùng chỉ xem, xử lý, sửa, xác nhận, tải/xuất và xóa tài liệu của mình.
- Dashboard thật, upload kéo-thả, tìm kiếm/lọc/phân trang, preview PDF/ảnh, chỉnh sửa field và xuất JSON.
- Tesseract `vie`, xử lý PDF nhiều trang, chống file giả định dạng, giới hạn dung lượng/trang/pixel.
- Upload PDF, PNG, JPG/JPEG, WebP, BMP và TIF/TIFF (kể cả TIFF nhiều trang), tối đa 10 MB; preview BMP/TIFF bằng PNG theo trang, giữ nguyên file gốc.
- Tự động trích xuất trường hóa đơn, CCCD và đơn/biểu mẫu bằng rule từ OCR; người dùng rà soát, sửa và xác nhận trước khi xuất JSON. Xem [chiến lược và kết quả kiểm thử extraction](docs/automatic-extraction.md).
- PostgreSQL + Alembic; extraction được upsert nên xử lý lại không tạo bản ghi trùng.
- Docker Compose phục vụ UI tại `http://localhost:3000`, API tại `http://localhost:8000` và Swagger tại `http://localhost:8000/docs`.

## Khởi động nhanh bằng PowerShell

```powershell
Copy-Item .env.example .env
$env:DEMO_USER_EMAIL = "demo@example.test"
$env:DEMO_USER_NAME = "demo"
$env:DEMO_USER_PASSWORD = "Thay-bang-mat-khau-demo-2026"
docker compose up --build -d
docker compose exec backend python -m app.seed_demo
```

Không có mật khẩu demo mặc định trong source. Xem quy trình đầy đủ và kịch bản trình bày tại [docs/demo-guide.md](docs/demo-guide.md).

## Phát triển và kiểm thử

Backend/AI nhắm Python 3.12; frontend nhắm Node.js 20.

```powershell
python -m pytest -q
python -m compileall -q backend ai_service tests
Set-Location frontend
npm.cmd install
npm.cmd run build
```

## Kiến trúc

```text
Browser → Nginx :3000 ─┬→ React SPA
                      └→ /api → FastAPI :8000 → PostgreSQL
                                           ├→ private upload volume
                                           └→ AI Service :8001 → OpenCV/PyMuPDF/Tesseract vie
```

Confidence phân loại là điểm heuristic 0–100, không phải xác suất hoặc độ chính xác đã hiệu chuẩn. Các giới hạn và trạng thái xác minh thực tế được ghi trong [docs/demo-guide.md](docs/demo-guide.md).

Chi tiết giới hạn ảnh, kiểm thử và hướng dẫn kiểm tra định dạng upload: [docs/upload-image-formats.md](docs/upload-image-formats.md).
