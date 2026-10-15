# Kịch bản demo

1. Mở trang Upload và giải thích định dạng/giới hạn 15 MB.
2. Chọn ảnh/PDF biểu mẫu không chứa PII thật, tải lên và chờ xử lý.
3. Ở trang Review, so sánh preview bên trái với trường dữ liệu bên phải.
4. Sửa một trường, chọn **Lưu sửa đổi**, sau đó **Xác nhận**.
5. Mở Lịch sử, tìm theo tên và lọc trạng thái `confirmed`.
6. Mở `/docs` để minh họa JSON contract và `/health` để kiểm tra service.

Với `OCR_ENGINE=mock`, bước 3 hiển thị cảnh báo OCR rỗng. Muốn demo nhận diện
thật phải cài PaddleOCR/model trước và thử với tài liệu mẫu đã được cho phép.

## Change request RE-044

Mọi yêu cầu mới được ghi nhận thời điểm nhận, người yêu cầu, lý do và acceptance
criteria. Trong tối đa 18 giờ, nhóm phản hồi tác động tới phạm vi, dữ liệu, API,
UI, bảo mật, effort và lịch. Thay đổi chỉ được triển khai sau khi người phụ trách
chấp thuận; prototype và quyết định được liên kết với issue/PR để truy vết.
