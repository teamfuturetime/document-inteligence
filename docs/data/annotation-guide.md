# Hướng dẫn nhãn

Nguồn chuẩn giá trị là **ảnh sau render**. Kiểm tra dấu Việt, số 0 đầu, crop/mask và tràn; không dùng dữ liệu generator để suy giá trị không còn nhìn thấy. Field definitions provisional tại [SRS](../requirements/srs.md), cần BL-001 chốt.

`present`: đọc được giá trị, lưu string theo normalization policy. `absent`: không có/thực sự để trống, null. `unreadable`: có vùng thông tin nhưng không đủ đọc, null; không lưu bí mật từ seed. GoldAnnotation dùng sample_id và fields; cả bảy field trong seed luôn có status rõ.

Giữ mã dạng chuỗi và dấu Việt, không fuzzy nhãn chính. Ngày sai nhưng nhìn rõ giữ chuỗi sai: accuracy có thể đúng trong khi validation sai nghiệp vụ. Gộp whitespace request_content nhiều dòng, không đổi nghĩa. Faculty trống không đoán từ class_name. Nhiều ứng viên/mơ hồ đưa vào review và guideline trước đánh giá.

Review chéo mục tiêu: annotator không xem predictions → người khác đối chiếu ảnh → record bất đồng → giải quyết bằng source/schema → version/audit/manifest. Người review TBD; foundation chưa có hai người thực hiện. Blur/crop/mask làm mất thông tin cần gán nhãn lại, cùng parent/split. Inference không đọc annotations; evaluator là nơi đọc gold.
