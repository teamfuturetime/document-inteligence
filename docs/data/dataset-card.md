# Dataset card — synthetic-seed-1.0.0

**Purpose:** contract_fixture; EVD-01 mới scaffolded. Sáu PNG 1100×1400, một bố cục đơn đề nghị tự thiết kế, tiếng Việt đánh máy, bảy field; không là golden benchmark đại diện hoặc yêu cầu tối thiểu của giảng viên. Không chứa hồ sơ thật. [Manifest](../../data/manifests/fixtures.json) có ID/parent/template/type/paths/checksum/split/quality/provenance/version.

| Sample | Mục đích | Gold/prediction |
| --- | --- | --- |
| fixture_001 | Clear + dấu Việt | Predictions tương ứng ảnh |
| fixture_002 | Mã đầu 0 | 00123456 trong ảnh, fixture dự đoán 00123457 cố ý sai |
| fixture_003 | Nhiều dòng | Nội dung nhìn thấy, prediction null để kiểm tra missing |
| fixture_004 | Faculty trống | Gold absent; prediction Kinh tế không bằng chứng, kiểm tra extra |
| fixture_005 | Ngày sai | 31/02/2005 nhìn thấy; gold giữ chuỗi, validation INVALID_DATE |
| fixture_006 | Vùng bị che | Student ID unreadable; gold null, không lưu giá trị bí mật |

Nguồn: `scripts/generate_fixtures.py`, seed 20261005, tên/mã/nội dung hư cấu. Font Arial hệ thống chỉ dùng render, không copy/phân phối; manifest ghi filename/hash font. Khác font/Pillow/layout cần kiểm tra dấu Việt, tràn, checksum và nhãn; không bảo đảm bit-identical giữa font/runtime khác. Quyền code/data tại [licensing](../governance/licensing.md).

Gold phản ánh ảnh sau render, kể cả ngày sai nhìn thấy; không sửa để làm đẹp metric. Quy trình: render → đối chiếu từng ảnh/field → review chéo khi có người thật → giải quyết bất đồng bằng ảnh → version/manifest. Foundation có đối chiếu bởi coding agent tại báo cáo, **chưa có review chéo bởi thành viên**.

Hạn chế: một template, không OCR thật, không hóa đơn/line items/chữ viết tay/đa trang, không calibration/latency/review study. Chưa có test độc lập. BL-008 mở rộng sau scope, phân parent trước biến thể, kiểm tra chéo nhãn, chọn quality groups/template holdout nếu cần. Đổi nội dung/labels tăng dataset version, manifest checksum và rerun evaluator; report cũ giữ hashes để truy vết.
