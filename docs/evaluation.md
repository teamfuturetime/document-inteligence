# Đánh giá AI

## Trạng thái bằng chứng

Repository chưa có tập dữ liệu biểu mẫu tiếng Việt đã gán nhãn và chưa có phép đo
accuracy, precision, recall hay F1. Vì vậy dự án không tuyên bố độ chính xác.

Classifier hiện là luật giải thích được. Output gồm:

- `raw_score`: tổng trọng số keyword/regex của nhãn tốt nhất;
- `confidence`: heuristic 0–100, bị chặn dưới 100;
- `confidence_type`: luôn là `heuristic`;
- `matched_rules`: tín hiệu đã khớp;
- `needs_review`: true với bằng chứng yếu, confidence thấp hoặc kết quả mơ hồ;
- `unknown`: fallback cho không có bằng chứng hoặc hòa điểm.

Unit test bao phủ văn bản rõ, rỗng, nhiễu, không dấu, hòa điểm, điểm gần và nhiều
rule. Đây không phải đánh giá chất lượng trên dữ liệu thật.

## Kế hoạch đánh giá hợp lệ

1. Thu thập/ẩn danh dữ liệu có consent cho từng loại và nhóm `unknown`.
2. Tách tập test trước khi điều chỉnh rule; không dùng test set để tune.
3. Báo confusion matrix, macro-F1, coverage của `unknown`, tỷ lệ cần review và lỗi OCR.
4. Đánh giá riêng ảnh scan mờ, xoay, thiếu dấu và dữ liệu ngoài phân phối.
5. Chỉ hiệu chuẩn confidence khi đủ dữ liệu; lưu version rule/dataset.

## Kiểm thử hiện tại

Unit test dùng văn bản tổng hợp và mock pipeline. Integration/E2E với PostgreSQL,
Tesseract runtime và container chưa được triển khai; không được gọi các mock đó là E2E.
