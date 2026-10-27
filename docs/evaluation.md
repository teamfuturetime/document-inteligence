# Đánh giá AI và OCR

## Trạng thái bằng chứng

Repository có một regression set nhỏ gồm 7 tài liệu tổng hợp được sinh từ nội dung
gán nhãn trước khi OCR. Tập này không đại diện cho tài liệu thực tế và không đủ để
tuyên bố độ chính xác tổng quát.

## Kết quả Tesseract thực tế

Đo trong Docker với Tesseract 5.5.0. Baseline là pipeline cũ (PSM 6); improved là
pipeline layout-aware. Số thấp hơn tốt hơn với CER/WER, số cao hơn tốt hơn với
reading order.

| Ngôn ngữ | Pipeline | CER | WER | Reading order |
|---|---:|---:|---:|---:|
| `vie` | Baseline | 0.0373 | 0.1064 | 0.5520 |
| `vie` | Improved | 0.0170 | 0.0801 | 0.6561 |
| `vie+eng` | Baseline | 0.0441 | 0.1305 | 0.5316 |
| `vie+eng` | Improved | 0.0386 | 0.1593 | 0.6173 |

Trên fixture hóa đơn duy nhất, structure recall và exact accuracy của trường MST
đều là 1.0. Một ô số lượng bị Tesseract bỏ sót; bảng vẫn được giữ theo tọa độ và
đánh dấu cần kiểm tra, không tự tạo giá trị. `vie` được giữ làm mặc định vì tốt hơn
`vie+eng` trên tập này.

Chạy lại trong runtime có Tesseract:

```powershell
python scripts/evaluate_ocr.py --languages vie vie+eng
```

Script tính CER, WER, reading-order score, exact field accuracy và structure recall;
không dùng output OCR làm ground truth.

## Classifier

Classifier vẫn là luật giải thích được. `classification.confidence` là heuristic,
không phải xác suất đã hiệu chuẩn. Output giữ `raw_score`, `matched_rules`,
`confidence_type` và `needs_review`.

## Kế hoạch đánh giá mở rộng

1. Thu thập/ẩn danh dữ liệu có consent cho từng loại và nhóm `unknown`.
2. Tách tập test trước khi điều chỉnh rule; không dùng test set để tune.
3. Báo confusion matrix, macro-F1, coverage của `unknown`, tỷ lệ cần review và lỗi OCR.
4. Đánh giá riêng scan mờ, xoay, thiếu dấu và dữ liệu ngoài phân phối.
5. Chỉ hiệu chuẩn confidence khi đủ dữ liệu; lưu version rule/dataset.

Unit test bao phủ numeric token, bảng, hai cột, Unicode, preprocessing và metrics.
Benchmark Docker dùng Tesseract thật nhưng dữ liệu vẫn là tổng hợp; cần tập test
thực tế được cấp phép trước khi công bố chất lượng production.
