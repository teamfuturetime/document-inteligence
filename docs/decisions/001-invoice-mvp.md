# ADR 001 — Phạm vi hóa đơn MVP

Ngày: 2026-10-09. Trạng thái: baseline triển khai Phase 1 theo yêu cầu tiếp tục;
chưa có review nhóm/PR GitHub. Owner: Technical Lead.

## Quyết định

Giữ kiến trúc monorepo Phase 0. MVP xử lý hóa đơn bán hàng tổng hợp dạng in,
một tài liệu một trang, PNG/JPEG/PDF, tối đa 10 MiB (10 × 1024 × 1024 bytes).
PDF nhiều trang bị từ chối, không bỏ trang âm thầm. Giới hạn ảnh decode đề xuất
25 megapixel; deadline xử lý 30 giây sẽ được thực thi khi tích hợp pipeline.
Kiểm tra nội dung file thật thay vì tin extension/MIME do client gửi.

| Field | Extraction | Giá trị cuối để export |
| --- | --- | --- |
| `invoice_number` | string hoặc null | Chuỗi NFC không rỗng, tối đa 100 ký tự |
| `invoice_date` | ISO date hoặc null | `YYYY-MM-DD`, ngày tồn tại trong lịch |
| `seller_name` | string hoặc null | Chuỗi NFC không rỗng, tối đa 200 ký tự |
| `total_amount` | integer hoặc null | VND nguyên, không âm, ≤ 9007199254740991 |
| `currency` | `VND` hoặc null | `VND` |

Cả năm key luôn xuất hiện. Null nghĩa là không trích xuất được, không phải 0
hay chuỗi rỗng. Nếu nguồn có ngày/tiền không hợp lệ, extraction trả null kèm
warning và raw evidence; không ép giá trị sai vào schema normalized.
Giới hạn tiền bảo đảm integer an toàn khi trao đổi với JavaScript.
Không tự điền VND nếu tài liệu không có evidence; reviewer có thể bổ sung.

Validation request nhận raw strings để người dùng nhập ngày/tiền sai vẫn có
field errors thân thiện. Phase 4 thực hiện normalization NFC/trim, ISO date,
integer amount và VND; không suy đoán định dạng ngày quốc tế mơ hồ.
Validation response `valid=false` khi chưa đủ năm trường hợp lệ; UI chỉ export
response normalized hợp lệ của đúng bản edit hiện tại.

Tách `mode=mock|real`, các version và evidence; mock không mang tên version
OCR thật. Confidence heuristic nằm trong [0,1] hoặc null, không phải xác suất
đã hiệu chuẩn. Dữ liệu cuối không có confidence AI mới do reviewer sửa.

## Acceptance mục tiêu

- Upload → OCR → extraction → review/edit → validation → JSON cho ba định dạng.
- Input lỗi, thiếu field và timeout có thông báo/mã lỗi ổn định.
- Golden dataset Phase 6: 30 tài liệu synthetic độc lập, 18 dev/12 test;
  mẫu Phase 1 là development, không tự coi ba định dạng của cùng hóa đơn là
  ba mẫu test độc lập. Ground truth cần review bởi thành viên khác.
- Macro exact match mục tiêu ≥ 0.85 trước review, không phải số đã đo;
  báo cáo support/null policy và từng field kể cả khi không đạt ngưỡng.
- Không database, đăng nhập, cloud, handwritten, multi-page hoặc line items.

## Hệ quả và bước tiếp theo

Frontend/Backend/Extraction làm từ schema và fixture chung. Pydantic là nguồn
JSON Schema; frontend sẽ generate TypeScript từ schema ở Phase 2, không sửa
type sinh ra bằng tay. OCR có contract riêng không phụ thuộc HTTP framework.
Thay đổi phạm vi sau ADR này cần ADR/issue và PR riêng.

P1-01 hoàn thành local: có quyết định baseline; chưa thay thế review nhóm.
P1-02 thêm contract/tests, P1-03 thêm mẫu synthetic. Chưa có app/API/OCR chạy.
