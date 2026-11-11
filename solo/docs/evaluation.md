# Phương pháp đo

API và CLI cùng gọi `pipeline.run`; không có extractor đánh giá riêng, không
dùng kết quả sau review làm đầu vào phép đo. Dataset đã freeze ở commit
`93afac7`, trước lượt metrics đầu tiên. Xem [dataset](../data/README.md).

Từ thư mục `solo/`:

```bash
uv run --locked python -m ai02_solo.evaluate --split dev --mode rules --output evaluation/reports/dev-rules.json
uv run --locked python -m ai02_solo.evaluate --split test --mode rules --output evaluation/reports/test-rules.json --check
uv run --locked python -m ai02_solo.evaluate --split all --mode rules --output evaluation/reports/all-rules.json
```

Mục tiêu ban đầu macro exact match ≥0,85 trên test, đồng thời không có execution
error (`--check` exit 2 nếu không đạt). Chỉ số macro chung không thay thế số liệu
từng schema/trường. Luôn xem các trường kém để lên backlog. Không tuning bằng
holdout test; thử config/model mới trên dev trước, giữ test để báo cáo cuối.

Exact match phân biệt dấu/chữ hoa và so sánh giá trị canonical; ngày ISO, số tiền
integer. Cặp null-null được tính exact match nhưng báo số lượng riêng và không
được tính TP. Sai giá trị non-null là cả FP và FN; thừa là FP; thiếu là FN.
Precision/recall/F1 không có denominator trả null thay vì tự coi là 1.0. Có metrics
từng trường theo schema, micro chung và slices theo schema/split/layout/condition.

Report kiểm tra hash tài liệu/ground truth và từ chối duplicate/path traversal;
lưu hash manifest, code, lockfile, Git SHA/dirty, Python/platform/dependency,
Tesseract/model hashes, luật/prompt/model revision. Không ghi API key/URL vào
report. Không chèn timestamp/duration làm report rules thay đổi giữa hai lượt.
VLM có seed/temperature cố định nhưng chưa đảm bảo deterministic trên mọi runtime.

## Phân loại lỗi

Rule `solo-labels-2` bổ sung ghép gần đúng cho nhãn dài ≥10 ký tự có dấu hai
chấm, tối đa một edit và duy nhất một trường. Không tự sửa giá trị OCR. Thay
đổi được xác định từ lỗi dev `application-001` trên Linux; rules/config hash và
source hash mới được lưu riêng, không ghi đè baseline v1. Xem
[verification](verification.md) để phân biệt số liệu theo OS/engine.

`symptom` là quan sát tự động: `missing_prediction`, `unexpected_prediction`,
`wrong_value`, `diacritic_or_case_difference`; execution error được báo riêng.
`cause` ban đầu `unverified` để không gán mọi lỗi cho OCR khi chưa đối chiếu.
Khi triage, ghi ID, trường, ảnh, OCR text, evidence, config/model và người kiểm tra.

| Cause sau kiểm tra | Bằng chứng cần đối chiếu |
| --- | --- |
| `input_quality` | Chữ trên ảnh không đủ rõ để đọc |
| `preprocessing` | Nội dung bị cắt/đổi chiều khi render/EXIF |
| `ocr_text` | Ảnh đúng nhưng OCR khác ground truth |
| `field_mapping` | OCR có đủ chữ nhưng extractor gán nhầm/không tìm thấy |
| `normalization` | Raw value đúng nhưng chuẩn hóa sai |
| `validation` | Quy tắc kiểm tra từ chối/chấp nhận sai |
| `unsupported_layout` | Layout vượt phạm vi baseline đã công bố |
| `model_generation` | VLM sinh dữ liệu không được ảnh hỗ trợ hoặc JSON sai |

Theo lựa chọn của chủ dự án, mới chuẩn bị hai adapter VLM, chưa cấu hình model.
Lệnh `--mode vlm` hoặc `--mode hybrid` hiện từ chối chạy nếu chưa cấu hình;
không có chỉ số VLM và không dùng mock để lấp báo cáo. Sau khi chọn model, chạy
cùng manifest/split cho cả ba chế độ; so sánh chất lượng, thời gian và lỗi.
