# Contract v1.0.0

Baseline: [ADR 001](decisions/001-invoice-mvp.md). Models nguồn tại
`backend/app/models/contracts.py`; JSON Schema export tại `schemas/v1/`.
Không có endpoint/server thực thi trong Phase 1.

## API

| Endpoint | Input | Success | Failure |
| --- | --- | --- | --- |
| `GET /health` | Không | 200 `health-response` | 500 `api-error` |
| `POST /api/v1/extract` | multipart/form-data, một part `file` | 200 `extraction-response` | 413, 415, 422, 503, 504, 500 |
| `POST /api/v1/validate` | application/json `validation-request` | 200 `validation-response` kể cả field invalid | 422 malformed request/schema version sai; 500 |

`GET /health` chứng minh server hoạt động, không chứng minh OCR sẵn sàng;
`ocr_ready` báo riêng. Extract synchronous; không polling hoặc database.
`document_id` là ID tương quan request, không phải URL tải tài liệu đã lưu.
Giới hạn: 10 MiB file, 25 megapixel decode, một trang, deadline 30 giây.
Backend phải áp dụng cả streaming size limit và giới hạn decode khi triển khai;
không chỉ kiểm tra Content-Length. UI có thể preview file local.

| HTTP status | `error.code` |
| --- | --- |
| 413 | `file_too_large` |
| 415 | `unsupported_media_type` |
| 422 | `invalid_document`, `multiple_pages`, `image_too_large`, `invalid_request` |
| 503 | `ocr_unavailable` |
| 504 | `processing_timeout` |
| 500 | `internal_error` |

Error envelope luôn `{ "error": { "code", "message", "field" } }`.
`field` null cho lỗi request/file; không lộ exception/stack/đường dẫn.
Phase 2 phải chuyển cả RequestValidationError mặc định của FastAPI vào envelope
này, không trả lẫn hai format. Invalid review values trả 200 `valid=false`;
JSON sai kiểu/key/version là 422 `invalid_request`.

## Schema và validation

- Tất cả keys được khai báo là required; `additionalProperties=false`.
- Không ép kiểu string thành number hoặc bool thành integer. Raw input review
  là string/null; amount input `"125000"` được service normalize ở Phase 4.
- InvoiceValues cho extraction/ground truth có null; FinalInvoiceValues không
  có null. Missing luôn null, không empty string/0. Amount 0 vẫn hợp lệ.
- ISO date phải khớp `YYYY-MM-DD` và tồn tại; schema dùng `format=date`.
  Consumer JSON Schema phải bật format checking. Validator Pydantic cũng kiểm
  tra ngày thực. Final normalization NFC/trim là trách nhiệm service Phase 4.
- `valid=true`: đủ năm giá trị non-null, errors rỗng. `valid=false`: mỗi field
  invalid có value null và một hoặc nhiều FieldError, không lỗi cho value hợp lệ.
- ReviewedExport giữ `original_extraction`, `values` hợp lệ và `edited_fields`
  đúng tập field có normalized value khác AI. Confidence chỉ nằm trong bản AI.
  Không có endpoint export; browser tạo/download JSON sau validation thành công.
- Schema chỉ bảo đảm cấu trúc/constraints cục bộ. Pydantic model validators
  kiểm tra quan hệ giữa các field: null/confidence, bounding box, validation
  consistency, edited_fields. JSON Schema riêng không thay thế kiểm tra ngữ nghĩa.

## OCR và extraction

OCRResult: mode, engine/model version, `language=vie+eng`, một OCRPage chứa
width/height, tokens, transform `to_original`. Box pixel integer trên ảnh
processed, gốc trên trái, `(x0,y0)` inclusive, `(x1,y1)` exclusive; positive area
và không vượt page. `to_original` là ma trận 3×3 row-major áp dụng tọa độ đồng
nhất từ processed sang original; không đổi ảnh thì identity.

Field evidence có text raw, page=1 và box; confidence [0,1]/null. Value null
buộc confidence null; có thể giữ evidence về ứng viên bị loại để debug.
Warnings dùng code ổn định đề xuất `missing_field`, `ambiguous_field`,
`invalid_source_value`; nội dung OCR vẫn nằm evidence, không nhúng vào warning.
Mock fixtures dùng `ocr_version=mock-not-run`, không phải output OCR thật.
Extractor nhận OCRResult + rules/config; không import FastAPI. OCR contract
hiện được định nghĩa cùng file nguồn models để schema nhất quán. Phase 2 tách
kiểu dùng chung thành package độc lập trước khi pipeline import, giữ wire shape.

## Fixtures và chiến lược frontend

`schemas/fixtures/manifest.json` liệt kê schema và expectation của từng file:
success, missing, raw/invalid review, errors, OCR mock và reviewed export.
Fixture là contract data tự tạo, không phải output model hay chất lượng đã đo.

Phase 2 sẽ thêm công cụ generate TS từ `schemas/v1/*.schema.json`, khóa version
công cụ bằng npm lockfile. Type sinh ra nằm thư mục riêng, không chỉnh bằng tay;
CI regenerate và fail nếu diff. Runtime vẫn dùng backend validation; TypeScript
type không tự validate JSON từ mạng. Chưa tạo frontend package ở Phase 1.

## Versioning và kiểm tra

SemVer schema: phá shape/kiểu/required/null policy tăng major; additive thay đổi
phải kiểm tra consumer strict trước khi gọi compatible; docs-only tăng patch.
API major theo `/api/v1`; fixture, schema và source đổi cùng PR. Rules/config,
OCR model và pipeline có version độc lập, không giả vờ schema version là model.

```bash
uv venv .venv --python python3
uv pip install --python .venv/bin/python -r backend/requirements-contracts.txt
uv pip install --python .venv/bin/python -r backend/requirements-contract-tests.txt
.venv/bin/python -m backend.export_schemas --check
.venv/bin/python -m pytest backend/tests -q
```

Chạy từ root, Python ≥ 3.11; không sửa sys.path. Khi đổi model, chạy
`python -m backend.export_schemas`, review schema diff rồi chạy --check/tests.
Schema là generated artifact cần commit vì là interface được version; khác
với output runtime/reports không cần track.

Tham khảo cơ chế export và strict validation từ [Pydantic JSON Schema](https://github.com/pydantic/pydantic/blob/main/docs/concepts/json_schema.md)
và [Pydantic strict mode](https://github.com/pydantic/pydantic/blob/main/docs/concepts/strict_mode.md).
