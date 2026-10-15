# Synthetic data

Hai hóa đơn mẫu development ở [samples](samples/README.md); bộ 30 hóa đơn độc lập
và split 18 dev/12 test ở [golden](golden/README.md). Tất cả dữ liệu tự tạo,
không có tài liệu/cửa hàng/người thật. Manifest hash tài liệu/truth và pin
versions/seed/font. Review ground truth độc lập còn pending.

Integrity tests ở tests/. uploads/, generated/, models/ là runtime/ignored;
chỉ fixture synthetic có chủ đích được track. Xem [evaluation](../docs/evaluation.md)
để chạy cùng pipeline thật với API và đọc giới hạn đo chất lượng.
