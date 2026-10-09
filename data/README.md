# Synthetic data

Owner: OCR tạo tài liệu; Extraction tạo ground truth; người khác kiểm tra chéo.

Phase 1 thêm mẫu nhỏ ở `samples/`; Phase 6 thêm golden manifest ở `golden/`.
Chỉ dùng tên/cửa hàng/số hóa đơn giả. Không commit tài liệu cá nhân thật.
`uploads/` và `generated/` là dữ liệu runtime bị Git bỏ qua; fixture synthetic
có chủ đích được track. Chưa có dataset. Xem [thiết kế dữ liệu](../docs/architecture.md).
