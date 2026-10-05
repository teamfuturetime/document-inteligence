# Split và leakage

Seed có `purpose=contract_fixture`, cả 6 samples split contract_fixture, chưa development/validation/test và chưa benchmark. Không gọi metrics seed là test độc lập.

BL-008: development viết rules/prompt/debug; validation chọn config/ngưỡng; test chỉ chạy config đã chốt. Chia **parent documents trước biến thể**; mọi clear/blur/rotate/crop cùng parent ở một split. Nếu đo layout mới, thêm template holdout/protocol riêng. Tỷ lệ/số mẫu TBD theo nguồn lực/phép đo, không đặt tùy tiện.

Validator hiện kiểm tra IDs, paths trong repo, checksum/duplicate image hash, dataset version, gold IDs/field keys, parent overlap; canonical gold content trùng giữa splits fail để review leakage. Đây không bảo đảm hết near duplicates/template leakage; BL-008 bổ sung audit ảnh/nội dung và quyền test.

Inference không đọc gold. Nếu tune theo test, ghi contamination và có test độc lập mới. Production validation (required/date/quan hệ) khác validation split (chọn config); không lấy gold để sửa runtime prediction.
