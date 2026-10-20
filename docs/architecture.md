# Kiến trúc dự kiến

## Quyết định trong Giai đoạn 0

Đề xuất modular monolith với một backend **Python/FastAPI**, một frontend
**React/TypeScript/Vite**, schema/validation **Pydantic** ở backend.
S1.1 đã triển khai backend FastAPI tối thiểu; S1.2 đã tạo frontend React/TypeScript/Vite.
Pipeline tài liệu còn là định hướng.
Giữ backend đơn giản, frontend dự kiến gọi HTTP API; chưa cần database, queue, microservice
hoặc cloud. Chỉ bổ sung lưu trữ khi có nhu cầu khôi phục/lịch sử được xác định rõ.

Backend dùng `.venv` với `requirements.txt` pin runtime và `requirements-dev.txt`
pin test; đã kiểm tra trên Windows / Python 3.13.7. Runtime chỉ khai báo trực tiếp
FastAPI và Uvicorn, test dùng pytest và HTTPX2 cho TestClient của Starlette hiện tại.
Chưa thêm extras `standard`, SDK AI, cấu hình provider hay database.
Frontend có `package-lock.json`; chỉ dùng React/ReactDOM và các công cụ TypeScript,
Vite, React plugin, type definitions. Không thêm UI library, router hay state manager.
`uv` không phải điều kiện bắt buộc.

## Quyết định dữ liệu S2.1

Chốt một loại biểu mẫu: **hóa đơn bán hàng tiếng Việt một trang, tổng hợp**, mã
`sales_invoice`, đặc tả `schema_version = "1.0.0"`. Chỉ năm trường
`invoice_number`, `invoice_date`, `seller_name`, `total_amount`, `currency`.
[Requirements](requirements.md) là nơi định nghĩa kiểu, giới hạn và quy tắc chuẩn hóa;
chưa có model Pydantic hoặc schema JSON thực thi. Sau này Pydantic là nguồn contract
thực thi, không duy trì hai bộ validation Python/TypeScript riêng với quy tắc khác nhau.

S1.2 vẫn **chưa kiểm tra trực quan**; các kết quả CLI/HTTP/render trong Node được giữ
đúng phạm vi ở [testing.md](testing.md). Việc chốt thiết kế S2.1 không xác nhận toàn bộ
Giai đoạn 1 đã hoàn thành kiểm tra giao diện.

## Cấu trúc sẽ tạo dần

```text
README.md
docs/                    # Yêu cầu, khảo sát, kiến trúc và roadmap hiện có
backend/                 # S1.1: FastAPI app, health route và tests
  app/
    main.py
    api/                 # HTTP routes; không chứa logic AI
    schemas/             # S2: schema và validation
    services/            # S3–4: điều phối pipeline và review/export
    providers/           # S3: OCR/VLM adapter và fake provider
  tests/
frontend/                # S1.2: React; S4: upload/review/export
data/                    # S3/5: mẫu tổng hợp, manifest, ground truth
evaluation/              # S5: metrics, taxonomy và báo cáo phiên bản
```

Hiện có `backend/app/__init__.py`, `backend/app/main.py`, `backend/tests/test_health.py`,
`backend/pytest.ini` và hai file requirements. Frontend có `index.html`, `src/main.tsx`,
`src/App.tsx`, `src/styles.css`, `vite.config.ts`, `tsconfig.json`, package/lockfile và
`.npmrc` đặt cache trong repo. Các thư mục api/schemas/services/providers, data và
evaluation trong sơ đồ còn là kế hoạch, chưa được tạo.
Không dựng package workspace hoặc registry nhiều provider trước khi cần.

## Luồng dữ liệu dự kiến

```text
React: chọn ảnh mẫu
  → Backend: kiểm tra file, kích thước và khả năng giải mã
  → OCR adapter: nhận dạng text, vị trí và score nếu engine cung cấp
  → OCRResult (giữ thông tin nguồn)
  → Extraction adapter: ảnh + OCR + schema → candidate fields
  → Backend: parse schema, validation, gắn cảnh báo và run metadata
  → React: hiển thị extraction gốc, cho sửa bản nháp
  → Backend: chuẩn hóa và validation lại bản nháp
  → Người dùng xác nhận bản hợp lệ
  → Backend: validation lại và tạo JSON của bản xác nhận
  → React: tải JSON
```

Luồng tài liệu này là thiết kế. S1.1 chỉ có luồng HTTP client → Uvicorn →
FastAPI `GET /health` → `200 {"status":"ok"}`, không gọi frontend hoặc AI.
S1.2 có luồng Vite → trình duyệt → React root → trang giới thiệu tĩnh.
Frontend chưa gọi backend nên chưa cần dev proxy hay thay đổi CORS.
Contract upload/extract, validate và export chỉ chốt khi task tương ứng bắt đầu.
Xử lý đồng bộ cho một tài liệu trong MVP, có timeout rõ ràng ở tầng provider;
nếu đo được thời gian xử lý không phù hợp mới xem xét job bất đồng bộ.

## Ranh giới dữ liệu và AI

Các kiểu bên dưới là **đặc tả**, chưa tạo class/endpoint tương ứng. Dữ liệu đầu vào
của provider, draft thô, giá trị canonical và bản đã xác nhận có trách nhiệm khác nhau:

| Artifact | Nội dung / kiểu chính | Ai tạo và được phép thay đổi |
| --- | --- | --- |
| `OCRResult` | `document_id: string`, raw text, token/span text, trang 1, vị trí nếu có, native score/thang đo, phiên bản engine/model/config. Chưa phải năm trường hóa đơn. | OCR adapter tạo; giữ nguyên raw text/score, không sửa đè khi normalize hoặc review. |
| `ExtractionResult` | Envelope có `document_id`, `document_type: "sales_invoice"`, `schema_version: "1.0.0"`, `normalization_version`, `run_metadata`, `fields`: đủ năm `ExtractedField<T>` theo requirements. | Extraction adapter và service chuẩn hóa tạo dự đoán có evidence; không sửa bản gốc khi review. |
| `ValidationResult` | `valid: boolean`, `normalized_values: InvoiceValues`, `errors: FieldIssue[]`, `warnings: FieldIssue[]`. | Backend tạo từ đúng bản input đang kiểm tra; có thể tạo kết quả mới, không biến lỗi thành thành công. |
| `ReviewDraft` | `document_id`, `extraction_run_id`, `draft_revision: integer >= 1`, `values`: đủ năm key với `string` hoặc `null` cho input của trình duyệt. Không mang confidence mới. | Người dùng sửa bản sao; có thể chưa hợp lệ, mỗi lần sửa tăng revision và bỏ xác nhận/kết quả validation cũ. |
| `ReviewedExport` | Envelope có schema/type/document/run ID, `original_extraction`, `values: FinalInvoiceValues`, `edited_fields: FieldName[]`, `review_revision: integer >= 1`, `confirmed: true`. | Backend tạo sau khi validate lại và người dùng xác nhận đúng revision. Đây mới là dữ liệu đã duyệt; không tính lại confidence thành 1.0. |

`FieldName` chỉ là một trong năm key nghiệp vụ. `FieldIssue` gồm `field: FieldName`
hoặc null cho lỗi toàn bản ghi, `code: string` không rỗng và `message: string` cho UI.
`valid = true` chỉ khi đủ năm giá trị canonical khác null, không có error; warning
có thể còn và phải được hiển thị. `valid = false` có ít nhất một error, trường thiếu/sai
trong `normalized_values` là null. Validation không đồng nghĩa người dùng đã xác nhận
hoặc đối chiếu được dữ liệu với ảnh.

`InvoiceValues` và `FinalInvoiceValues` có cùng năm key, từ chối key lạ, kiểm tra kiểu
strict và không default. Khác nhau ở quyền có null: kết quả chưa hoàn chỉnh cho phép
null, bản cuối không cho phép. Số tiền canonical là integer; draft vẫn giữ chuỗi
`"125.000"` cho bước normalize, không để frontend tự chuyển float hoặc đoán định dạng.
Không parse số hóa đơn thành số. Người dùng có thể điền dữ liệu máy bỏ sót, nhưng
phải qua cùng validation với mọi thay đổi khác.

`edited_fields` không trùng và chính xác là những field có giá trị canonical cuối
khác `original_extraction.fields[field].value`, kể cả khi giá trị gốc null. Giữ
nguyên extraction gốc cùng confidence/evidence; không gắn confidence của giá trị máy
sang giá trị người dùng sửa. Thay đổi draft sau xác nhận bắt buộc validate/xác nhận lại;
không xuất kết quả validation thuộc revision trước.

### Evidence, phiên bản và confidence

Evidence có ID không rỗng, duy nhất trong từng trường; `page` chỉ là 1.
`bbox` null khi không có tọa độ, hoặc object số nguyên pixel `{x0, y0, x1, y1}`,
với `0 <= x0 < x1 <= width`, `0 <= y0 < y1 <= height`. Gốc tọa độ ở góc trên trái
ảnh nguồn đã áp dụng chiều hiển thị EXIF như ảnh review; width/height và quy ước
ảnh nguồn phải được giữ ở metadata tài liệu. Nếu OCR xử lý ảnh đã resize/rotate,
adapter phải ánh xạ tọa độ về cùng ảnh review; không chế bbox để lấp null.
Native OCR output và thông tin biến đổi vẫn được giữ riêng để truy vết.

`run_metadata` cần `run_id`, `mode` (`fake` hoặc `real`), code revision,
OCR/VLM provider/model/revision, prompt version/hash, normalization/config version/hash.
Thành phần chưa chạy để version null và trạng thái chưa chạy; fake phải mang tên/version
fake rõ ràng. Chuỗi `normalization_version` định danh bộ quy tắc ở requirements;
giá trị khởi đầu dự kiến `invoice-normalization-1`, chưa phải code đang hoạt động.
Đổi ý nghĩa trường/kiểu/required phải tăng schema version; đổi rule/prompt/config phải
ghi version/hash mới để so sánh evaluation. Không dùng thời gian chạy thay cho model version.

Field confidence là object có score, nguồn, method/calibration version và evidence IDs
theo requirements; confidence null khi chưa có cơ sở. Candidate không có evidence
phải chuyển sang `uncertain`, không tự tin hóa điểm VLM. Chưa có chính sách đã đánh giá,
ngưỡng review hay số đo thực nghiệm; S2.1 không thiết lập một công thức điểm mới.

### Phạm vi code tiếp theo

Task riêng **S2.1a** chỉ hiện thực `InvoiceValues` và `FinalInvoiceValues` cùng unit test
offline cho canonical input: key bắt buộc/null, kiểu strict, giới hạn, key lạ,
ngày có thật và giữ số 0 đầu. Chưa tạo normalization service, API, pipeline/envelope
OCR/extraction/confidence hoặc UI. Các envelope trên sẽ hiện thực ở S3.1/S4 khi cần.
Service chuyển chuỗi tiền/ngày/currency thô và business validation vẫn là S2.2.

Business logic nhận interface nhỏ (ví dụ Python `Protocol`) được định nghĩa từ ca sử dụng thực tế.
OCR adapter chịu trách nhiệm SDK/CLI; extraction adapter chịu trách nhiệm SDK VLM, prompt và parse.
Service chỉ điều phối, không phụ thuộc trực tiếp SDK. Fake adapter trả output cố định có nhãn
`fake`, version và confidence null, dùng cho test/UI; không đọc ground truth để giả thành inference.
Thay provider bằng cấu hình đơn giản; chưa cần plugin registry hay dependency-injection framework.

Pydantic được chọn làm nguồn schema thực thi. Khi API và frontend bắt đầu trao đổi dữ liệu, xuất OpenAPI/JSON
Schema để kiểm tra đồng bộ TypeScript; chỉ thêm công cụ generate type nếu task đó cần.
Đầu ra VLM là dữ liệu không tin cậy: parse, kiểm tra kiểu/trường và validation trước khi dùng.
Text trong tài liệu là dữ liệu, không được thực thi như lệnh hoặc dùng để thay đổi chỉ dẫn pipeline.

## OCR, VLM và confidence

Tesseract đã có `vie`/`eng` trên máy, nên là ứng viên cần đo trên mẫu, chưa được chọn làm provider
chính. Chọn OCR/VLM sau khi kiểm tra chất lượng tiếng Việt, tài nguyên CPU/GPU, giấy phép,
khả năng chạy Python local, chi phí và API key. Việc chọn model chưa chặn skeleton.

VLM thật vẫn nằm trong S3.3; OCR cộng rule không đáp ứng riêng yêu cầu VLM.
Trước khi dùng API có phí hoặc gửi tài liệu ra ngoài phải xác định provider, giá, dữ liệu gửi
và được người dùng đồng ý theo phạm vi đó. Fake provider cho phép hoàn thành các test offline.

Confidence OCR phản ánh nhận dạng token, không mặc nhiên là độ đúng trường extraction.
Chỉ gán confidence cấp trường khi có chính sách và evidence rõ; lưu nguồn, cách tính và giới hạn.
Giữ null nếu thiếu cơ sở; điểm mô hình tự báo chưa được hiệu chuẩn không xem như xác suất.
Chọn ngưỡng review sau evaluation, không tự điền một ngưỡng được cho là chính xác.

## Validation, lỗi và export

Backend kiểm tra ngày, số tiền, trường bắt buộc và currency cho cả validate lẫn export.
Frontend hiển thị lỗi cạnh trường và giữ input để sửa. Export kiểm tra chính payload cuối cùng
và yêu cầu xác nhận; nếu người dùng sửa tiếp thì phải validate/xác nhận lại, tránh xuất bản cũ.

Ở task upload, chốt giới hạn byte/pixel, kiểm tra nội dung file thay vì chỉ extension/MIME,
không dùng tên file người dùng làm đường dẫn lưu. File tạm được dọn kể cả khi lỗi/timeout.
Phân biệt file không hợp lệ, OCR/VLM unavailable, timeout, output sai schema và export lỗi
bằng mã lỗi ổn định; không trả nội dung exception chứa tài liệu/API key ra UI.

Health-check chỉ xác nhận backend sống, không tuyên bố OCR/VLM sẵn sàng nếu chưa kiểm tra.
Không thêm database chỉ để giữ trạng thái review: MVP có thể gửi extraction gốc và bản sửa
trong request export; đây là công cụ local, chưa cung cấp bằng chứng chống sửa metadata.
Nếu cần audit đáng tin cậy hoặc nhiều người dùng, phải thiết kế lưu trạng thái phía server sau.

## Khi nào ghi ADR

Ghi ADR khi chốt OCR/VLM provider, thay đổi nguồn schema hoặc bổ sung persistence/async
vì các quyết định đó có chi phí chuyển đổi. Hiện tại tài liệu này đủ cho kiến trúc đề xuất;
quyết định schema MVP S2.1 được ghi ở đây và requirements. Chưa đổi nguồn schema,
chưa tạo thư mục ADR trống hoặc ghi quyết định provider khi chưa thử nghiệm.
