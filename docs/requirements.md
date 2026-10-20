# Yêu cầu và phạm vi MVP

## Mục tiêu

Hỗ trợ luồng tài liệu mẫu → OCR → trích xuất theo schema → người dùng kiểm tra/sửa
→ backend validation → xác nhận → xuất JSON. Phát triển cá nhân theo từng task nhỏ,
chạy local, có kiểm tra và commit trên `tuannguyen`.

## Phạm vi đề xuất cho MVP

Đề xuất bắt đầu với **hóa đơn tổng hợp tiếng Việt một trang**, ảnh PNG/JPEG.
Chốt trước task S2.1; đây là đề xuất thiết kế, chưa có schema hay dữ liệu triển khai.
PDF, nhiều trang, bảng chi tiết hàng hóa, chữ viết tay và các loại đơn khác để sau
luồng ảnh một trang. Giai đoạn OCR/VLM vẫn phải có VLM thật để đáp ứng yêu cầu;
fake provider hoặc extraction theo luật chỉ hỗ trợ phát triển và baseline.

Các trường dự kiến:

| Trường | Giá trị sau chuẩn hóa dự kiến | Quy tắc cần kiểm tra |
| --- | --- | --- |
| `invoice_number` | Chuỗi | Không rỗng; giữ số 0 đầu. |
| `invoice_date` | Chuỗi `YYYY-MM-DD` | Ngày có thật; quy tắc đọc ngày nguồn phải rõ ràng. |
| `seller_name` | Chuỗi Unicode | Không rỗng; không bỏ dấu tiếng Việt trong dữ liệu xuất. |
| `total_amount` | Số nguyên VND | Không âm; không tự đoán dấu phân cách nhập nhằng. |
| `currency` | `VND` | Có chứng cứ trong tài liệu hoặc người dùng xác nhận; không tự điền ngầm. |

Ở kết quả trích xuất, trường không đọc được có thể là `null` kèm cảnh báo.
Ở dữ liệu cuối, các trường bắt buộc phải hợp lệ; không coi số 0 là thiếu giá trị.
Chưa đặt giới hạn file, độ dài chuỗi hay timeout trong code; chốt trong task tương ứng.

## Theo dõi đủ yêu cầu giảng viên

Trạng thái chỉ phản ánh nhánh `tuannguyen`. Viết tài liệu hoặc có code trên remote
không đồng nghĩa đã triển khai. Trạng thái dùng: **chưa triển khai**, **đang triển khai**,
**đã triển khai**, **đã kiểm thử**. Chỉ dùng trạng thái cuối khi có kết quả chạy kiểm tra
phù hợp, chỉ rõ phạm vi và phiên bản.

| ID | Yêu cầu | Giai đoạn / task | Bằng chứng cần để xác nhận | Trạng thái |
| --- | --- | --- | --- | --- |
| R01 | OCR nội dung tài liệu | 3 / S3.1–S3.2 | Chạy OCR thật trên ảnh mẫu; xử lý lỗi; test fake offline. | Chưa triển khai |
| R02 | Schema extraction | 2–3 / S2.1, S3.1, S3.3 | Output có schema; trích xuất từ tài liệu; test thiếu/sai trường. | Chưa triển khai |
| R03 | Confidence cấp trường khi có cơ sở | 3–4 / S3.3, S4.2 | Ghi nguồn/cách tính; test null khi không có cơ sở; UI giải thích điểm. | Chưa triển khai |
| R04 | Review UI có chỉnh sửa | 4 / S4.2 | Test hiển thị và sửa từng trường; giữ kết quả trích xuất gốc. | Chưa triển khai |
| R05 | Schema và business validation | 2, 4 / S2.1–S2.2, S4.3 | Unit test và API test; backend từ chối dữ liệu sai. | Chưa triển khai |
| R06 | Export JSON đã kiểm tra/chỉnh sửa | 4 / S4.4 | Export phản ánh sửa đổi; từ chối bản chưa hợp lệ/chưa xác nhận; test JSON. | Chưa triển khai |
| R07 | Chỉ dùng dữ liệu tổng hợp/được phép | 3, 5 / S3.2, S5.1 | Manifest có nguồn, quyền sử dụng, hash; rà soát ảnh và ground truth. | Chưa triển khai |
| R08 | Python, OCR, VLM và React/Vue | 1, 3 / S1.1–S1.2, S3.2–S3.3 | Backend Python, UI React và cả OCR/VLM thật có ví dụ chạy; fake không thay thế tích hợp thật. | Đang triển khai: Python health-check và React skeleton đã kiểm tra CLI/HTTP; còn kiểm tra trực quan frontend, OCR, VLM. |
| R09 | Golden dataset | 5 / S5.1 | Ảnh và ground truth field-level đã rà soát, manifest/version, tập đánh giá tách tập chỉnh cấu hình. | Chưa triển khai |
| R10 | Field-level metrics | 5 / S5.2 | Script chạy lại; test công thức, null và mẫu số 0; báo cáo theo trường. | Chưa triển khai |
| R11 | Error taxonomy | 5 / S5.2 | Mã lỗi và quy tắc phân loại được dùng trong báo cáo; có ví dụ đã kiểm tra. | Chưa triển khai |
| R12 | Model/config version | 3, 5 / S3.1–S3.3, S5.2 | Run metadata có model/config/schema/prompt/dataset version và commit; báo cáo so sánh tái lập. | Chưa triển khai |

## Yêu cầu chất lượng

- Business logic không import SDK OCR/VLM; fake provider chạy được offline, không API key.
- Tách OCR output, extraction gốc, validation result, bản sửa và bản đã xác nhận.
- Validation quan trọng nằm ở backend; frontend hỗ trợ người dùng sửa lỗi.
- Không bịa giá trị thiếu, không coi điểm OCR là xác suất trường đúng, không tự tin hóa điểm VLM.
- Lỗi file hỏng/sai loại/quá giới hạn, OCR/VLM thất bại, timeout, sai schema và export thất bại
  phải được biểu diễn rõ; không trả output giả như thể xử lý thật thành công.
- Không log nội dung tài liệu, trường dữ liệu hoặc secrets. Chỉ log mã lỗi, request/run ID và thời gian.
- Dữ liệu tải lên chỉ lưu tạm nếu cần, dọn sau xử lý; chưa có lưu trữ lâu dài, tài khoản hay cloud.

## Kế hoạch evaluation ban đầu

Chưa có golden dataset, script hay kết quả chất lượng. Giai đoạn 5 dự kiến tạo một bộ nhỏ
khoảng 20–30 tài liệu tổng hợp có biến thể dấu tiếng Việt, bố cục, nhiễu, trường thiếu và
giá trị nhập nhằng. Tách tập dùng chỉnh rule/prompt với tập đánh giá trước khi chạy so sánh;
không đưa ground truth của tập đánh giá vào provider.

Tính exact match sau chuẩn hóa theo trường; công bố chuẩn hóa và support.
Báo cáo riêng null/null để không che độ chính xác trường có dữ liệu. Với PRF:
TP là dự đoán khác null và đúng; giá trị sai khác null tính FP và, nếu gold có giá trị,
tính FN; bỏ sót gold tính FN; null/null không tính TP. Mẫu số 0 trả `null` kèm số đếm,
không tự quy thành 100%. Có thể tổng hợp micro/macro nhưng luôn giữ báo cáo từng trường.

Taxonomy dự kiến: `input_invalid`, `ocr_text`, `layout`, `field_missing`, `field_wrong`,
`normalization`, `schema_invalid`, `business_validation`, `provider_timeout`, `export_error`.
Lưu trường bị ảnh hưởng và bằng chứng, cho phép nhiều nhãn; không suy đoán nguyên nhân OCR
khi chưa kiểm tra OCR output. Chốt định nghĩa và ví dụ ở S5.2 trước khi công bố báo cáo.

Mỗi run cần gắn commit code, dataset version/hash, schema version, OCR engine và model/weights,
VLM model/revision, prompt/config version/hash, tham số generation và thời gian chạy.
Nếu provider bên ngoài không bảo đảm tái lập tuyệt đối, ghi rõ giới hạn và lưu output cho so sánh.
