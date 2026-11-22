# PDF synthetic cho kiểm thử

- `hoa_don_007.pdf` là ảnh synthetic `data/product/images/hoa_don_007.png` đóng gói bằng Pillow ở 200 DPI thành một trang 432 × 558 pt. Không thuộc tập benchmark và không thay gold. SHA256 `36639ed1d790f7b0af76ab846c147289912b60498ef2a1e7e09a89c3abddf43a`.
- `encrypted.pdf` và `empty-password.pdf` là các trang trống 72 × 72 pt, tạo với pypdf 6.21.4 và RC4-128 để kiểm từ chối PDF mã hóa. Fixture thứ nhất dùng mật khẩu synthetic `synthetic-password`, fixture thứ hai dùng mật khẩu mở rỗng. Cả hai có mật khẩu chủ synthetic và không chứa dữ liệu thật. MD5/RC4 chỉ xuất hiện trong fixture định dạng cũ, không dùng để bảo vệ dữ liệu ứng dụng.
- Browser E2E và native workflow đọc mẫu hóa đơn này độc lập với evaluator. Script nhận dạng không đọc annotation.
