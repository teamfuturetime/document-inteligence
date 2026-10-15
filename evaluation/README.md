# Evaluation

Owner: thành viên 5; Technical Lead review phương pháp đo.

CLI gọi cùng `run_document` với backend, xác minh manifest/hash, không dùng mock.

```bash
uv run --locked python -m document_evaluation.cli --tessdata-dir data/models/tessdata --split test --output evaluation/reports/test.json --check
```

Report ghi exact match/PRF từng field, macro/micro, null support, slice theo
layout/condition/split, mismatches và engine/model/config/source versions.
`--check` fail nếu macro exact match < .85; mọi execution error cũng fail.
Report lớn nằm trong `reports/` đã ignore. Xem [evaluation guide](../docs/evaluation.md).
