# Kiểm thử backend S1.1

## Môi trường và dependency

Đã kiểm tra ngày 20/10/2026 trên Windows, CPython 3.13.7 trong `.venv` riêng.
Phiên bản trực tiếp: FastAPI 0.153.0, Uvicorn 0.54.0, pytest 9.1.1 và HTTPX2 2.15.1.
Tất cả dependency runtime/test đang dùng được pin, gồm dependency gián tiếp,
trong `backend/requirements.txt` và `backend/requirements-dev.txt`.

Đã kiểm tra metadata package đã cài: FastAPI/pytest dùng MIT;
Uvicorn/HTTPX2 dùng BSD-3-Clause, tương ứng các trang
[FastAPI](https://pypi.org/project/fastapi/), [pytest](https://pypi.org/project/pytest/),
[Uvicorn](https://pypi.org/project/uvicorn/), [HTTPX2](https://pypi.org/project/httpx2/).
Các package chạy local, không cần API key hoặc dịch vụ tính phí.

S1.1 chỉ dùng FastAPI cơ bản và Uvicorn cơ bản; không cài extras `standard`.
OpenTelemetry API là dependency gián tiếp của FastAPI được pin theo metadata;
app không cấu hình instrumentation hoặc exporter.

Lần cài đầu cần Internet hoặc package có sẵn; **offline áp dụng cho lúc chạy test**,
không cam kết cài mới từ Git mà không có kho package. Xem README để tạo `.venv`.
Chưa xác minh bộ pin trên OS/Python khác hoặc checkout sạch; kiểm tra checkout sạch
toàn dự án thuộc S6.1.

## Test API trong tiến trình

Tại thư mục gốc, sau khi cài dependency:

```powershell
.\.venv\Scripts\python.exe -m pytest -c backend/pytest.ini -q
.\.venv\Scripts\python.exe -m pip check
```

`backend/pytest.ini` đặt import path là `backend`, tìm test trong `backend/tests`,
kiểm tra config/marker chặt chẽ và coi warning là lỗi.

Hai test trong `backend/tests/test_health.py` kiểm tra:

- `GET /health` trả status 200, content type JSON và đúng `{"status":"ok"}`.
- `POST /health` trả 405 và công bố GET là method được phép.

TestClient gọi ASGI app trong cùng tiến trình, không mở server HTTP thật.
Fixture chặn `socket.socket.connect`, `connect_ex` và `socket.create_connection`
trong lúc test gửi request; không cần Internet, OCR/VLM hoặc API key.
Windows asyncio cần socketpair loopback để khởi tạo event loop nên TestClient được
khởi tạo trước khi chặn socket, và bỏ chặn trước khi đóng client.
Việc chặn này kiểm tra request health, không phải sandbox cho mọi hoạt động Python
hoặc bằng chứng cấm mạng ở thời điểm import/startup.

## HTTP smoke check

Chạy Uvicorn theo README, rồi ở terminal PowerShell khác:

```powershell
$response = Invoke-WebRequest -Uri http://127.0.0.1:8000/health
if ($response.StatusCode -ne 200) { throw 'Unexpected HTTP status' }
if (($response.Content | ConvertFrom-Json).status -ne 'ok') { throw 'Unexpected body' }
```

Trong lượt S1.1 đã chạy Python inline khởi động đúng lệnh Uvicorn ở README
bằng subprocess, chỉ gọi `127.0.0.1:8000/health`, kiểm tra status/content type/JSON,
và dừng tiến trình con trong `finally`. Không để server chạy nền sau kiểm tra.
Smoke check này dùng socket local, tách khỏi bộ test in-process.

## Kết quả và xử lý lỗi đã gặp

- Lần cài pip đầu bị sandbox chặn kết nối (`WinError 10013`); cài thành công sau khi cấp quyền.
- Test đầu dừng ở collection do Starlette 1.9.0 deprecate HTTPX cũ. Đổi sang HTTPX2
  theo [tài liệu TestClient](https://starlette.dev/testclient/), gỡ HTTPX cũ và dependency riêng;
  giữ nguyên chính sách warning là lỗi.
- Fixture chặn socket ban đầu chặn cả socketpair khởi tạo event loop Windows.
  Chuyển phạm vi chặn sang lúc gửi request để bảo vệ kiểm tra offline đúng mục đích.
- Chạy lại pytest: **2 passed**, không có warning; `pip check`: **No broken requirements found**.
- Uvicorn khởi động thành công; HTTP thật: **200**, `application/json`, `{"status":"ok"}`;
  tiến trình kiểm tra đã dừng.

Health chỉ báo backend sống. Chưa có test frontend, schema nghiệp vụ, upload,
OCR/VLM hoặc evaluation; S1.1 không xác nhận Giai đoạn 1 đã hoàn thành.
