# Evaluation và regression — Phase 6

Dataset [golden-1.0.0](../data/golden/README.md) gồm 30 ID độc lập, split 18 dev/
12 test, manifest/hash/ground truth. Các file được xác minh hash trước khi chạy;
path traversal, duplicate ID, schema sai hoặc hash lệch đều bị từ chối.
Chỉ dùng dev để thay config/rules. Không tuning theo test hoặc đổi target .85
để làm báo cáo xanh. Review ground truth độc lập vẫn cần người khác trong nhóm.

## Chạy và tái lập

```bash
uv sync --locked
.venv/bin/python -m document_pipeline.ocr_models --directory data/models/tessdata
.venv/bin/python -m document_evaluation.cli --tessdata-dir data/models/tessdata --split test --output evaluation/reports/test.json --check
.venv/bin/python -m document_evaluation.cli --tessdata-dir data/models/tessdata --split all --output evaluation/reports/all.json
.venv/bin/python -m pytest evaluation/tests --run-ocr --tessdata-dir=data/models/tessdata -q
```

CLI dùng cùng pipeline/deadline với API, từ chối mock. Không có edit/review trong
đường đo chất lượng. `--check` trả exit 2 nếu macro exact match < .85 hoặc có
execution error; input/manifest lỗi trả exit 1. Report ghi các lỗi thực thi,
không bỏ tài liệu lỗi khỏi denominator. Output nằm ngoài dataset đóng băng.

Report không thêm timestamp/duration ngẫu nhiên. Cùng files/engine/model/config/
source và trạng thái Git cho cùng JSON. Metadata: Git SHA/dirty, hash source +
lockfile, Python/platform/dependency versions, dataset hash, seed trong manifest,
engine/model/config/rules và prediction/evidence của từng tài liệu. Engine/OS
khác có thể khác OCR; không so snapshot byte giữa macOS 5.5.2 và Ubuntu 5.3.4.

## Metrics

So sánh NFC/trim/collapse whitespace, không bỏ dấu hoặc lowercase tên. Ngày ISO,
tiền integer từ normalized contract. Exact match tính cả null-null và báo riêng
`null_pairs`, `support` non-null để không che field thiếu.

Non-null đúng = TP; dự đoán sai non-null khi truth non-null = FP + FN;
dự đoán thừa = FP; bỏ sót = FN. Null-null không là TP. Precision/recall/F1 có
denominator 0 trả null (N/A). Macro lấy trung bình các field có metric xác định;
micro gộp count. Report từng field và slice layout/condition/split, không chỉ
một điểm trung bình. Metrics có tests với count tính tay, all-null/empty/Unicode.

## Taxonomy và điều tra lỗi

Mỗi mismatch ghi `symptom`: missing/unexpected/wrong_value và `cause=unverified`
ban đầu. Execution errors ghi riêng mã lỗi. Không suy đoán mọi sai lệch là OCR.
Khi review error, đối chiếu ảnh → preprocessing → OCR token → rule evidence:

| Cause sau xác minh | Evidence cần kiểm tra |
| --- | --- |
| `input_quality` | blur/skew/compression trên ảnh gốc |
| `preprocessing` | ảnh chuẩn hóa/hướng/DPI/transform không đúng |
| `ocr_text` | text OCR khác chữ thực trên ảnh |
| `field_mapping` | OCR đúng nhưng chọn nhãn/ứng viên sai |
| `normalization` | raw evidence đúng nhưng date/amount/string chuyển sai |
| `validation` | field hợp lệ bị từ chối hoặc invalid được chấp nhận |
| `unsupported_layout` | nhiều cột/nhãn khác dòng ngoài baseline |

Giữ symptom và cause đã xác minh riêng, không sửa ground truth theo output AI.
Golden regression chạy engine thật trên 12 holdout documents, target .85;
CI job real OCR thu thập marker ở cả backend/pipeline/evaluation.
