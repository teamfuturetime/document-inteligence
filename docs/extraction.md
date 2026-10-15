# Trích xuất hóa đơn theo nhãn — P4-01

`document_pipeline.extraction` nhận `OCRResult` v1.0.0 và trả
`ExtractionResponse` cùng schema hiện có. Module độc lập FastAPI/Tesseract;
không đọc ảnh hoặc tự gọi OCR. P4-02/03 đã bổ sung validation và [API thật](real-pipeline.md);
Phase 5 đã có [review/export](review-export.md).

## Chạy thử

Từ repository root, sau [cài model OCR](ocr.md):

```bash
uv sync --locked
.venv/bin/python -m document_pipeline.ocr data/samples/synthetic-001.png --tessdata-dir data/models/tessdata --output data/generated/ocr/invoice.json
.venv/bin/python -m document_pipeline.extraction data/generated/ocr/invoice.json --output data/generated/extraction/invoice.json
```

CLI extraction tạo JSON response và `.metadata.json` bên cạnh; không thay
input, ghi đè output đã có. Input tối đa 10 MiB, phải đúng OCRResult contract.
`--document-id ID` tùy chọn; mặc định ID lấy từ SHA-256 bytes OCR input.
Sai input/đường dẫn trùng trả exit code 1. Output runtime trong `data/generated/`
đã ignore. API Python: `extract_invoice(ocr_result, document_id)`.

Đổi file nguồn sang JPG/PDF hoặc `synthetic-002-missing.png` để thử luồng khác.
Mẫu thiếu tiền tệ trả `currency=null`; không tự điền VND.

## Rules baseline

`invoice-rules.json` trong package ghi alias nhãn, tham số nhóm dòng và version.
`config_version` gồm rules version + prefix hash; sidecar giữ full rules/hash
và hash OCR input. `pipeline_version=invoice-extraction-1.0.0` mô tả extractor
CLI; `ocr_version` và `mode` được giữ từ input. Mock OCR luôn cho output mock
kèm `mock_data`; không biến fixture thành kết quả OCR thật.

Nhóm token bằng độ chồng dọc và khoảng cách tâm, rồi sắp trái → phải. Chỉ nhận
nhãn ở đầu dòng, có dấu `:` và giá trị cùng dòng. So khớp nhãn không phân biệt
hoa/thường/dấu tiếng Việt; không sửa lỗi OCR trong giá trị. Ví dụ:

| Field | Nhãn |
| --- | --- |
| `invoice_number` | Số hóa đơn, Mã hóa đơn |
| `invoice_date` | Ngày, Ngày lập, Ngày hóa đơn |
| `seller_name` | Bên bán, Tên bên bán, Người bán |
| `total_amount` | Tổng tiền, Tổng cộng, Tổng thanh toán, Tổng tiền thanh toán |
| `currency` | Tiền tệ, Đơn vị tiền tệ |

Không chọn số từ dòng không nhãn, ghi chú, tên người mua hoặc đơn giá/thành
tiền từng sản phẩm. Nhiều nhãn trên cùng dòng được đánh dấu mơ hồ; chưa hỗ
trợ layout nhiều cột, label/value khác dòng, tên bên bán xuống dòng hoặc bảng.
Ngưỡng geometry hiện là baseline; chưa có benchmark trên ảnh nghiêng/layout khó.

## Chuẩn hóa và chọn ứng viên

- Chuỗi: NFC, trim/collapse whitespace; giữ nguyên dấu/chữ hoa của giá trị.
  Mã hóa đơn chỉ nhận ASCII chữ/số và `._/-`, tối đa 100 ký tự. Tên bên bán
  tối đa 200 ký tự, có chữ cái, không ký tự điều khiển.
- Ngày: ISO `YYYY-MM-DD`; hoặc ngày/tháng/năm với `/`, `-`, `.` khi xác định
  được thứ tự. `15/10/2026` → `2026-10-15`; `03/04/2026` → null/mơ hồ;
  `10/10/2026` hợp lệ vì hai cách đọc trùng nhau. Không đổi MM/DD thành DD/MM,
  sửa ngày sai lịch hoặc đoán năm hai chữ số.
- Tiền: integer ASCII không âm, hoặc nhóm nghìn đúng ba chữ số và cùng dấu
  `.`, `,`, khoảng trắng. `125.000` → 125000, `1,234,567` → 1234567.
  `125,50`, dấu nhóm hỗn hợp, số âm/khoa học/ngoài safe integer bị từ chối.
  0 là giá trị hợp lệ; không thay null bằng 0.
- Tiền tệ: `VND`, `VNĐ`, `đồng`, `đ`, `₫` → VND. Chấp nhận nhãn riêng hoặc
  suffix trên tổng tiền có nhãn. Không nhận chuỗi VND nằm trong từ khác,
  suy từ ngôn ngữ hóa đơn, mặc định hoặc tự quy đổi ngoại tệ.

Thiếu nhãn/giá trị: null + `missing_field`. Nguồn sai: null +
`invalid_source_value`. Nhiều ứng viên khác nhau hoặc ngày mơ hồ: null +
`ambiguous_field`. Ứng viên hợp lệ không che ứng viên lỗi/missing ở nhãn lặp.
Ứng viên lặp cùng giá trị chuẩn hóa được chấp nhận và giữ tất cả evidence.

## Evidence và confidence

Evidence giữ text raw và box của từng token trên dòng ứng viên, gồm nhãn và
giá trị, trong hệ tọa độ processed của OCR. Null do invalid/ambiguity vẫn giữ
evidence; không tìm thấy nhãn thì evidence rỗng. Không vẽ box mới từ text
chuẩn hóa hoặc ánh xạ sang preview ở bước này.

Confidence heuristic lấy minimum của tất cả token evidence dùng cho ứng viên
được chọn. Một token không có score → confidence null; score 0 được giữ.
Giá trị null luôn có confidence null. Đây là điểm OCR bảo thủ theo evidence,
không phải xác suất field đúng đã hiệu chuẩn.

## Kiểm thử và giới hạn kết quả

```bash
.venv/bin/python -m pytest pipeline/tests/test_extraction.py -q
.venv/bin/python -m pytest pipeline/tests/test_extraction_integration.py --run-ocr --tessdata-dir=data/models/tessdata -q
```

Ngày 2026-10-15, macOS ARM64/Python 3.13.14/Tesseract 5.5.2:

- 63 extraction unit/CLI tests pass: alias/Unicode, geometry, missing/invalid/
  ambiguity, ngày/tiền biên, evidence, confidence và tính lặp lại.
- 4 real-engine extraction smoke tests khớp ground truth: PNG/JPG/PDF của
  synthetic-001 và PNG thiếu currency của synthetic-002.
- Toàn bộ Python workspace với `--run-ocr`: 225 tests pass; 9 schema không drift.
- CLI OCR → extraction chạy thật trên PNG, trả đúng năm giá trị của sample.

Ba định dạng synthetic-001 vẫn chỉ là một hóa đơn; tổng cộng hai mẫu dev,
không phải golden test set hoặc số đo accuracy. Chưa chạy GitHub CI cho thay
đổi này. Job `OCR integration` được cập nhật để thu thập cả OCR và extraction
tests có marker `ocr_integration`; thiếu engine/model khi opt in sẽ fail.

Khi thay logic matching/normalization/geometry/confidence, bump version phù
hợp và chạy regression. Không tuning trên golden test set khi Phase 6 triển khai.
