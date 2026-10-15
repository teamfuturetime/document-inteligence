# Golden synthetic baseline 1.0.0

30 hóa đơn độc lập, 18 dev (`001`–`018`), 12 test (`019`–`030`). Mỗi ID chỉ có
một file; không đếm ba định dạng của cùng hóa đơn thành ba tài liệu độc lập.
Ba layout nhãn/thứ tự/spacing, PNG/JPG/PDF, năm điều kiện: clean, compression,
blur, rotation 1.1°, missing currency. Dữ liệu và tên cửa hàng đều tự tạo.

Manifest pin seed 20261015, generator/schema/Pillow/font version và SHA-256
cho từng document/ground truth. Dataset đã đóng băng trước lần chạy evaluation
đầu; không đổi rules/data theo holdout test. Ground truth do tác giả kiểm tra;
review độc lập bởi thành viên khác còn pending, không coi automated tests là review.

Generator từ root workspace (Pillow 12.3.0 theo lockfile):

```bash
.venv/bin/python data/create_golden.py --font '/System/Library/Fonts/Supplemental/Arial.ttf' --output /tmp/ai02-golden-rebuild
```

Font không bundled; hash sai hoặc output không rỗng đều bị từ chối. Rebuild
byte-identical cần cùng font/Pillow/encoder. Evaluation dùng files đã commit,
không cần font/generator. PDF raster không có text layer; đã render kiểm tra
glyph tiếng Việt và không cắt dòng.

Giới hạn: dataset nhỏ, chỉ ba template đơn giản, layout và format có tương quan.
Không đại diện hóa đơn thật/chữ viết tay/bảng/multi-page hoặc khả năng tổng quát.
