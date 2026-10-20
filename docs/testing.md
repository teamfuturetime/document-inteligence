# Kiểm thử skeleton S1.1–S1.2

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

## Frontend S1.2 — môi trường và cách chạy

Đã kiểm tra ngày 20/10/2026 trên Windows, Node.js **24.13.0**, npm **11.6.2**.
Metadata npm được đọc trước khi cài: Vite **8.3.4**, React plugin **6.1.2**
yêu cầu Node `^20.19.0 || >=22.12.0`; Node hiện tại đáp ứng.
React/ReactDOM **19.3.1**, TypeScript **7.0.2**, type definitions React/ReactDOM
**19.3.0** được pin trực tiếp; dependency gián tiếp và integrity nằm trong lockfile.
Theo metadata npm, TypeScript dùng Apache-2.0, các dependency trực tiếp còn lại dùng MIT.
Tham khảo [Vite getting started](https://vite.dev/guide/),
[React với Vite](https://react.dev/learn/build-a-react-app-from-scratch) và metadata
đã cài trong `frontend/node_modules/*/package.json` khi cần rà soát phiên bản.

Từ thư mục gốc, chuyển vào frontend:

```powershell
Set-Location frontend
npm ci --no-audit --no-fund
npm run typecheck
npm run build
npm run dev
```

Mở `http://127.0.0.1:5173/`. Trong terminal khác tại `frontend/`,
`npm run preview` phục vụ bản build ở `http://127.0.0.1:4173/`.
Các server dùng loopback và `strictPort`; `Ctrl+C` để dừng.
Xem README để đổi cổng nếu đang bị chiếm.

## Frontend S1.2 — kết quả thực tế và giới hạn

- Cài package từ npm thành công sau khi cấp quyền mạng; lần thử sandbox ban đầu lỗi
  `EACCES` khi truy cập registry. Không cập nhật Node/npm hoặc cấu hình global.
  Cache npm đặt trong repo qua `frontend/.npmrc`.
- `npm ci --offline --no-audit --no-fund`: đạt, cài lại **24 package** từ cache theo
  lockfile. Lần cài mới khi chưa có cache vẫn cần Internet.
- `npm run typecheck`: đạt. `npm run build`: đạt (chạy TypeScript rồi Vite).
  Output có `dist/index.html` và JS/CSS bundle; `dist/` được Git bỏ qua.
- `npm ls --depth=0`: đúng bảy dependency trực tiếp, không có lỗi dependency tree.
- Dev server: HTTP 200 cho HTML, `src/main.tsx`, `src/App.tsx` và CSS.
  Python/backend không cần chạy để phục vụ frontend.
- Smoke check inline dùng Vite `ssrLoadModule` và React `renderToStaticMarkup` trong Node:
  tên dự án, trạng thái giai đoạn và các mục chưa triển khai được render đúng;
  không có form/input/button upload. Đây là kiểm tra render trong Node,
  không thêm SSR vào sản phẩm và không kiểm chứng việc mount/hydrate trong trình duyệt.
- Production preview: HTTP 200 cho HTML và cả hai JS/CSS asset được tham chiếu.
  Đã dừng dev/preview sau kiểm tra, không còn listener ở cổng 5173/4173.
- Chạy lại backend: `python -m pytest -c backend/pytest.ini -q` bằng Python trong
  `.venv`: **2 passed**. `git diff --exit-code 2d78293 -- backend`: không có thay đổi.
- Smoke script ban đầu bị PowerShell thay ký tự Unicode khi pipe sang Node;
  đổi chuỗi kiểm tra sang Unicode escape và chạy lại đạt. Source frontend đọc UTF-8 đúng.

**Chưa kiểm tra trực quan:** inventory trình duyệt của công cụ trả danh sách rỗng;
thử mở dev server bằng in-app browser trả `Browser is not available: iab`.
Chưa xác nhận bố cục desktop/mobile, lỗi console hoặc việc React mount trong browser.
Typecheck/build/HTTP/render ở Node không thay thế bằng chứng đó.
Kiểm tra thủ công cần mở URL ở README, xác nhận tiêu đề/mô tả/trạng thái tiếng Việt,
thử chiều rộng desktop và mobile, kiểm tra console rồi ghi kết quả thực tế.

Chưa có unit test frontend hoặc script `test`: trang tĩnh chưa có tương tác nghiệp vụ,
không thêm test framework chỉ để kiểm tra text cố định. Khi có upload/review ở S4,
thêm test cho các tương tác quan trọng theo roadmap. Chưa chạy E2E hay gọi API/AI.
