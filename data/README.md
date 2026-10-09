# Synthetic data

Owner: OCR tạo tài liệu; Extraction tạo ground truth; người khác kiểm tra chéo.

Đã có hai hóa đơn synthetic và ground truth ở [samples/](samples/README.md),
gồm PNG/JPG/PDF và case missing. Integrity tests tại `tests/`.
Phase 6 sẽ thêm golden manifest ở `golden/`; samples hiện chỉ dành cho dev.
Chỉ dùng tên/cửa hàng/số hóa đơn giả. Không commit tài liệu cá nhân thật.
`uploads/` và `generated/` là dữ liệu runtime bị Git bỏ qua; fixture synthetic
có chủ đích được track. Chưa có golden dataset hoặc kết quả OCR/evaluation.
Xem [thiết kế dữ liệu](../docs/architecture.md).
