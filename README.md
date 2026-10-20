# AI-02 — Document Intelligence cho biểu mẫu tiếng Việt

Ứng dụng dự kiến nhận tài liệu mẫu, OCR, trích xuất các trường theo schema,
cho phép người dùng kiểm tra/chỉnh sửa, validation ở backend và xuất JSON.
Chỉ dùng dữ liệu tổng hợp hoặc dữ liệu mẫu được phép sử dụng.

## Trạng thái thực tế

Ngày khảo sát: **20/10/2026**. Nhánh phát triển cá nhân: **`tuannguyen`**.

Giai đoạn 0 đã khảo sát repository và lập kế hoạch. **S1.1 đã kiểm thử:** backend
FastAPI có `GET /health`, hai test offline và kiểm tra HTTP local bằng Uvicorn.
Chưa có frontend, OCR, VLM hay bộ dữ liệu. Code trên các nhánh remote chỉ được đọc
để tham khảo ở Giai đoạn 0, chưa được nhập vào nhánh này.

## Tài liệu

- [Khảo sát repository và môi trường](docs/repository-audit.md).
- [Yêu cầu, phạm vi MVP và trạng thái 12 yêu cầu](docs/requirements.md).
- [Kiến trúc tối giản và luồng dữ liệu dự kiến](docs/architecture.md).
- [Roadmap, task nhỏ và điều kiện hoàn thành](docs/roadmap.md).
- [Cách kiểm thử và kết quả S1.1](docs/testing.md).

## Cài đặt, chạy và kiểm tra

Đã kiểm tra backend trên **Windows, CPython 3.13.7**. Chạy các lệnh PowerShell
dưới đây tại thư mục gốc repository. Dùng trực tiếp Python trong `.venv`, không cần
activate môi trường hoặc thay đổi execution policy.

### Cài dependency

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
.\.venv\Scripts\python.exe -m pip check
```

Lần cài đầu cần Internet nếu package chưa có sẵn. Runtime và dependency gián tiếp
được pin trong `backend/requirements.txt`; `requirements-dev.txt` dùng lại runtime
và thêm pytest, HTTPX2 cùng dependency test. Chỉ chạy server thì cài
`-r backend/requirements.txt`. Chưa kiểm chứng bộ pin trên hệ điều hành/Python khác.
Không cần Node, Tesseract, model, API key hoặc dịch vụ AI cho S1.1.

### Chạy backend

Terminal thứ nhất:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Terminal thứ hai:

```powershell
$response = Invoke-WebRequest -Uri http://127.0.0.1:8000/health
$response.StatusCode
$response.Content
```

Kết quả mong đợi: `200` và `{"status":"ok"}`. Nhấn `Ctrl+C` ở terminal thứ nhất
để dừng server. Nếu cổng 8000 đang được dùng, chọn cổng khác bằng `--port`
và đổi URL kiểm tra tương ứng.

### Kiểm thử offline

Sau khi cài dependency, không cần chạy Uvicorn hay có kết nối Internet:

```powershell
.\.venv\Scripts\python.exe -m pytest -c backend/pytest.ini -q
git diff --check
```

Kết quả đã chạy: **2 passed**, không có warning. TestClient gọi app trong tiến trình;
fixture chặn socket connect trong lúc gửi request. Xem [testing.md](docs/testing.md)
về cách kiểm tra và giới hạn của việc chặn mạng.

## Các file chính và luồng hiện tại

- `backend/app/main.py`: tạo FastAPI app và endpoint `/health` trả JSON cố định.
- `backend/tests/test_health.py`: kiểm tra GET trả JSON đúng và POST bị từ chối 405.
- `backend/pytest.ini`: đường dẫn import/test, strict config và coi warning là lỗi.
- `backend/requirements*.txt`: phiên bản runtime/test đã cài và kiểm tra tương thích.

Luồng hiện tại là HTTP client → Uvicorn → FastAPI `/health` → JSON.
Endpoint chỉ xác nhận backend đang đáp ứng; chưa xác nhận khả năng OCR/VLM.

## Giới hạn và bước tiếp theo

Chưa chọn OCR/VLM provider, chưa đo chất lượng nhận dạng hay extraction.
Confidence sẽ chỉ hiển thị khi có nguồn và cách tính rõ ràng;
không xem confidence là bảo đảm dữ liệu đúng.

Task tiếp theo: **S1.2 — frontend React/TypeScript/Vite chạy local**.
Giai đoạn 1 chưa hoàn thành vì frontend chưa được triển khai.
Mỗi lần chỉ làm task đã thống nhất, có kiểm tra và commit local;
không tự động push, tạo PR hoặc merge.
