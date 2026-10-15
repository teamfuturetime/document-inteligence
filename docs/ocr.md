# OCR tiếng Việt — P3-02

`document_pipeline.ocr` dùng Tesseract 5 thực để đọc tài liệu đã preprocessing.
Kết quả là `OCRResult` v1.0.0 với `mode=real`, `language=vie+eng`, token Unicode,
bounding box pixel và confidence. P4-01 đã có [extraction CLI riêng](extraction.md)
nhận OCRResult. API đã tích hợp real mặc định ở P4-03; xem [real pipeline](real-pipeline.md).

## Cài và chạy local

Từ repository root trên `personal/canhtung-main`:

```bash
uv sync --locked
tesseract --version
.venv/bin/python -m document_pipeline.ocr_models --directory data/models/tessdata
.venv/bin/python -m document_pipeline.ocr_models --directory data/models/tessdata --check
.venv/bin/python -m document_pipeline.ocr data/samples/synthetic-001.png --tessdata-dir data/models/tessdata --output data/generated/ocr/invoice.json
```

Máy hiện tại đã có Tesseract 5.5.2 và model đã được cài vào thư mục dự án.
Máy khác cần Tesseract 5 trên PATH; ví dụ macOS dùng `brew install tesseract`,
Ubuntu 24.04 dùng `sudo apt-get install tesseract-ocr=5.3.4-1build5`.
Adapter kiểm tra major version 5 và ghi version thực tế; không tự cài engine.
Chạy lệnh installer cần mạng; `--check` chỉ kiểm tra file local.

CLI tự preprocessing PNG/JPEG/PDF một trang, rồi chạy OCR. Output gồm JSON
contract và `.metadata.json` bên cạnh. Có thể thay input bằng sample JPG/PDF
hoặc `synthetic-002-missing.png`. Output có sẵn sẽ được ghi đè; CLI từ chối
đường dẫn output/metadata trùng nhau hoặc trùng input.

Python callers dùng `recognize(prepared_page, tessdata_dir, config=None)`, nhận
`OCRRun.result` và `.metadata`. `PreparedPage` đến từ
[preprocessing](preprocessing.md), không phải ảnh thô chưa có transform.

## Model và config

Chọn `tessdata_fast` làm baseline nhỏ/gọn, chưa benchmark so với `tessdata_best`.
Lock nằm trong package tại `pipeline/src/document_pipeline/tessdata-lock.json`:

- Repository chính thức: `tesseract-ocr/tessdata_fast`.
- Commit: `87416418657359cb625c412a48b6e1d6d41c29bd`.
- `vie`: SHA-256 `79df64caf7bcfb2a27df5042ecb6121e196eada34da774956995747636d5bfa1`.
- `eng`: SHA-256 `7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2`.
- Model upstream có giấy phép Apache-2.0; xem [license tại commit đã pin](https://github.com/tesseract-ocr/tessdata_fast/blob/87416418657359cb625c412a48b6e1d6d41c29bd/LICENSE).

Installer chỉ tải hai model ở commit đã khóa, xác minh hash trước khi thay file
bằng rename nguyên tử. Download lỗi/hash sai dọn file tạm, không thay file cũ.
Model hợp lệ được dùng lại. Binary nằm trong `data/models/` đã ignore, không
commit vào Git. Mỗi lần OCR đều kiểm tra lại cả hai model; không dùng model
hệ thống thay thế và không tự download khi nhận diện.

Config baseline: `vie+eng`, LSTM `--oem 1`, layout tự động `--psm 3`,
`OMP_THREAD_LIMIT=1`. `OCRConfig` cho đổi PSM nhận diện không cần OSD, DPI ảnh
72–300 và timeout. PDF dùng DPI đã rasterize; ảnh mặc định gợi ý 150 DPI cho
engine, không resize pixel. Đây là config khởi đầu, chưa tối ưu trên golden set.

Metadata ghi engine version, commit/hash của từng model, config + SHA-256,
adapter version và toàn bộ metadata preprocessing. `ocr_version` trong
contract có engine/modelset/adapter identifiers; không thay shape schema.
Kết quả tái lập được kiểm tra trong cùng môi trường engine/model/config;
không cam kết byte-identical giữa Tesseract 5.3.4 và 5.5.2 hoặc các OS/CPU.

## TSV, tọa độ và lỗi

Adapter gửi PNG qua stdin và lấy TSV qua stdout, không cần file ảnh tạm.
Chỉ lấy word rows `level=5` có text; giữ thứ tự đọc engine và dấu tiếng Việt,
trim khoảng trắng hai đầu. Box dùng cạnh phải/dưới exclusive trên ảnh processed;
`to_original` được chuyển nguyên từ preprocessing. Confidence 0–100 chia 100;
sentinel `-1` thành null. Đây không phải xác suất đã hiệu chuẩn.

TSV lỗi, confidence NaN/ngoài miền, box không hợp lệ hoặc vượt trang bị từ chối
toàn bộ, không trả phần kết quả đã parse. Trang trắng trả `tokens=[]` và
warning `no_text_detected` trong sidecar. Không tự thêm token hoặc nội dung mẫu.

Thiếu engine, sai major version, thiếu/sai hash model hoặc engine exit lỗi:
`ocr_unavailable`. Quá deadline: `processing_timeout`; subprocess được dừng và
thu hồi. TSV lỗi: `internal_error`. Ảnh/metadata đầu vào không hợp lệ:
`invalid_document`. Không trả stderr engine trong lỗi và không fallback mock.
Preprocessing và OCR có hai deadline riêng mặc định 30 giây mỗi bước; chưa
có deadline chung cho HTTP vì chưa tích hợp API.

## Kiểm thử

```bash
# Unit/adapter tests không cần engine/model; real integration được skip rõ:
.venv/bin/python -m pytest -q
# Bắt buộc chạy engine thật; thiếu model/engine sẽ FAIL, không skip:
.venv/bin/python -m pytest pipeline/tests/test_ocr_integration.py --run-ocr --tessdata-dir data/models/tessdata -q
```

Fake engine chỉ kiểm tra parser/config/error handling. Real engine tests đọc
bốn sample variants, kiểm tra Unicode/contract/boxes, trang trắng và hai lần
chạy giống nhau. Đây là smoke coverage trên hai hóa đơn development, chưa phải
OCR accuracy benchmark, field extraction hoặc golden evaluation.

Verification local ngày 2026-10-15, macOS ARM64/Python 3.13.14/Tesseract 5.5.2:
toàn bộ workspace chạy với `--run-ocr` đạt 158 tests; trong đó 6 integration
tests dùng engine thật. 9 schema không drift. CLI PNG và PDF đều trả 53 token
trên `synthetic-001`, gồm dấu tiếng Việt và giá trị từ ảnh. Build wheel/sdist
của package pipeline thành công. Các kết quả này chưa phải evidence GitHub CI.

Tham khảo [TSV và language order](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html),
[model repositories](https://tesseract-ocr.github.io/tessdoc/Data-Files.html)
và [gói engine Ubuntu 24.04](https://packages.ubuntu.com/noble/arm64/tesseract-ocr).
