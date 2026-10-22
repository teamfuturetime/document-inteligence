# Hướng dẫn demo Document Intelligence

## 1. Điều kiện

- Docker Desktop có Docker Compose, hoặc Python 3.12 + PostgreSQL 16 + Tesseract `vie` + Node.js 20.
- Không dùng dữ liệu cá nhân thật. File demo nên là biểu mẫu tổng hợp với tên/số định danh hư cấu.

## 2. Cấu hình và khởi động bằng Docker

Trong PowerShell tại thư mục repository:

```powershell
Copy-Item .env.example .env
$env:DEMO_USER_EMAIL = "demo@example.test"
$env:DEMO_USER_NAME = "demo"
$env:DEMO_USER_PASSWORD = "Thay-bang-mat-khau-demo-2026"
docker compose up --build -d
docker compose exec backend python -m app.seed_demo
docker compose ps
```

Mở `http://localhost:3000`. API ở `http://localhost:8000`, Swagger ở `http://localhost:8000/docs`.

## 3. Chạy phát triển không dùng Docker

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt -r backend\requirements-dev.txt -r ai_service\requirements.txt
Copy-Item .env.example .env
Set-Location backend
alembic upgrade head
$env:DEMO_USER_EMAIL = "demo@example.test"
$env:DEMO_USER_NAME = "demo"
$env:DEMO_USER_PASSWORD = "Thay-bang-mat-khau-demo-2026"
python -m app.seed_demo
uvicorn app.main:app --reload --port 8000
```

Mở terminal thứ hai tại gốc repository:

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn ai_service.main:app --reload --port 8001
```

Mở terminal thứ ba:

```powershell
Set-Location frontend
npm.cmd install
npm.cmd run dev
```

## 4. Kịch bản trình bày với giảng viên

1. Đăng nhập bằng tài khoản vừa seed hoặc đăng ký tài khoản mới.
2. Mở Tổng quan để chỉ ra số liệu lấy trực tiếp từ backend.
3. Chọn Tải lên, kéo một PDF/PNG/JPEG tổng hợp dưới 10 MB và bấm **Tải lên và xử lý**.
4. Chờ chỉ báo bất định; hệ thống không bịa phần trăm tiến độ AI.
5. Ở trang chi tiết, đối chiếu bản gốc bên trái với OCR và trường trích xuất bên phải.
6. Giải thích điểm phân loại là heuristic, không phải xác suất đã hiệu chuẩn.
7. Sửa một trường, lưu, rồi xác nhận kết quả.
8. Xuất JSON và kiểm tra không có đường dẫn filesystem hay secret.
9. Quay lại danh sách, tìm theo tên hoặc OCR, mở lại tài liệu để chứng minh dữ liệu đã lưu.
10. Đăng xuất và thử mở `/documents` để thấy chuyển về trang đăng nhập.

## 5. Xóa dữ liệu demo

Lệnh sau xóa cả volume PostgreSQL và file upload nên chỉ dùng cho môi trường demo:

```powershell
docker compose down -v
```

## 6. Kết quả mong đợi và xử lý sự cố

- Tài liệu đi qua `uploaded → processing → processed → reviewed → confirmed`; lỗi OCR thành `failed` và có thể thử lại.
- Nếu AI service `degraded`, kiểm tra `docker compose logs ai_service` và gói `tesseract-ocr-vie`.
- Nếu migration lỗi, xem `docker compose logs backend`; không sửa migration đã áp dụng.
- Nếu PDF không hiển thị, kiểm tra cookie đăng nhập và phản hồi endpoint preview.

## 7. Giới hạn

- Bộ phân loại/trích xuất dựa trên luật và OCR Tesseract; chưa có tập đánh giá đủ lớn để tuyên bố độ chính xác tổng quát.
- Migration để `owner_id` nullable nhằm bảo toàn dữ liệu cũ; bản ghi cũ chưa gán chủ sẽ không hiển thị cho người dùng.
- Chưa có antivirus, rate limiting, TLS hoặc object storage cho production.
- Xử lý AI đồng bộ theo request; production nên chuyển sang hàng đợi tác vụ.
