# Vietnamese OCR regression fixtures

Các file trong thư mục này là dữ liệu tổng hợp, không chứa thông tin cá nhân thật.
`manifest.json` là nguồn ground truth được viết từ nội dung đầu vào của generator,
không được sao chép từ output OCR.

Mỗi case cần có `category`, `ground_truth`, `reading_order` và `synthetic`. Với bảng,
thêm `expected_structure`; với trường quan trọng, thêm `expected_fields` và giữ giá
trị chính xác từng ký tự.

Khi thêm dữ liệu mới:

1. Chỉ dùng dữ liệu tổng hợp hoặc dữ liệu công khai có quyền sử dụng.
2. Gõ nhãn từ tài liệu nguồn trước khi chạy OCR; hai người kiểm tra độc lập với số
   tiền, ngày, MST, số giấy tờ và tên riêng.
3. Giữ line order theo thứ tự đọc mong đợi; dùng form-feed giữa các trang.
4. Không “sửa” ground truth để giống output của engine.
5. Tách dữ liệu tuning và test trước khi điều chỉnh ngưỡng.

Tạo lại fixture:

```powershell
python scripts/generate_demo_fixtures.py
```
