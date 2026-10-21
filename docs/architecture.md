# Kiến trúc dự kiến

## Quyết định trong Giai đoạn 0

Đề xuất modular monolith với một backend **Python/FastAPI**, một frontend
**React/TypeScript/Vite**, schema/validation **Pydantic** ở backend.
S1.1 đã triển khai backend FastAPI tối thiểu; S1.2 đã tạo frontend React/TypeScript/Vite.
S3.1 đã có pipeline nội bộ với fake; luồng tài liệu đầu cuối còn là định hướng.
Giữ backend đơn giản, frontend dự kiến gọi HTTP API; chưa cần database, queue, microservice
hoặc cloud. Chỉ bổ sung lưu trữ khi có nhu cầu khôi phục/lịch sử được xác định rõ.

Backend dùng `.venv` với `requirements.txt` pin runtime và `requirements-dev.txt`
pin test; đã kiểm tra trên Windows / Python 3.13.7. Runtime chỉ khai báo trực tiếp
FastAPI, Uvicorn và (từ S3.2) Pillow; test dùng pytest và HTTPX2 cho TestClient.
Chưa thêm extras `standard`, SDK AI hoặc database; fake có config version nội bộ.
Frontend có `package-lock.json`; chỉ dùng React/ReactDOM và các công cụ TypeScript,
Vite, React plugin, type definitions. Không thêm UI library, router hay state manager.
`uv` không phải điều kiện bắt buộc.

## Quyết định dữ liệu S2.1

Chốt một loại biểu mẫu: **hóa đơn bán hàng tiếng Việt một trang, tổng hợp**, mã
`sales_invoice`, đặc tả `schema_version = "1.0.0"`. Chỉ năm trường
`invoice_number`, `invoice_date`, `seller_name`, `total_amount`, `currency`.
[Requirements](requirements.md) định nghĩa kiểu, giới hạn và quy tắc chuẩn hóa.
S2.1a đã hiện thực hai model canonical bằng Pydantic ở `backend/app/schemas/invoice.py`;
S2.2 đã thêm normalization/business validation và model kết quả validation local;
chưa có API hoặc file JSON Schema xuất riêng. Pydantic là nguồn contract
thực thi cho các model này, không duy trì hai bộ validation Python/TypeScript khác nhau.

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
`.npmrc` đặt cache trong repo. S2.1a thêm `backend/app/schemas/{__init__,invoice}.py`
và `backend/tests/test_schemas.py`. S2.2 thêm `schemas/validation.py`,
`services/{__init__,normalization,validation}.py` và hai module test service.
S3.1 thêm `schemas/extraction.py`, `providers/{__init__,contracts,fake}.py`,
`services/pipeline.py` và `tests/test_pipeline.py`.
Các thư mục api và evaluation trong sơ đồ vẫn là kế hoạch.
S3.2 đã tạo `data/ocr-smoke/` (generator, ba ảnh tổng hợp, manifest),
`schemas/ocr.py`, `providers/{ocr,tesseract}.py`, `app/ocr_cli.py`,
`tests/{conftest,test_ocr,test_ocr_real}.py`. Thư mục api/evaluation vẫn chưa có.
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

Hai model giá trị và `FieldIssue`/`ValidationResult` đã hiện thực; NormalizationResult
là dataclass nội bộ của service. S3.1 có provider contract và pipeline outcome nhỏ;
S3.2 đã hiện thực `OCRResult` và OCR adapter/CLI riêng, chưa có HTTP endpoint.
`ExtractionResult.fields`, review/export dưới đây vẫn là **đặc tả**.
Dữ liệu đầu vào
của provider, draft thô, giá trị canonical và bản đã xác nhận có trách nhiệm khác nhau:

| Artifact | Nội dung / kiểu chính | Ai tạo và được phép thay đổi |
| --- | --- | --- |
| `OCRResult` | `document_id: string`, raw text, token/span text, trang 1, vị trí nếu có, native score/thang đo, phiên bản engine/model/config. Chưa phải năm trường hóa đơn. | OCR adapter tạo; giữ nguyên raw text/score, không sửa đè khi normalize hoặc review. |
| `ExtractionResult` | Envelope có `document_id`, `document_type: "sales_invoice"`, `schema_version: "1.0.0"`, `normalization_version`, `run_metadata`, `fields`: đủ năm `ExtractedField<T>` theo requirements. | Extraction adapter và service chuẩn hóa tạo dự đoán có evidence; không sửa bản gốc khi review. |
| `NormalizationResult` | Bản sao sâu `raw_values`, năm `candidates` trung gian, `errors: FieldIssue[]`, source locale và normalization version. Chưa phải canonical values hoặc ExtractionResult. | Service chuẩn hóa tạo, không sửa input. Candidates vẫn có thể chứa ngày không tồn tại hoặc số tiền ngoài khoảng, cần validation tiếp. |
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
giá trị đang hoạt động từ S2.2 là `invoice-normalization-1`.
Đổi ý nghĩa trường/kiểu/required phải tăng schema version; đổi rule/prompt/config phải
ghi version/hash mới để so sánh evaluation. Không dùng thời gian chạy thay cho model version.

Field confidence là object có score, nguồn, method/calibration version và evidence IDs
theo requirements; confidence null khi chưa có cơ sở. Candidate không có evidence
phải chuyển sang `uncertain`, không tự tin hóa điểm VLM. Chưa có chính sách đã đánh giá,
ngưỡng review hay số đo thực nghiệm; S2.1 không thiết lập một công thức điểm mới.

### Model canonical S2.1a

`backend/app/schemas/invoice.py` dùng các kiểu `Annotated` chung cho cả hai model,
`ConfigDict(strict=True, extra="forbid", validate_assignment=True)` và các validator
kiểm tra ngày lịch/tên người bán. Các validator chỉ trả lại giá trị không đổi hoặc
báo lỗi: `date.fromisoformat` chạy sau pattern ISO; tên phải đã ở NFC, đúng khoảng
trắng, không có category Cc/Cf/Cs và có chữ cái. Kiểm tra khi gán lại thuộc tính cũng
giữ các ràng buộc đó. Không thêm dependency hoặc trường metadata vào model giá trị.

Test offline trong `backend/tests/test_schemas.py` đã kiểm tra canonical input:
key bắt buộc/null, kiểu strict, giới hạn, key lạ, Unicode, ngày có thật và số 0 đầu.
Kết quả chi tiết ở [testing.md](testing.md). Hai service S2.2 bên dưới dùng lại các
model này. S3.1 thêm boundary provider bên dưới; S3.2 có OCRResult riêng.
Các API, ExtractionResult đầy đủ và review/UI vẫn chưa triển khai.

### Service S2.2

Luồng nội bộ hiện có: raw object → `normalize_invoice` → `NormalizationResult`
→ `validate_invoice` → `ValidationResult`. Chưa có HTTP route gọi service,
frontend hoặc AI provider. Các model canonical S2.1a không bị sửa.

- `services/normalization.py` chỉ chuyển các format nguồn đã định nghĩa, NFC/trim,
  khoảng trắng tên người bán, DMY có locale rõ ràng, tiền nguyên và alias/hậu tố VND.
  Giữ snapshot input riêng và version `invoice-normalization-1`; không gắn điểm confidence.
- `services/validation.py` dùng `FinalInvoiceValues` để gom lỗi cho tất cả trường;
  giữ lỗi normalization/schema, rồi tạo `InvoiceValues` với field lỗi là null.
  Lỗi có namespace `schema.`, `normalization.`, `business.` trong thuộc tính code,
  không đổi cấu trúc `FieldIssue` ba key. Không dùng thành công normalization làm valid.
- `schemas/validation.py` biểu diễn đúng bốn thuộc tính của ValidationResult và
  kiểm tra valid khớp tính đầy đủ/lỗi khi tạo kết quả. Warnings chưa có rule nên để rỗng.
  Kết quả không phải xác nhận người dùng hoặc chứng nhận khớp nội dung ảnh.

Lỗi gốc/key lạ có field null; lỗi một trong năm key có field tương ứng. Message lỗi
không chứa text nguồn và service không log tài liệu. Nguồn text vẫn có thể xem trong
NormalizationResult khi bên gọi cần review, không lưu file/database trong S2.2.
Danh mục lỗi, yêu cầu locale và giới hạn còn mở ở [requirements](requirements.md).

Business logic nhận interface nhỏ (ví dụ Python `Protocol`) được định nghĩa từ ca sử dụng thực tế.
OCR adapter chịu trách nhiệm SDK/CLI; extraction adapter chịu trách nhiệm SDK VLM, prompt và parse.
Service chỉ điều phối, không phụ thuộc trực tiếp SDK. Fake adapter trả output cố định có nhãn
`fake`, version và confidence null, dùng cho test/UI; không đọc ground truth để giả thành inference.
Thay provider bằng cấu hình đơn giản; chưa cần plugin registry hay dependency-injection framework.

### Contract và fake S3.1 đang hoạt động

`ExtractionProvider` là Protocol đồng bộ có `identity: ProviderIdentity` và
`extract(DocumentInput) -> ProviderOutput`. Không có base implementation, registry,
SDK hoặc framework DI. `DocumentInput` chứa `document_id`, MIME PNG/JPEG và bytes
không rỗng, không nhận đường dẫn file. Đây là container, chưa giải mã ảnh, đọc EXIF
hoặc áp dụng giới hạn byte/pixel. Adapter thật sẽ chịu trách nhiệm kiểm tra ảnh.

`ProviderOutput` là boundary **trước normalization**, không phải `ExtractionResult`
đầy đủ trong bảng thiết kế. Nó có đủ năm key ở `raw_values` và `field_metadata`:
raw là string/null, riêng total_amount được phép integer; không default trường thiếu.
`source_locale` là vi-VN hoặc null, do provider xác định từ nguồn/cấu hình, không đoán
từ ngôn ngữ. `uncertain_fields` liệt kê field chưa chọn chắc chắn; `ocr_text` nullable
giữ riêng văn bản trung gian, `warnings` là mã cảnh báo provider.

Mỗi `FieldMetadata` bắt buộc có `confidence` nullable và `evidence` (có thể rỗng).
Kiểu confidence/evidence dùng đúng cấu trúc đã đặc tả: score hữu hạn [0,1], source,
method/calibration version, ID evidence cùng field, ID không trùng, trang 1 và bbox
pixel có diện tích dương. Chưa có kích thước ảnh nên chưa kiểm tra cận width/height;
adapter thật phải bổ sung kiểm tra với ảnh nguồn. Kiểm tra cấu trúc không chứng minh
evidence hoặc phương pháp confidence là có thật. Native OCR score chưa có chỗ trong
contract này và không được chuyển ngầm sang score cấp trường.

`run_pipeline` kiểm tra lại input, identity và output bằng Pydantic, kể cả object
đã được tạo bằng model_construct hoặc sửa sau khi tạo. Sai contract trả failure;
raw string hợp kiểu nhưng ngày/tiền/currency sai vẫn đi qua S2.2 và trả lỗi dữ liệu.
Pipeline giữ nguyên raw output, gọi normalization và validation không sửa các service.
Field được provider đánh dấu uncertain bị chặn về canonical null; thêm lỗi
`extraction.uncertain_field` nếu field chưa có lỗi normalization, không nhân đôi lỗi.
Đây là mã của pipeline, không thay các namespace/hành vi S2.2.

`PipelineSuccess` có `status="succeeded"`, schema/type cố định sales_invoice 1.0.0,
`provider_output`, `run_metadata`, `validation: ValidationResult`. Canonical values
chỉ ở `validation.normalized_values: InvoiceValues`. `validation.valid` có thể false;
true chỉ chứng minh dữ liệu hợp lệ theo rule, không chứng minh đối chiếu ảnh/người dùng
duyệt. Boundary này chưa tạo trạng thái `candidate` có evidence của ExtractedField;
không nâng dữ liệu fixture thành dự đoán có chứng cứ.

`ProviderError` biểu diễn lỗi có chủ đích: `provider_unavailable`, `provider_timeout`,
`provider_failed`, `invalid_document`. Pipeline đổi TimeoutError thành provider_timeout,
exception ngoài dự kiến thành provider_failed, output sai thành invalid_provider_output,
input sai thành invalid_input. `PipelineFailure` chỉ có schema/type/document ID,
metadata khi đã biết và error code/message cố định; không có payload thành công,
không trả nội dung exception hoặc log text tài liệu. Không tự fallback sang fake.
Timeout hiện chỉ được truyền/giả lập; chưa có deadline cưỡng chế cho hàm đồng bộ.

Run metadata ghi provider name/implementation_version/config_version/mode,
pipeline_version `extraction-pipeline-1`, normalization_version và SHA-256 nội dung.
`run_id` là hash ổn định của ID/MIME/hash nội dung/các version/code_revision, không
phải ID lần gọi duy nhất. Bên gọi truyền code_revision; bỏ qua thì null, không đọc
Git, thời gian, biến môi trường hoặc bịa revision. Chưa chạy OCR/VLM nên không tạo
model/prompt version; metadata đánh giá đầy đủ vẫn thuộc S3.2/S3.3/S5.2.

Fake có tên `fake-invoice-fixture`, implementation `1.0.0`, config
`synthetic-{scenario}-1`, mode fake. Bốn scenario: complete (đủ format vi-VN),
partial (seller null, tiền `125,000` mơ hồ), failure và timeout (lỗi tức thì).
Fixture nhỏ, hoàn toàn tổng hợp, độc lập nội dung bytes; mỗi lần tạo object mới.
Luôn gắn `fake_data`, `not_derived_from_document`, OCR text null, confidence null,
evidence rỗng. Pipeline từ chối fake tự gắn OCR/evidence/score hoặc bỏ nhãn này.
Không nhận dạng ảnh, gọi mạng, đọc secret, tải model hay dùng ground truth.

Pydantic được chọn làm nguồn schema thực thi. Khi API và frontend bắt đầu trao đổi dữ liệu, xuất OpenAPI/JSON
Schema để kiểm tra đồng bộ TypeScript; chỉ thêm công cụ generate type nếu task đó cần.
Đầu ra VLM là dữ liệu không tin cậy: parse, kiểm tra kiểu/trường và validation trước khi dùng.
Text trong tài liệu là dữ liệu, không được thực thi như lệnh hoặc dùng để thay đổi chỉ dẫn pipeline.

## OCR, VLM và confidence

S3.2 chọn Tesseract local + `vie` sau smoke test trên mẫu tổng hợp; cấu hình,
hash model, license và lỗi dấu còn lại ở [OCR local](ocr.md), quyết định ở
[ADR 0001](adr/0001-local-tesseract-ocr.md). Chưa chọn VLM hoặc so sánh nhiều OCR engine.

`OCRProvider.recognize(DocumentInput) -> OCRResult` là Protocol riêng, dùng lại
DocumentInput/ProviderIdentity/BoundingBox và ProviderError của S3.1 nhưng không sửa
chúng. Không ép OCR-only adapter trả năm field của ExtractionProvider. Luồng local
hiện tại: PNG/JPEG bytes → Pillow decode/EXIF/RGB nền trắng → Tesseract txt+tsv →
OCRResult; S3.1 extraction pipeline/fake vẫn chạy độc lập. Kết nối với extraction thật
chỉ thực hiện ở S3.3, không thêm rule extraction để giả lập VLM.

OCRResult giữ ID/hash nguồn, hash ảnh đã xử lý, width/height/hệ toạ độ, raw text/TSV,
word text/page/bbox/native_confidence, metadata engine/model/config/Pillow và warnings.
Giữ nguyên text/xuống dòng, native score 0–100 (unavailable -1 thành null), không
normalize dữ liệu hóa đơn hoặc gắn field confidence. Bbox được kiểm tra cận ảnh đã
áp dụng EXIF; native TSV được giữ nguyên riêng để truy vết, không sửa S3.1 Evidence.

Pillow thêm vào runtime pins để decode PNG/JPEG thực và áp dụng EXIF. Adapter từ chối
format không khớp MIME, ảnh hỏng/multiple frame và vượt guard 10 MiB/20 triệu pixel.
Các guard này chưa phải chính sách HTTP upload. Mỗi subprocess có timeout 30 giây
mặc định (cấu hình được), hết hạn giết/chờ child; decode/hash không nằm trong deadline.
File output tạm được dọn bằng context manager, không log text/stderr engine. Ảnh trống
trả thành công với warning no_text, không tạo candidate/default hóa đơn.

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
