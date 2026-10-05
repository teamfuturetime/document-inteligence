# Confidence

`confidence-draft-1`: method unknown/simulated/heuristic/calibrated, score/ocr_score/mapping_signals/policy_version/reason_codes. Scaffold tất cả fixture method unknown, scores null, FIXTURE_NOT_MEASURED. Unknown không có score; không bịa weights/ngưỡng. UI nói rõ chưa đo, không phải xác suất đúng.

Engine thật có thể giữ OCR aggregation từ spans **của field** và mapping signals nhãn/vị trí/candidate/evidence. Heuristic phải ghi rõ; không trung bình trang cho mọi field, không lấy lời tự tin model làm probability. Calibration cần phương pháp và dữ liệu riêng; 0.95 chưa đồng nghĩa đúng 95%.

BL-010 chọn review thresholds trên validation sau baseline, version/freeze trước test, báo support và accuracy từng nhóm. Evaluator có bucket mô tả `[0,0.5)`, `[0.5,0.8)`, `[0.8,1]` tách heuristic/calibrated; không threshold review hay quality gate. Simulated/unknown không vào real-confidence buckets; thiếu tín hiệu report NO_REAL_CONFIDENCE. Chưa calibrate/chạy policy thật. Tham khảo [Guo et al.](https://proceedings.mlr.press/v70/guo17a.html).
