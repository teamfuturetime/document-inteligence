# MVP và kiến trúc đề xuất

Trạng thái: đề xuất ban đầu, chưa phải contract đã được triển khai. Chốt bằng
issue P1-01 trước khi viết skeleton. Thay đổi phạm vi sau đó cần issue/PR riêng.

## Phạm vi và tiêu chí thành công

Một hóa đơn bán hàng tổng hợp dạng in rõ, PNG/JPG/PDF một trang, tối đa 10 MiB.
PDF nhiều trang bị từ chối với lỗi rõ ràng; không âm thầm bỏ trang.
Năm trường: `invoice_number`, `invoice_date`, `seller_name`, `total_amount`,
`currency`. Chưa xử lý dòng sản phẩm, thông tin cá nhân hoặc chữ viết tay.

Luồng hoàn chỉnh: upload → preprocessing → OCR → extraction → validation
→ review/sửa → validation lần cuối → tải JSON. Tài liệu không có trường cần
trích xuất vẫn phải hiển thị lỗi/missing; không tự bịa giá trị.
Chỉ export khi các trường bắt buộc hợp lệ sau review.

Mục tiêu đánh giá ban đầu: macro exact match trên năm trường ≥ 0.85 trên tập
test synthetic cố định; đây là mục tiêu, chưa phải kết quả đo. Báo cáo riêng từng
trường, trường thiếu, tập dễ/khó và số lượng mẫu. Dataset nhỏ không chứng minh
khả năng xử lý hóa đơn thực tế; không điều chỉnh test để đạt ngưỡng.

## Công nghệ và lựa chọn

- React + TypeScript + Vite theo yêu cầu, frontend chỉ biết HTTP/JSON contract.
- FastAPI + Pydantic cho API, kiểu dữ liệu và validation.
- Python cho pipeline và evaluation để dùng lại extraction thực tế.
- OCR baseline đề xuất: Tesseract với `vie+eng`, adapter trả token/bounding box.
  [Tesseract có model vie](https://tesseract-ocr.github.io/tessdoc/Data-Files.html).
  Chọn bộ traineddata và ghi hash/version sau benchmark Phase 3; chưa cài OCR.
- Extraction baseline dùng rule theo nhãn và định dạng; version rules/config.
  Adapter vision-language model chỉ là khả năng mở rộng, chưa triển khai.
- Pytest, Vitest và GitHub Actions sẽ được thêm khi có module chạy được.

Chạy local với hai process frontend/backend, không cần database. Mỗi request
xử lý đồng bộ trong MVP; phải giới hạn thời gian/kích thước trước khi tích hợp.
Kết quả giữ ở trình duyệt, backend không lưu lịch sử. File tạm được cleanup cả
khi thành công/lỗi. Không dùng tên file upload làm đường dẫn trực tiếp.

## Ranh giới module

```text
Browser (frontend) → HTTP → backend → pipeline
                                ↑         ↑
                         schemas/   evaluation CLI
                                         ↑
                              data/ + ground truth
```

Frontend không import Python và không tự chạy AI. Backend gọi pipeline qua
interface Python; pipeline không import FastAPI hoặc frontend. Evaluation gọi
cùng pipeline/config với API, không viết bản extraction riêng.
`schemas/` chứa JSON Schema/fixtures chung; Pydantic phía backend là nguồn để
xuất schema. Phase 1 định nghĩa cách kiểm tra schema export và type TS không
bị lệch; không duy trì ba bản schema độc lập bằng tay.

| Module | Interface dự kiến | Người sở hữu |
| --- | --- | --- |
| Preprocessing | bytes + media type → page image + transform metadata | OCR |
| OCR adapter | page image → tokens(text, box, confidence), page dimensions | OCR |
| Extraction adapter | OCR result + config → fields + evidence + versions | Extraction |
| Validation | reviewed values → normalized values + field errors | Backend |
| HTTP API | multipart file → extraction JSON; reviewed JSON → validation | Backend |
| Review | extraction JSON → editable values → validated export | Frontend |
| Evaluation | dataset manifest + config → metrics + error records | Extraction |

Bounding boxes đề xuất dùng pixel với gốc trên trái trên ảnh đã preprocessing;
metadata transform cần đủ để vẽ trên preview gốc. Nếu chưa làm highlight,
vẫn giữ evidence để debug. OCR confidence được chuẩn hóa về [0,1], giá trị
không xác định là null; confidence extraction là heuristic, không phải xác
suất đã hiệu chuẩn. Giá trị do người dùng sửa không được mang confidence AI
như thể AI đã trích xuất đúng.

## Contract dự kiến cho Phase 1

- `GET /health`: trạng thái service; không giả định OCR đã sẵn sàng.
- `POST /api/v1/extract`: multipart `file`; trả `document_id`, `schema_version`,
  `pipeline_version`, `ocr_version`, `config_version`, `fields`, `warnings`.
- `POST /api/v1/validate`: reviewed values + schema version; trả `valid`,
  `normalized_values`, `errors` theo tên trường. Không cần lưu document_id.
- Export JSON tại frontend sau validation; gồm giá trị cuối, giá trị AI gốc,
  trường đã sửa và provenance/version để phân biệt AI và người review.
- Mã lỗi dự kiến: 413 vượt dung lượng; 415 loại file không hỗ trợ; 422 tài liệu
  lỗi/PDF nhiều trang hoặc dữ liệu request không hợp lệ; 503 OCR chưa sẵn sàng.
  Lỗi xử lý trả mã ổn định, không lộ stack trace hoặc đường dẫn máy chủ.

Field envelope: `value`, `confidence`, `evidence` (text, page, box), `warnings`.
Các value có thể null khi extraction không tìm thấy. Ngày chuẩn hóa ISO
`YYYY-MM-DD`; tiền VND là số nguyên không âm; ngày sai lịch bị validation từ
chối. `currency` chỉ nhận VND trong MVP, thiếu evidence không tự coi là đúng.
Phase 1 sẽ chốt trường bắt buộc, schema version `1.0.0`, fixture JSON và
request/response lỗi trước khi frontend/backend làm song song.

## Cấu trúc triển khai tiếp theo

```text
frontend/src/{api,components,features}/  # tests cạnh component
backend/app/{api,models,services}/
backend/tests/
pipeline/src/document_pipeline/{preprocessing,ocr,extraction}/
pipeline/tests/
evaluation/src/document_evaluation/
evaluation/tests/
schemas/                               # JSON Schema + contract fixtures
data/{samples,golden}/                  # synthetic + ground truth + manifest
docs/
.github/{ISSUE_TEMPLATE,workflows}/
```

Hiện chỉ tạo README nêu ownership trong từng thư mục. Backend, pipeline và
evaluation sẽ là các package Python nhỏ dùng dependency local, cài editable
khi phát triển; không chỉnh `sys.path` bằng tay. Chốt layout đóng gói ở Phase 2.
Frontend có lockfile riêng; dependency Python và công cụ OCR phải được pin
khi triển khai để CI và evaluation dùng cùng cấu hình.

## Dữ liệu và evaluation

Đề xuất 30 hóa đơn synthetic: 18 development, 12 test cố định; nhiều layout,
dấu tiếng Việt, biến thể nhãn, missing fields, ảnh nghiêng/mờ và định dạng tiền.
Ground truth do người khác người tạo mẫu kiểm tra. Manifest ghi ID, đường dẫn,
hash tài liệu, split, layout, điều kiện ảnh và schema version. Ground truth
không chứa output model; không tuning trên test. Seed generator phải cố định.

Exact match từng trường sau normalization đã version: trim/Unicode NFC cho
chuỗi (không bỏ dấu), ISO cho ngày, integer cho tiền. Báo cáo TP/FP/FN:
đúng giá trị non-null = TP, sai giá trị non-null = FP và FN, dự đoán thừa = FP,
bỏ sót = FN. Cặp null-null tính exact match nhưng không là TP; báo cáo riêng
để tránh tỷ lệ cao giả tạo. Precision/recall/F1 có denominator 0 phải hiển thị
N/A; ghi support và macro/micro rõ ràng.

Taxonomy: `input_quality`, `preprocessing`, `ocr_text`, `field_mapping`,
`normalization`, `validation`, `unsupported_layout`. Ghi lỗi quan sát và nguyên
nhân được xác minh riêng; không suy đoán mọi sai lệch là lỗi OCR.
Report phải có Git SHA, dependency/engine versions, hash model và dataset,
schema/config version, seed, lệnh chạy. Đo kết quả trước review để không dùng
chỉnh sửa thủ công làm tăng chất lượng AI. Phase 6 cung cấp CLI tái lập thực tế.
