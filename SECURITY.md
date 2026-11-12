# Bảo mật trong phạm vi demo local

Ứng dụng hiện không có authentication và chỉ phù hợp demo local/single-user. Cấu hình native/Compose bind loopback; không công khai demo như hệ thống nhiều người dùng. Không đưa API key vào frontend, `.env`, upload, database hoặc model weights vào commit. Không log toàn văn tài liệu mặc định. React hiển thị text qua escaping; không dùng `dangerouslySetInnerHTML` cho OCR/model output.

Chức năng thật hiện chỉ GET API và đọc fixture theo ID catalogue; đường dẫn ảnh được kiểm tra nằm trong thư mục fixture. File upload/provider thật chưa có. BL-005/003 phải bổ sung kiểm tra magic bytes + loại file PNG/JPG, giới hạn byte/pixel/page, tên hệ thống sinh, ngăn traversal, timeout có giới hạn và dọn tạm. Giá trị nền trong Settings chỉ là config thiết kế, chưa chứng minh kiểm soát upload hoạt động.

Kênh báo lỗi riêng của nhóm **TBD**, cần điều phối thiết lập trước khi dùng dữ liệu nhạy cảm hoặc dịch vụ ngoài. Với lỗi không nhạy cảm có thể dùng issue của remote repository đang tồn tại sau khi xác nhận quyền; không đăng secret hoặc thông tin cá nhân lên issue công khai. Chưa có email bảo mật hay private advisory đã cấu hình để công bố.
