# Confidence

## Product policy 1.1.0 — 24/10/2026

`evidence-minimum-ocr-abstain-1.1.0`: minimum OCR score của các token evidence, mapping signals/candidate count/reasons, heuristic không phải calibrated probability. Nhiều giá trị mâu thuẫn luôn abstain; score không có thì giữ unknown, không biến thành 0%. Candidate có score dưới 0.5 được để null, giữ evidence/reason LOW_OCR_EVIDENCE để người dùng đối chiếu.

Ngưỡng này được chọn trên **30 validation documents**, trước khi chạy test. Profile 0/0.25/0.5/0.75: cả bốn giữ 174 trường present đúng trên 176; 0 và 0.25 từ chối 0/2 vùng unreadable, 0.5 và 0.75 từ chối 2/2. Chọn 0.5 là ngưỡng nhỏ nhất trong grid đạt mục tiêu đó, không tăng lên 0.75. Support unreadable rất nhỏ; đây không chứng minh tổng quát hoặc calibration. [Profile và report](../../evaluation/reports/confidence-selection-2026-10-24.json) lưu counts và run nguồn. Đổi threshold phải đổi version/config/hash và đo lại trước holdout.

## Foundation policy lịch sử

`confidence-draft-1`: method unknown/simulated/heuristic/calibrated, score/ocr_score/mapping_signals/policy_version/reason_codes. Scaffold tất cả fixture method unknown, scores null, FIXTURE_NOT_MEASURED. Unknown không có score; không bịa weights/ngưỡng. UI nói rõ chưa đo, không phải xác suất đúng.

Engine thật có thể giữ OCR aggregation từ spans **của field** và mapping signals nhãn/vị trí/candidate/evidence. Heuristic phải ghi rõ; không trung bình trang cho mọi field, không lấy lời tự tin model làm probability. Calibration cần phương pháp và dữ liệu riêng; 0.95 chưa đồng nghĩa đúng 95%.

BL-010 chọn review thresholds trên validation sau baseline, version/freeze trước test, báo support và accuracy từng nhóm. Evaluator có bucket mô tả `[0,0.5)`, `[0.5,0.8)`, `[0.8,1]` tách heuristic/calibrated; không threshold review hay quality gate. Simulated/unknown không vào real-confidence buckets; thiếu tín hiệu report NO_REAL_CONFIDENCE. Chưa calibrate/chạy policy thật. Tham khảo [Guo et al.](https://proceedings.mlr.press/v70/guo17a.html).
