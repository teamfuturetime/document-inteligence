# Kiểm thử backend và frontend

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

Health chỉ báo backend sống. Ở thời điểm S1.1 chưa có test frontend, schema nghiệp vụ, upload,
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

## Schema canonical S2.1a

Môi trường giữ nguyên: Windows, Python 3.13.7, Pydantic 2.14.1, pytest 9.1.1
trong `.venv`. Không thêm hoặc đổi dependency. Hai model trong
`backend/app/schemas/invoice.py` theo contract `sales_invoice` 1.0.0 ở requirements.

Lệnh đã chạy tại thư mục gốc, đúng README:

```powershell
.\.venv\Scripts\python.exe -m pytest -c backend/pytest.ini -q
```

Kết quả thực tế: **209 passed in 0.68s**, không có warning:
**207 test schema**, **2 test health**. Không cần server, Internet, API key hoặc model AI.
Fixture tại module test schema chặn socket connect/connect_ex/create_connection trong
lúc test chạy; health test giữ fixture riêng để khởi tạo event loop Windows đúng cách.
Đây không phải bằng chứng cấm mạng toàn bộ tiến trình ở thời điểm import.

| Nhóm | Các quy tắc đã được kiểm thử |
| --- | --- |
| Giá trị chuẩn | Ví dụ hợp lệ, giữ nguyên khi dump/parse JSON, đủ năm key, không tự thêm default. |
| Thiếu/null | Từng key null và tất cả null được nhận ở `InvoiceValues`; bỏ bất kỳ key nào đều lỗi ở cả hai model; null bị từ chối ở `FinalInvoiceValues`. |
| Số hóa đơn | Giữ `0000123`, hoa/thường và dấu phân cách cho phép; độ dài 1/100 hợp lệ, 101 bị từ chối; từ chối số/bytes/bool, khoảng trắng/control, ký tự ngoài ASCII pattern. |
| Ngày | ISO đúng, năm 0001/9999, ngày nhuận 2024/2000; từ chối 1900-02-29, 2026-02-29, 2026-04-31, tháng 13, năm 0000, DMY, thiếu zero-padding, datetime, digit ngoài ASCII, Python date object. |
| Tiền | Chấp nhận integer 0 và 9007199254740991; từ chối âm/vượt giới hạn, bool, float (kể cả 125000.0), Decimal, NaN/Infinity, chuỗi số/nhóm nghìn/nhập nhằng; JSON cũng giữ kiểu strict. |
| Tên người bán | Unicode NFC, có chữ cái, độ dài theo code point 1–200; giữ dấu/hoa thường. Từ chối chuỗi rỗng/trắng/chỉ số, NFD, thừa khoảng trắng, tab/newline/NBSP, Unicode Cc/Cf/Cs và quá dài. |
| Currency | Chỉ `VND` canonical được nhận; USD, lowercase, alias `VNĐ`/`đồng`/`đ`/`₫`, bytes, rỗng và khoảng trắng bị từ chối. Chuyển alias là việc của service S2.2. |
| Ranh giới | Từ chối key lạ và metadata status/warnings/confidence/schema/type/confirmed; từ chối object extraction wrapper ở value. Không tạo confidence giả; metadata đó không thuộc hai model. |
| Gán lại | Gán tiền âm bị từ chối và không đổi giá trị cũ; gán mã hóa đơn chuỗi hợp lệ giữ số 0 đầu. |

Test dùng input tổng hợp, không đọc tài liệu thật hoặc ground truth để giả làm OCR.
`FinalInvoiceValues` chỉ xác nhận dữ liệu canonical hợp lệ; chưa có test xác nhận người dùng
vì ReviewDraft/ReviewedExport chưa hiện thực. Không triển khai hoặc kiểm thử chuyển đổi
DD/MM/YYYY, số tiền có dấu phân cách, alias VND, phân loại uncertain/cảnh báo/confidence,
business validation service hay API ở S2.1a. Chúng vẫn thuộc các task sau.

Endpoint `/health` và frontend không được sửa trong task này. Trạng thái chưa có
kiểm tra trực quan frontend ở S1.2 vẫn giữ nguyên.

## Normalization và business validation S2.2

Không thay đổi dependency hoặc model S2.1a. Hai service dùng Python stdlib và
Pydantic đã có. Không cần Internet, server hoặc API key để chạy test.

Lệnh đã chạy tại thư mục gốc theo README:

```powershell
.\.venv\Scripts\python.exe -m pytest -c backend/pytest.ini -q
```

Sau triển khai ban đầu: **365 passed**. Sau review ranh giới hậu tố VND và thêm
test kiểm tra marker/giá trị thiếu: **370 passed in 0.83s**, không có warning.
Gồm 207 test schema và 2 test health giữ nguyên, **161 test mới** ở
`backend/tests/test_normalization.py` và `backend/tests/test_validation.py`.
Hai module mới chặn socket connect/create_connection trong lúc test chạy.

| Nhóm | Hành vi đã được kiểm thử |
| --- | --- |
| Input canonical | Không đổi dữ liệu hợp lệ; NormalizationResult ghi version/locale; ValidationResult JSON round-trip giữ nguyên. |
| Text | NFC từ NFD, trim ngoài, gộp whitespace tên người bán, giữ số 0 đầu và ký tự O trong mã hóa đơn; không sửa nhầm thành 0. Control không hỗ trợ bị báo lỗi. |
| Ngày | ISO, DMY với vi-VN, ngày nhuận, năm 0001/9999; DMY không rõ nguồn/locale không hỗ trợ không được đoán; ngày thật được kiểm tra sau chuyển đổi. Không thêm điều kiện quá khứ/tương lai. |
| Tiền | Integer và chuỗi chữ số/nhóm nghìn chấm hợp lệ, số 0 đầu/giá trị 0, hậu tố VND; giữ chính xác biên 9007199254740991. Từ chối bool/float, âm/vượt khoảng, format sai, tiền có dấu phẩy mơ hồ; chuỗi 5000 chữ số được báo lỗi có cấu trúc. |
| Currency | Alias VND không phân biệt hoa/thường, hậu tố có ranh giới hợp lệ; không suy VND khi không có nguồn. Không che key bị thiếu hoặc ghi đè currency sai/mơ hồ/mâu thuẫn. Hậu tố rõ vẫn cho biết currency khi phần tiền sai. |
| Thiếu/sai schema | Phân biệt thiếu key, null, chuỗi trắng, input không phải object, key lạ và sai kiểu; không default giá trị. Object rỗng báo đủ năm key thiếu, input không phải object báo lỗi gốc. |
| Phân loại lỗi | Error có field/code/message; schema, normalization và business có namespace riêng. Mơ hồ/format sai không bị biến thành required trùng hoặc thành success. |
| Nhiều lỗi | Tất cả năm trường lỗi được báo cùng lần; field sai có canonical value null, field tốt giữ nguyên; lỗi gốc vẫn chặn valid dù năm field đã đủ. |
| Không sửa nguồn | Input trước/sau gọi service giống nhau; snapshot raw được deepcopy, kể cả object lồng ở key lạ. Validator không sửa candidates hoặc error list của normalization result. |
| Ranh giới kết quả | valid phải khớp completeness/errors; chưa có rule warning nên warnings rỗng. Không có confidence, extraction status hoặc confirmed flag trong kết quả. |

Giới hạn: service nhận scalar ở mỗi field, chưa chọn giữa nhiều candidate của AI,
chưa đối chiếu ảnh/OCR, chưa có business rule cho thuế hoặc chi tiết hàng hóa.
Locale phải được bên gọi cung cấp theo nguồn mẫu, không đoán từ tài liệu.
Chưa có API, UI review hoặc export; đây không phải kết quả kiểm thử luồng tài liệu đầu cuối.
Các file `/health`, hai model canonical và toàn bộ frontend được giữ nguyên.
Kiểm tra trực quan frontend vẫn chưa có thêm bằng chứng trong S2.2.

## Extraction contract và fake S3.1

Trước sửa code đã xác nhận `tuannguyen`, HEAD `50e2273`, working tree sạch,
đọc model/service/test và tài liệu. Không khác bối cảnh task. Baseline thực tế:
**370 passed in 0.85s** bằng lệnh README dưới đây. Không thêm dependency, không
chạy OCR/VLM hoặc test frontend; giữ nguyên giới hạn chưa kiểm tra trực quan S1.2.

```powershell
.\.venv\Scripts\python.exe -m pytest -c backend/pytest.ini -q
git diff --check
```

Sau S3.1: **419 passed in 0.95s**, không warning, gồm 49 test mới trong `test_pipeline.py`
và 370 test cũ giữ nguyên. Backend chưa cấu hình type checker/linter, không báo
mypy/ruff đã đạt. Pytest coi warning là lỗi theo config hiện có.

| Nhóm | Hành vi đã kiểm thử |
| --- | --- |
| Contract | Fake tuân Protocol; success dùng InvoiceValues và sales_invoice 1.0.0; JSON round-trip; từ chối schema version sai. |
| Fixture | Nhãn fake, identity/implementation/config version đầy đủ; OCR null, confidence null, evidence rỗng; output mới không chia sẻ trạng thái. |
| Canonical | Ngày/tiền được chuyển qua S2.2; thiếu một field/tất cả field giữ null; tiền mơ hồ không đoán; raw sai ngày/currency trả validation false. |
| Uncertainty | Raw vẫn giữ; uncertain dù parse được vẫn chặn canonical value và báo field; không sửa output nguồn. |
| Determinism | Bốn scenario gọi lặp cùng input/version cho JSON giống nhau; hash/run ID thay theo bytes/config; code_revision không cung cấp là null. |
| Failure | Expected error codes, TimeoutError, exception ngoài dự kiến; không lộ exception/text trong response/log; failure không mang payload thành công. |
| Boundary | Từ chối input/identity sai trước khi gọi provider; bare dict hoặc model_construct output sai key/type/metadata bị chặn; không fallback fake. |
| Metadata | Từ chối score NaN/ngoài khoảng, thiếu calibration version, ID evidence lạ/trùng, confidence trên null/uncertain, bbox đảo chiều hoặc page khác 1. Fake tự nhận OCR/evidence/score hoặc bỏ nhãn bị chặn. |

Test dùng marker bytes tổng hợp, **không phải ảnh hợp lệ**: chứng minh contract/fake,
không chứng minh giải mã ảnh hoặc chất lượng AI. Fixture test chặn socket
connect/connect_ex/create_connection và os.getenv trong lúc test chạy; đây không
phải sandbox cấm mọi truy cập mạng/môi trường lúc import. Không có score/evidence
thực nghiệm; metadata khác null chỉ xuất hiện trong stub kiểm thử cấu trúc.
Timeout fake phát lỗi tức thì, chưa kiểm tra thời gian thực hoặc cơ chế ngắt provider.
Không có kiểm thử route extraction, upload, review, export hoặc metric trong S3.1.

## OCR local S3.2 — kết quả thực tế ngày 21/10/2026

Trước sửa: `tuannguyen`, HEAD `39c6789`, working tree sạch, baseline **419 passed
in 0.95s**. Đọc handoff/Master Prompt/roadmap và code; không thay S3.1 hoặc schema.
Môi trường: Python 3.13.7, Tesseract 5.5.0.20241111 có vie/eng, thêm Pillow 13.0.0.
Model `vie` khớp hash tessdata_fast chính thức; [OCR local](ocr.md) ghi nguồn/license,
manifest, cấu hình và lỗi dấu còn lại. Không thay engine/model hoặc cài package global.

Các lệnh thực tế tại thư mục gốc:

```powershell
.\.venv\Scripts\python.exe -m pip install --no-cache-dir --disable-pip-version-check Pillow==13.0.0
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe data/ocr-smoke/generate.py --font C:/Windows/Fonts/arial.ttf
.\.venv\Scripts\python.exe -m pytest -c backend/pytest.ini -q
.\.venv\Scripts\python.exe -m pytest -c backend/pytest.ini backend/tests -q --require-real-ocr
.\.venv\Scripts\python.exe -m pytest -c backend/pytest.ini -q -m "not ocr_real"
git diff --check
git diff --cached --check
```

- Cài Pillow thành công sau khi chạy lại với quyền mạng (sandbox lần đầu chặn socket).
  `pip check`: **No broken requirements found**.
- Lệnh README mặc định: **463 passed in 2.74s**, không warning/skip.
- Lệnh bắt buộc OCR thật: **463 passed in 2.81s**, không warning/skip.
- Nhóm không cần Tesseract: **456 passed, 7 deselected in 1.12s**.
- Tổng 419 test cũ + **37 unit OCR** (`test_ocr.py`) + **7 test tích hợp/mẫu**
  (`test_ocr_real.py`). Trong nhóm sau: 5 ca chạy inference thật (PNG, JPEG, blank,
  JPEG EXIF, CLI), 1 ca từ chối ảnh hỏng và 1 ca kiểm tra manifest.

| Nhóm | Bằng chứng đã kiểm tra |
| --- | --- |
| OCR thật | Đọc được tiêu đề tiếng Việt, tên cửa hàng, số có 0 đầu, ngày và tiền từ PNG/JPEG; giữ native text/TSV và metadata. Không so toàn bộ text thành exact match. |
| Ảnh | Khớp MIME/format, decode PNG/JPEG, áp dụng EXIF, alpha nền trắng, bbox trong ảnh hiển thị; ảnh hỏng/truncated/GIF/APNG và vượt byte/pixel bị từ chối. |
| Raw/score | Không sửa input hoặc xuống dòng nguồn; native score 88.5 giữ nguyên, -1 thành null; từ chối NaN/Infinity/ngoài khoảng; dấu ngoặc kép không bị parser bỏ. |
| Output lỗi | Header/row/page/geometry sai, duplicate/missing page, text/token mâu thuẫn bị từ chối, không biến thành quan sát hợp lệ. |
| Lỗi thực thi | Thiếu executable/model, nonzero exit, timeout, không lộ stderr/text hoặc log tài liệu; file tạm được dọn cả khi lỗi. |
| Timeout thật | _invoke chạy Python child ngủ 10 giây với timeout 0.05 giây và nhận provider_timeout; riêng nhánh lỗi Tesseract được test bằng stub. Không tuyên bố đã đo SLA hoặc cố tình làm Tesseract treo. |
| Metadata/mẫu | JSON round-trip, provider/config/engine/model/Pillow/hash; manifest khớp hash/kích thước/ID, chỉ dữ liệu tổng hợp, không phân phối font/model. |

Đã chạy CLI thật qua integration test với `python -m app.ocr_cli ...` từ backend,
JSON UTF-8 hợp lệ, stderr rỗng. PNG mẫu đã được xem trực quan; chưa kiểm tra trực quan
frontend. Test Python chặn socket connect; đây không phải sandbox mạng cho tiến trình
Tesseract con. Adapter không có lệnh mạng/model download, chỉ nhận ảnh và model local.

Lần đầu gọi `--require-real-ocr` mà không chỉ rõ `backend/tests` bị pytest từ chối
option trước khi collect (conftest chưa được nạp từ thư mục con). Chạy lại đúng lệnh
ở trên đã đạt; không giảm yêu cầu hoặc bỏ qua real tests để báo thành công.
Trên máy thiếu engine/model, lệnh mặc định skip 6 ca cần môi trường; strict command
sẽ fail thay vì skip. Backend chưa cấu hình type checker/linter; không báo chúng đã chạy.
Test không chứng minh chất lượng ảnh thật/ảnh khó, không đánh giá field-level metrics,
không tích hợp extraction S3.1 với OCR, không có VLM hoặc API/UI/export trong S3.2.

## Benchmark fixture S3.3.2a

Trước sửa: branch tuannguyen, HEAD 7a28be3, hai file khảo sát đã sửa và một file
khảo sát mới chưa staged; giữ các thay đổi đó. Baseline chạy thực tế: 463 passed in 2.93s.
Không tải/chạy VLM, cài dependency mới hoặc dùng API. S3.1/S3.2/schema không đổi.

Lệnh đã chạy:

```powershell
.\.venv\Scripts\python.exe -m pytest -c backend/pytest.ini backend/tests/test_benchmark.py -q
.\.venv\Scripts\python.exe -m pytest -c backend/pytest.ini -q
git diff --check
git diff --cached --check
```

Toàn bộ **531 passed in 3.60s**, 463 test cũ và 68 test mới, không warning/skip.
Test mới bao gồm JSON/fence/schema/evidence lỗi, normalization/null/no GT/zero/typed
match, mẫu số không loại failure, determinism/version/hash, không truyền label cho
provider, không mutate source, optional fixture timing và CLI JSON. Chi tiết và giới
hạn ở [benchmark offline](benchmark-offline.md). Kết quả fixture là kiểm tra plumbing,
không phải field accuracy, confidence hoặc tốc độ của VLM.

## Xác minh cuối phiên — 22/10/2026

Chạy lại theo yêu cầu finalize, không cài dependency hoặc chạy VLM:

```powershell
.\.venv\Scripts\python.exe -m pytest -c backend/pytest.ini -q -p no:cacheprovider
git diff --check
git diff --cached --check
```

**531 passed in 4.09s**, không warning/skip. Kiểm tra whitespace đạt; các kiểm tra
staged được chạy lại trước commit. S3.1/S3.2 và canonical schema vẫn giữ nguyên.
Không chạy lại frontend vì không thay đổi frontend. S3.3.2b chỉ có tài liệu preflight,
chưa tải weights/runtime, chưa có inference hoặc benchmark VLM thật. Trạng thái commit
và push cuối phiên ghi ở [bàn giao](session-handoff.md).
