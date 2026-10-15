# Bảo mật và dữ liệu cá nhân

- MIME được xác minh bằng signature, không tin extension hay header client.
- Upload giới hạn kích thước và tên lưu trữ là UUID; path traversal bị chặn.
- Đặt `API_KEY` ở production để yêu cầu header `X-API-Key` trên toàn bộ API tài liệu.
- Log chỉ chứa sự kiện kỹ thuật, không ghi nội dung OCR hay trường cá nhân.
- File và metadata hết hạn sau 41 ngày; job retention phải chạy hằng ngày.
- HTTPS, secret manager, rate limiting và phân quyền theo người dùng phải đặt ở
  gateway trước khi dùng ngoài môi trường demo nội bộ.
