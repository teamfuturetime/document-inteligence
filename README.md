# AI-02 — Document Intelligence cho biểu mẫu tiếng Việt

Ứng dụng dự kiến nhận tài liệu mẫu, OCR, trích xuất các trường theo schema,
cho phép người dùng kiểm tra/chỉnh sửa, validation ở backend và xuất JSON.
Chỉ dùng dữ liệu tổng hợp hoặc dữ liệu mẫu được phép sử dụng.

## Trạng thái thực tế

Ngày khảo sát: **20/10/2026**. Nhánh phát triển cá nhân: **`tuannguyen`**.

Giai đoạn 0 đã khảo sát repository và lập kế hoạch. **S1.1 đã kiểm thử:** backend
FastAPI có `GET /health`, hai test offline và kiểm tra HTTP local bằng Uvicorn.
**S1.2 đã có frontend React/TypeScript/Vite** với trang giới thiệu và trạng thái dự án;
đã kiểm tra lockfile, TypeScript, build, HTTP và render React trong Node.
Chưa kiểm tra trực quan trên trình duyệt vì công cụ trình duyệt của phiên phát triển
không khả dụng. S3.2 đã thêm OCR local và mẫu smoke tổng hợp; chưa có VLM hay golden dataset.
Code trên các nhánh remote chỉ được
đọc để tham khảo ở Giai đoạn 0, chưa được nhập vào nhánh này.

**S2.1 đã chốt đặc tả dữ liệu:** hóa đơn bán hàng tiếng Việt một trang từ dữ liệu
tổng hợp, mã `sales_invoice`, schema dự kiến `1.0.0`, gồm số hóa đơn, ngày lập,
tên người bán, tổng tiền nguyên VND và currency. Quy tắc và ranh giới dữ liệu ở
[requirements](docs/requirements.md) và [architecture](docs/architecture.md).
**S2.1a đã hiện thực hai model Pydantic canonical** `InvoiceValues` (cho phép null,
nhưng yêu cầu đủ key) và `FinalInvoiceValues` (đầy đủ giá trị hợp lệ).
Đã kiểm thử offline các ràng buộc dữ liệu. Hai model không chứa confidence/status,
và bản `FinalInvoiceValues` không tự chứng minh người dùng đã xác nhận.
Phần kiểm tra trực quan S1.2 vẫn chưa hoàn tất.

**S2.2 đã có normalization service và business validation local**: giữ bản sao input,
chuyển format nguồn đã quy định rồi kiểm tra bằng các model có sẵn. Kết quả trả lỗi
theo field với mã phân biệt schema/normalization/business; input mơ hồ không bị đoán.
Chưa tích hợp service vào API, OCR/VLM, frontend hoặc export.

**S3.1 đã có extraction contract và fake provider offline**: nhận ID/MIME/bytes,
trả raw candidates và metadata riêng, rồi dùng lại service S2.2 để tạo kết quả
canonical `sales_invoice` 1.0.0. Fake mang nhãn rõ ràng, không nhận dạng ảnh,
không tạo confidence/evidence. Riêng S3.1 không có OCR/VLM thật hoặc route extraction.

**S3.2 đã có OCR Tesseract local** trên ảnh tổng hợp PNG/JPEG, giữ text/TSV,
token/toạ độ/native score và engine/model/config metadata. Có xử lý ảnh hỏng,
ảnh trống, EXIF và timeout thực thi; chưa nối OCR vào extraction hoặc API/UI.
Hướng dẫn, license, kết quả và lỗi dấu tiếng Việt còn lại ở [OCR local](docs/ocr.md).

**S3.3.1 đã khảo sát VLM**: phần cứng, Qwen/InternVL/Gemini từ nguồn chính thức,
khuyến nghị local có điều kiện và kế hoạch benchmark/confidence ở
[khảo sát VLM](docs/vlm-survey.md). Chưa tải/chạy model hoặc đo chất lượng VLM;
khảo sát được lưu cùng benchmark offline trong phiên chốt tiến trình.

**S3.3.2a đã có benchmark runner/parser offline** cho ba mode, dùng text/response
fixture tổng hợp, labels evaluator-only và metric typed/normalized/evidence riêng.
Report ghi rõ không inference và không phải chất lượng VLM; hướng dẫn ở
[benchmark offline](docs/benchmark-offline.md). Không đổi S3.1/S3.2 hoặc schema 1.0.0.

**S3.3.2b mới có preflight**, gồm revision/checksum công bố, runtime CPU và ngân sách
tải dự kiến tại [VLM preflight](docs/vlm-preflight.md). Chưa được xác nhận cho phép
tải model/runtime; chưa có provider inference hoặc benchmark VLM thật.

## Tài liệu

- [Khảo sát repository và môi trường](docs/repository-audit.md).
- [Yêu cầu, phạm vi MVP và trạng thái 12 yêu cầu](docs/requirements.md).
- [Kiến trúc tối giản và luồng dữ liệu dự kiến](docs/architecture.md).
- [Roadmap, task nhỏ và điều kiện hoàn thành](docs/roadmap.md).
- [Cách kiểm thử và kết quả backend/frontend](docs/testing.md).
- [OCR local và mẫu tổng hợp S3.2](docs/ocr.md).
- [Khảo sát VLM và kế hoạch benchmark S3.3.1](docs/vlm-survey.md).
- [Benchmark fixture và parser/evidence adapter S3.3.2a](docs/benchmark-offline.md).
- [Preflight model/runtime S3.3.2b](docs/vlm-preflight.md).
- [Bàn giao phiên và bước tiếp theo](docs/session-handoff.md).

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

Kết quả toàn bộ backend sau S3.3.2a trên máy đã cài Tesseract/vie: **531 passed**
(463 test S1–S3.2 và 68 test benchmark offline),
không có warning. TestClient gọi app trong tiến trình; fixture chặn socket connect
trong lúc gửi request. Test schema cũng chặn kết nối mạng khi chạy.
Xem [testing.md](docs/testing.md) về coverage và giới hạn của việc chặn mạng.

Hai model chỉ nhận dữ liệu canonical: ngày ISO `YYYY-MM-DD`, tiền JSON integer,
currency đúng `VND`, mã hóa đơn là chuỗi giữ số 0 đầu, tên người bán đã ở Unicode NFC.
Input như `03/04/2026`, `125.000`, `₫` bị từ chối ở lớp này;
service S2.2 chuyển chúng trước khi gọi model. Sử dụng nội bộ:
`normalize_invoice(raw_values, source_locale="vi-VN")` trong
`app.services.normalization`, rồi `validate_invoice(result)` trong
`app.services.validation`. Kết quả có `valid`, `normalized_values`, `errors`, `warnings`.
DMY cần nguồn vi-VN được xác định; bỏ locale nghĩa chưa rõ nguồn và chỉ nhận ngày ISO.
Các hàm này chạy local trong backend, chưa có HTTP endpoint riêng.

S3.1 cung cấp hàm nội bộ `run_pipeline(document, provider, code_revision=None)`
trong `app.services.pipeline`. `document` là `DocumentInput` trong
`app.schemas.extraction` (ID, MIME PNG/JPEG, bytes không rỗng); provider là
`FakeExtractionProvider()` trong `app.providers.fake`. Constructor nhận một trong
`complete`, `partial`, `failure`, `timeout`. Bytes chỉ là dữ liệu đầu vào contract,
chưa kiểm tra nội dung/giải mã ảnh. Fake cố ý trả fixture tổng hợp không phụ thuộc ảnh.

Kết quả `status="succeeded"` có `provider_output`, `run_metadata` và `validation`;
phải kiểm tra thêm `validation.valid`, không xem chạy thành công là hóa đơn hợp lệ
hay đã được xác nhận. Kết quả `status="failed"` có error code/message cố định,
không có payload hóa đơn thành công. Confidence luôn null, evidence luôn rỗng ở fake.
Không cần chạy server, API key hoặc model; backend chưa cấu hình type checker/linter.

### OCR local S3.2

Dependency Python có thêm Pillow 13.0.0. Tesseract và model `vie` là công cụ ngoài
Python, cần cài riêng để chạy OCR thật; S3.2 dùng bản có sẵn, không sửa cài đặt hệ thống.
Chạy tại thư mục gốc, sau khi Tesseract ở PATH và có `vie.traineddata`:

```powershell
Push-Location backend
..\.venv\Scripts\python.exe -m app.ocr_cli ../data/ocr-smoke/invoice_vi.png
Pop-Location
```

CLI trả OCR JSON ra stdout, chưa trả hóa đơn canonical. Có thể thêm
`--tesseract`/`--tessdata-dir`/`--timeout`; xem [ocr.md](docs/ocr.md).
Test mặc định tự bỏ qua nhóm cần engine nếu không có môi trường. Để bắt buộc kiểm
tra OCR thật, truyền rõ đường dẫn test để pytest nạp các option từ conftest:

```powershell
.\.venv\Scripts\python.exe -m pytest -c backend/pytest.ini backend/tests -q --require-real-ocr
.\.venv\Scripts\python.exe -m pytest -c backend/pytest.ini -q -m "not ocr_real"
```

Lệnh thứ hai chạy nhóm không cần Tesseract: **456 passed, 7 deselected**.
Có thể thêm `--ocr-executable` và `--ocr-tessdata-dir` vào lệnh bắt buộc OCR thật.

### Benchmark fixture offline S3.3.2a

```powershell
Push-Location backend
..\.venv\Scripts\python.exe -m app.benchmark
Pop-Location
```

Report JSON là `fixture_simulation`, không inference hoặc đo chất lượng VLM.
Mặc định deterministic, thời gian null; `--without-labels` báo metric N/A,
`--measure` chỉ đo runner fixture. Dữ liệu, contract, mẫu số và giới hạn ở
[benchmark-offline.md](docs/benchmark-offline.md). Không cần Tesseract hoặc model
để chạy công cụ này, không cài dependency mới.

### Frontend React/TypeScript/Vite

Đã kiểm tra trên **Windows, Node.js 24.13.0, npm 11.6.2**. Yêu cầu Node
`^20.19.0 || >=22.12.0` theo Vite đã chọn; chỉ môi trường nêu trên đã được chạy thử.
Từ thư mục gốc, mở terminal riêng:

```powershell
Set-Location frontend
npm ci --no-audit --no-fund
npm run dev
```

Mở **http://127.0.0.1:5173/** để xem trang **AI-02 — Document Intelligence**,
mô tả chức năng dự kiến và trạng thái phát triển. Đây là trang giới thiệu tĩnh;
không cần backend đang chạy, không gửi API request hoặc tải tài nguyên bên ngoài.
Chưa có upload hay tích hợp AI. Nhấn `Ctrl+C` để dừng dev server.

Trong terminal khác tại `frontend/`, kiểm tra và xem bản production:

```powershell
npm run typecheck
npm run build
npm run preview
```

Mở **http://127.0.0.1:4173/** để kiểm tra bản build; `Ctrl+C` để dừng preview.
`build` chạy cả TypeScript và Vite, tạo output trong `frontend/dist/` (không commit).
Preview chỉ phục vụ kiểm tra local, chưa phải cấu hình triển khai production.
Các server chỉ bind loopback; cổng bị chiếm sẽ báo lỗi (`strictPort`). Có thể đổi cổng
bằng `npm run dev -- --port 5174` hoặc `npm run preview -- --port 4174` và đổi URL.

`package-lock.json` khóa dependency; dùng `npm ci` để cài theo lockfile. Lần cài đầu
cần Internet; khi cache đầy đủ có thể thêm `--offline` (đã kiểm tra trong S1.2).
`frontend/.npmrc` đặt cache tại `.npm-cache` trong thư mục frontend và pin dependency
khi thêm package. Không cài package global, không cần API key.
Trang hiện chưa có tương tác nghiệp vụ, nên chưa thêm framework/script unit test frontend.
Kiểm tra trực quan desktop/mobile vẫn cần thực hiện trong trình duyệt.

## Các file chính và luồng hiện tại

- `backend/app/main.py`: tạo FastAPI app và endpoint `/health` trả JSON cố định.
- `backend/tests/test_health.py`: kiểm tra GET trả JSON đúng và POST bị từ chối 405.
- `backend/pytest.ini`: đường dẫn import/test, strict config và coi warning là lỗi.
- `backend/requirements*.txt`: phiên bản runtime/test đã cài và kiểm tra tương thích.
- `backend/app/schemas/invoice.py`: hai model giá trị dùng chung ràng buộc strict;
  kiểm tra dữ liệu canonical, không normalize hoặc gọi AI.
- `backend/tests/test_schemas.py`: test required/null, kiểu/giới hạn/Unicode/ngày,
  từ chối metadata/key lạ và giữ nguyên giá trị khi round-trip JSON.
- `backend/app/services/normalization.py`: snapshot input và chuyển các format rõ ràng,
  giữ candidates/lỗi/locale/version riêng, chưa khẳng định dữ liệu hợp lệ.
- `backend/app/services/validation.py`: kiểm tra candidates theo model hiện có, giữ lỗi
  và trả kết quả cấu trúc; không sửa input hoặc tự tạo confidence.
- `backend/app/schemas/validation.py`: `FieldIssue` và `ValidationResult`.
- `backend/app/schemas/extraction.py`: input, output thô/metadata và success/failure.
- `backend/app/providers/{contracts,fake}.py`: Protocol, lỗi provider và fixture giả lập.
- `backend/app/services/pipeline.py`: kiểm tra boundary, ghi version/hash, gọi S2.2.
- `backend/tests/test_pipeline.py`: test offline contract, fake và điều phối pipeline.
- `backend/app/schemas/ocr.py`, `providers/{ocr,tesseract}.py`: OCR-only contract/adapter.
- `backend/app/ocr_cli.py`: chạy OCR local từ PNG/JPEG, không tạo API hoặc invoice fields.
- `data/ocr-smoke/`: generator, ba ảnh tổng hợp và manifest; không chứa model/font.
- `frontend/src/main.tsx`: gắn React vào phần tử `root` trong `index.html`.
- `frontend/src/App.tsx`, `styles.css`: nội dung giới thiệu/trạng thái và CSS thuần.
- `frontend/vite.config.ts`, `tsconfig.json`: React plugin và kiểm tra TypeScript strict.
- `frontend/package.json`, `package-lock.json`: scripts và dependency đã khóa.

Luồng hiện tại là HTTP client → Uvicorn → FastAPI `/health` → JSON.
Endpoint chỉ xác nhận backend đang đáp ứng; chưa xác nhận khả năng OCR/VLM.
Frontend hiện chạy độc lập: Vite → trình duyệt → React, chưa nối với luồng backend.

## Giới hạn và bước tiếp theo

Đã chọn Tesseract local cho smoke OCR; chưa chọn VLM hoặc đo chất lượng field extraction.
Confidence sẽ chỉ hiển thị khi có nguồn và cách tính rõ ràng;
không xem confidence là bảo đảm dữ liệu đúng.

Task tiếp theo duy nhất: **S3.3.2b — Runtime/model và benchmark inference thật**,
sau khi được cho phép tải/chạy; nền fixture S3.3.2a không thay bằng chứng VLM thật.
OCR adapter S3.2 đã
kiểm tra ảnh và timeout từng subprocess; pipeline extraction S3.1 giữ nguyên,
chưa tích hợp OCR/VLM thật hoặc API/review/export.
Skeleton backend/frontend đã có; giới hạn kiểm tra trực quan frontend được ghi ở trên
và trong tài liệu testing, chưa coi kết quả CLI là bằng chứng giao diện hiển thị đúng.
Mỗi lần chỉ làm task đã thống nhất, có kiểm tra và commit local;
không tự động push, tạo PR hoặc merge.
