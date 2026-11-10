# Tự động trích xuất trường từ OCR

Triển khai trên branch `minhthao`. Chưa commit, push hoặc merge thay đổi này.

## Nguyên nhân và luồng hiện có

Pipeline và API đã kết nối extraction tới `Extraction.data`; frontend đã hiển thị được dữ liệu này. Các khoảng trống nằm ở rule:

1. `build_vietnamese_classifier()` chỉ đăng ký CCCD/CMND, hợp đồng, đơn xin việc và hộ khẩu. Hóa đơn/biểu mẫu chung thiếu lớp tương ứng nên có thể trả `unknown` và confidence 0 dù OCR có đủ thông tin.
2. Bộ extraction cũ tập trung vào tên/CCCD/ngày sinh/địa chỉ/điện thoại/email/MST, chưa có trường hóa đơn hoặc hồ sơ theo loại tài liệu. Một số regex dùng `\s` trong giá trị nên ăn sang trường ở dòng sau.
3. Pattern CMND 9 số có thể khớp tiền tố của CCCD 12 số, gây điểm hòa. “Kính gửi” cũng được dùng làm tín hiệu đơn xin việc dù xuất hiện trong nhiều đơn từ khác.
4. Xử lý lại bằng `/process` trước đây có thể upsert đè extraction đã được người dùng sửa.

Luồng giữ nguyên: upload → OCR → classifier → extraction → lưu JSON hiện có → detail → sửa/lưu thủ công → confirm → export/reopen. Không tạo module dịch vụ extraction song song, không thêm endpoint/schema/migration hoặc dependency, không gửi OCR/ảnh tới dịch vụ bên ngoài.

## Thay đổi

### Phân loại

Thêm `hoa_don` và `application_form` trong classifier hiện có; bổ sung nhận diện tiêu đề/số hóa đơn và các tiêu đề đơn/biểu mẫu. Bỏ dấu trên cả text lẫn pattern nhưng giữ cú pháp regex. Pattern ID có ranh giới số để phân biệt 9/12 số. Loại bỏ “Kính gửi” khỏi tín hiệu độc lập cho đơn xin việc; detector cũ tương thích với các loại mới.

Điểm classification vẫn là heuristic từ số keyword/pattern khớp, độ phủ và khoảng cách giữa hai lớp theo công thức hiện có; không phải xác suất đã hiệu chuẩn. Chỉ có từ “thanh toán”, “tổng cộng” hoặc “địa chỉ” không đủ để ép một tài liệu thành hóa đơn.

### Trích xuất theo loại

| Loại | Trường được tìm khi có nhãn/căn cứ |
| --- | --- |
| Hóa đơn | `invoice_number`, `issue_date`, `seller`, `address`, `total_amount`, `vat`, `vat_rate`, `payment_method`; giữ `tax_code`, `phone`, `email` khi có |
| CCCD/CMND | Các key tương thích `cccd`, `full_name`, `birth_date`, `gender`, `hometown`, `address`; thêm `nationality`; thông tin liên hệ có nhãn vẫn được giữ |
| Đơn/biểu mẫu | `form_name`, `full_name`, `issue_date`, `address`, `content` và thông tin liên hệ có nhãn |
| Không xác định/loại khác | Chỉ các trường chung có nhãn rõ: tên, địa chỉ, điện thoại, email, MST; không đoán số định danh hoặc loại tài liệu từ số rời rạc |

Parser hoạt động theo dòng, ưu tiên nhãn dài, hỗ trợ có/không dấu, Unicode tổ hợp và nhãn song ngữ. Giữ giá trị tiếng Việt từ nguồn; chỉ sửa O/0, I/l/1 trong ngữ cảnh số được kiểm tra chiều dài/định dạng. Ngày phải hợp lệ theo lịch. Tiền giữ dạng chuỗi, không dùng float hoặc tự tính VAT/tổng tiền.

Giá trị ở dòng kế tiếp được đọc có giới hạn; địa chỉ có thể nối tối đa hai dòng địa chỉ rõ ràng, bỏ qua tối đa một dòng trắng. Dừng tại nhãn kế tiếp, trang mới hoặc phần ký tên. Có xử lý dấu `_` phân cột do Tesseract tạo. Phân biệt phần người bán/người mua của hóa đơn để không chọn nhầm địa chỉ người mua.

Trường thiếu, placeholder, sai định dạng hoặc có nhiều giá trị mâu thuẫn bị bỏ khỏi dict; không tạo giá trị mặc định. Tài liệu PDF/TIFF cùng một chứng từ có thể gom trường qua các trang; không ghép giá trị một trường xuyên qua ngắt trang. Nếu nhiều chứng từ có số/tổng tiền khác nhau, các trường mâu thuẫn được để người dùng nhập lại.

Extraction không còn gán cố định 75–95% cho từng trường. `ExtractedField` và assessment ghi `confidence_type="not_estimated"`, kèm nhãn đã khớp và kiểm tra định dạng. Giá trị float confidence 0 được giữ để tương thích cấu trúc hiện có, không được diễn giải là ước lượng xác suất. UI chỉ hiển thị điểm classification với nhãn heuristic như trước.

Đầu vào extraction giới hạn 1.000.000 ký tự, từng dòng tối đa 2048 ký tự, số dòng nối và độ dài giá trị đều có giới hạn. Pattern cố định, không thực thi regex từ client. Raw OCR và file gốc không bị thay đổi bởi extraction.

### Rà soát và bảo vệ dữ liệu

- Machine fields ban đầu có `pending_review`. UI dùng tên trường tiếng Việt và thông báo chờ đối chiếu, không hiển thị như đã xác nhận.
- Giữ thêm/sửa/xóa và nút Lưu thay đổi hiện có. Phân biệt AI classification, loại đã được người dùng chọn và trạng thái đã lưu rà soát/chưa confirm.
- Lưu OCR không gọi extraction và không thay thế các trường đã chỉnh sửa. Manual save và Hủy OCR giữ nguyên hành vi đã sửa.
- `/process` từ chối với 409 nếu có OCR hiệu chỉnh hoặc kết quả đã được rà soát/xác nhận, kể cả sau Reopen. Repository còn chặn upsert đè dữ liệu đã duyệt. Nếu review hoàn tất trong lúc chờ AI, rollback kết quả OCR đề xuất và giữ trường/raw/trạng thái review, trả 409.
- Không tự backfill hay thay đổi tài liệu cũ. Không thêm nút trích xuất lại trong thay đổi này. Muốn thử các rule mới qua UI, upload một bản mẫu mới.

## Ví dụ dữ liệu tổng hợp

Input OCR:

```text
HÓA ĐƠN GIÁ TRỊ GIA TĂNG
Số hóa đơn: HD-2026-0142
Ngày lập: 06/11/2026
Đơn vị bán hàng: CÔNG TY MINH HỌA
Tiền thuế GTGT: 100.000 đồng
Tổng tiền thanh toán: 1.100.000 đồng
```

Các trường tương ứng:

```json
{
  "invoice_number": "HD-2026-0142",
  "issue_date": "06/11/2026",
  "seller": "CÔNG TY MINH HỌA",
  "vat": "100.000",
  "total_amount": "1.100.000"
}
```

`CĂN CƯỚC CÔNG DÂN\nHọ tên: NGUYỄN VĂN MẪU\nQuốc tịch: Việt Nam` chỉ tạo `full_name` và `nationality`; không tự điền số định danh, ngày sinh hoặc địa chỉ còn thiếu.

## File thay đổi

| Nhóm | File |
| --- | --- |
| Classification | `ai_service/classification/engine.py`, `ai_service/classification/rules.py` |
| Extraction/pipeline | `ai_service/extraction/engine.py`, `ai_service/extraction/rules.py`, `ai_service/extraction/confidence.py`, `ai_service/pipeline.py` |
| Bảo vệ dữ liệu | `backend/app/services/documents.py`, `backend/app/repositories/documents.py` |
| Giao diện | `frontend/src/pages/DocumentDetailPage.tsx`, `frontend/src/utils/extractedFields.ts` (mới) |
| Test frontend | `frontend/src/pages/DocumentDetailPage.test.tsx`, `frontend/src/utils/extractedFields.test.ts` (mới) |
| Test backend/AI | `tests/unit/test_extraction.py`, `tests/unit/test_document_fields.py` (mới), `tests/unit/test_document_repository.py`, `tests/integration/test_document_review.py` |
| Bộ mẫu và công cụ | `tests/fixtures/extraction/cases.json` (mới), `tests/fixtures/vietnamese/manifest.json`, `scripts/generate_demo_fixtures.py`, `scripts/verify_extraction.py` (mới) |
| Tài liệu | `README.md`, `docs/automatic-extraction.md` (mới) |

Giữ nguyên hai file chưa được Git theo dõi có sẵn (`ocr-review.patch` và file tên bắt đầu bằng `how 75a0feb`). Ảnh/tài liệu sinh để kiểm chứng nằm trong `storage`, không đưa vào Git.

## Kiểm thử và kết quả

| Kiểm tra | Kết quả |
| --- | --- |
| `.venv/Scripts/python.exe -m pytest -q -rs` | 295 PASS, 1 SKIP; không FAIL |
| `npm.cmd test` trong frontend | 94 PASS / 12 file; không FAIL |
| Frontend build / typecheck / lint | PASS |
| Ruff trên các module Python thay đổi và test mới | PASS |
| Docker API + Tesseract thật | 8/8 PASS |
| Edge headless tại localhost:3000 | Upload hóa đơn, CCCD, đơn/biểu mẫu và hiển thị trường: 3/3 PASS |

SKIP có sẵn: môi trường Windows không tạo được symlink cho test storage. Warning deprecation Starlette/PyMuPDF và cảnh báo fixture TIFF hỏng vẫn như trước. Docker build PASS, nhưng image frontend Node 20 hiện có cảnh báo engine với một số dependency test yêu cầu Node mới hơn; frontend tests chạy bằng Node 26 trên máy. Không nâng dependency hoặc chạy audit-fix trong tác vụ này.

Unit test bao phủ các trường đầy đủ/thiếu, không dấu/NFD/khoảng trắng, OCR lỗi nhẹ, số ID sai, ngày không tồn tại, placeholder, nhãn ở dòng kế tiếp, địa chỉ nhiều dòng, nhãn song ngữ, người mua/người bán, ký tên, số không có nhãn và mâu thuẫn/ngắt trang.

Integration test dùng pipeline/classifier/extractor thật, giả lập riêng bước nhận dạng chữ để kiểm tra chính xác dữ liệu ground truth. Test gồm PNG, PDF/TIFF hai trang, lưu tay, giữ raw OCR, bảo vệ trường bị xóa/đổi tên/ghi đè, review đến trong lúc chờ AI, confirm/reopen/export và authentication/CSRF/ownership.

Kiểm chứng Docker dùng Tesseract thật trên tám mẫu tổng hợp có bố cục: hóa đơn đầy đủ 9 trường, CCCD 7 trường, đơn 5 trường, hóa đơn PDF hai trang, hóa đơn TIFF hai trang, đơn xin việc, biểu mẫu hành chính và hóa đơn bảng có sẵn. Mỗi mẫu đi qua upload → OCR → classification/extraction → preview → review → lưu OCR → chặn process ghi đè → confirm → export → reopen → delete. Dùng SQLite và thư mục tạm riêng, không ghi vào PostgreSQL đang sử dụng.

Browser tải frontend Docker tại localhost:3000. Chỉ trong tab kiểm thử, CDP chuyển API tới FastAPI/SQLite riêng; backend đó gọi AI service Docker thật. Đã chọn file qua input, tự xử lý/chuyển detail, hiển thị trường của cả ba loại. Với hóa đơn còn kiểm tra sửa/thêm/xóa trường, manual save, lưu/Hủy OCR không làm đổi fields, 409 khi xử lý lại, confirm/reopen/export.

Artifacts cục bộ:

- `storage/extraction-verification/api-report.json`
- `storage/extraction-verification/browser-report.json`
- `storage/extraction-verification/extracted-fields.png`
- `storage/extraction-verification/fixtures/`: tài liệu mẫu có thể dùng để thử qua UI.

Chạy lại phần Docker/API bằng PowerShell ở gốc repository:

```powershell
.\.venv\Scripts\python.exe scripts/verify_extraction.py --generate
docker compose up -d --build
docker compose cp storage/extraction-verification/fixtures backend:/tmp/extraction-fixtures
Get-Content -Raw -Encoding UTF8 scripts/verify_extraction.py | docker compose exec -T backend python - --verify /tmp/extraction-fixtures --report /tmp/extraction-report.json
docker compose cp backend:/tmp/extraction-report.json storage/extraction-verification/api-report.json
```

## Kiểm tra thủ công

1. Tải lại localhost:3000, đăng nhập và upload `invoice_full.png`, `identity_full.png`, `application_full.png` trong thư mục fixtures sinh ở trên.
2. Kiểm tra loại AI nhận diện, thông báo máy trích xuất/chờ rà soát và các trường đối chiếu với ảnh gốc.
3. Chọn Chỉnh sửa dữ liệu; sửa một trường, thêm một trường, xóa một trường rồi bấm Lưu thay đổi. Reload để kiểm tra dữ liệu đã lưu.
4. Sửa OCR, chờ nhưng chưa bấm Lưu OCR: không gửi request lưu. Bấm Hủy để khôi phục; sửa lại và bấm Lưu OCR: các trường đã rà soát phải giữ nguyên.
5. Confirm, xuất JSON và kiểm tra `fields`, `ai_document_type`, `reviewed_document_type`, `ocr_text_raw` và `ocr_text`. Reopen để sửa tiếp.
6. Upload `invoice-multipage.pdf` và `invoice-multipage.tiff`, kiểm tra trường từ hai trang và preview TIFF chuyển trang. Thử tài liệu thiếu nhãn để kiểm tra hệ thống không tự điền dữ liệu không có căn cứ.

## Giới hạn

Chưa có precision/recall trên tập chứng từ thực tế đã gán nhãn; bộ kiểm chứng hiện tại là tài liệu tổng hợp, không phải số đo chất lượng trên mọi mẫu hóa đơn/CCCD. Chưa kiểm tra mọi trình duyệt hoặc tải đồng thời lớn. Bố cục nhiều cột khó, chữ viết tay, nhãn lạ, OCR sai nặng và bảng không có nhãn tổng rõ có thể bỏ sót trường. Rule ưu tiên bỏ trống khi thiếu căn cứ hoặc mâu thuẫn; người dùng cần đối chiếu trước khi xác nhận.
