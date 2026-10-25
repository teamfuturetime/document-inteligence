# Protocol đánh giá

Sản phẩm có evaluator `docintel.evaluation.product`, generator 150 synthetic parents và CLI `scripts/evaluate_model.py`. Output tách report model trước review với fixture check. Dataset/splits/hashes được kiểm; report có present accuracy, strict types/dấu/zero, PRF/support, unreadable/absent, confidence buckets và document exclusions. [Dataset card](../../data/product/README.md) nêu giới hạn và review nhãn còn cần nhóm thực hiện.

Unit document_id + field_id, dùng **máy trước review**; `nfc-whitespace-date-1.0.0`: NFC, gộp whitespace, ngày dd/mm/yyyy rõ về ISO khi tồn tại, giữ dấu/số 0; không fuzzy/casefold. Ngày sai nhìn thấy giữ chuỗi sai, validation không đổi gold.

| Gold/prediction | Counts |
| --- | --- |
| Present/readable đúng | TP |
| Present null/missing | FN + missing |
| Present sai non-null | FP + FN + wrong |
| Absent non-null | FP + extra |
| Absent null | Correct abstention riêng, không TP |
| Unreadable | Loại value matching; support/abstain/non-null riêng |

Precision TP/(TP+FP); recall TP/(TP+FN); F1 2TP/(2TP+FP+FN). Mẫu số 0 null + ZERO_DENOMINATOR, không NaN/100%. Per-field support present, predicted_non_null đủ điều kiện, correct/wrong/missing, absent support/extra_fill_rate, unreadable support/rate. Micro cộng counts; macro mean từng metric fields có denominator xác định + field support. Missing document là null; duplicate IDs/unknown prediction document fail. Seed gold đủ bảy fields.

Document exact match chỉ document có cả bảy required gold present/readable; prediction sai/null fail, excluded ghi lý do. Confidence model + heuristic/calibrated có score mới có bucket support/accuracy; fixture/unknown bị loại. Latency scaffold null NOT_MEASURED; thật phải ghi hardware/cold-warm/config.

Test công thức **minh họa**: 50 present, 48 non-null, 45 đúng → TP45 FP3 FN5, precision45/48, recall45/50, F1=90/98. Seed report evaluator_contract_check + fixture, không chất lượng model/quality gate.

BL-003/004/008/009: chốt config trên development/validation → đóng băng test → inference thật không gold → predictions + run metadata → evaluator/report/taxonomy. Tune theo test ghi contamination và đo độc lập mới. Validation split khác rules nghiệp vụ.

Post-review study riêng: fields sửa/thời gian/lỗi còn lại; so nhập tay phải kiểm soát độ khó/hiệu ứng nhớ. Foundation chưa có người tham gia, số thời gian tiết kiệm hay kết luận thống kê.
