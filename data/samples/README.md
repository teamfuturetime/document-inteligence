# Mẫu development synthetic v1

Hai hóa đơn tự tạo, bốn file: hóa đơn `synthetic-001` đủ năm field có PNG/JPG/PDF;
`synthetic-002-missing` chỉ PNG, cố ý thiếu tiền tệ. PDF là ảnh raster một trang
để OCR phải nhận diện thay vì lấy text embedded. Không có dữ liệu cá nhân thật.

Ground truth JSON dùng InvoiceValues v1.0.0, amount integer VND, ngày ISO.
`currency=null` trên mẫu thiếu; không tự suy ra VND. Các file variant cùng ID
có chung ground truth, không tính là các tài liệu test độc lập.
Manifest có SHA-256 cho tài liệu/truth, split dev, versions generator/schema,
Pillow/font hash và trạng thái review. Đã kiểm tra bởi tác giả; review độc lập
bởi thành viên nhóm còn pending. Đây chưa phải golden dataset Phase 6.

## Tái tạo

```bash
uv venv /tmp/ai02-sample-env --python python3
uv pip install --python /tmp/ai02-sample-env/bin/python -r data/requirements-samples.txt
# macOS: chọn font hỗ trợ đầy đủ tiếng Việt. Font không được copy vào repo.
/tmp/ai02-sample-env/bin/python data/create_samples.py --font "/System/Library/Fonts/Supplemental/Arial.ttf" --output /tmp/ai02-samples
```

Các file đã commit chạy được mà không cần generator/font. Rebuild byte-for-byte
cần cùng Pillow, font hash và JPEG encoder; font/encoder khác có thể đổi ảnh/hash.
Generator không dùng random (seed null), metadata PDF cố định, không dùng thời
gian hiện tại. Đối chiếu manifest thay vì ghi đè fixture đã review mù quáng.
Generator dùng môi trường riêng để không thay Pillow/dependency đã khóa của
backend; samples đã commit giữ nguyên hash dù decoder backend được cập nhật.

Kiểm tra PDF: Poppler `pdftoppm` hoặc PyMuPDF để render ra PNG, kiểm tra bố cục
và glyph tiếng Việt. Không dùng text extraction để chứng minh OCR đã pass.
Ground truth chưa phải output OCR/extraction; không có confidence chất lượng AI.
