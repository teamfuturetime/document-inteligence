# Error taxonomy

Mã ổn định, severity độc lập category. Record: sample_id, field_id, run_id, expected, predicted, primary_cause, secondary_tags, severity, status, issue_reference. [Ví dụ synthetic/illustrative](../../evaluation/examples/error-illustrative.json), không thống kê model thực nghiệm.

| Mã | Nguyên nhân |
| --- | --- |
| INPUT_QUALITY | Mờ/nghiêng/cắt nội dung |
| OCR_CHARACTER | Nhầm chữ/số/dấu |
| OCR_LAYOUT | Thứ tự đọc/ghép dòng/cột |
| FIELD_MAPPING | Gán nhầm trường |
| FIELD_MISSING | Bỏ sót giá trị đọc được |
| UNSUPPORTED_VALUE | Giá trị không bằng chứng |
| NORMALIZATION | Sai nghĩa/mất số 0 |
| VALIDATION_RULE | Rule thiếu/sai/báo sai |
| REVIEW_STATE | Mất sửa/xung đột revision |
| EXPORT_STALE | Bản cũ/chưa confirmed |
| PROVIDER_FAILURE | Timeout/unavailable/quota/rate limit |

Primary cause dựa ảnh/spans/rules/evidence, secondary ghi hậu quả. OCR dẫn field sai chỉ tính một primary, không cộng trùng tùy tiện. Severity critical/high/medium/low theo ảnh hưởng, không category; status open/investigating/resolved/accepted, issue_reference null khi chưa issue thật. QA ghi sample/run/config/expected/actual/repro, chỉ đính kèm data hợp lệ.
