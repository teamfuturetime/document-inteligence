# Evaluation

Product 0.2.0 có evaluator `docintel.evaluation.product` cho invoice/application và `scripts/evaluate_model.py`; labels chỉ được evaluator đọc sau prediction. [Các run thực](runs/2026-10-24-test-frozen/report.json), [policy profile](reports/confidence-selection-2026-10-24.json), [candidate hashes](reports/product-candidate-2026-10-24.json). Mỗi run giữ predictions.json và report.json; test source đã freeze, không tune trên test. Bộ synthetic nhỏ/template đã biết không là độ chính xác tổng quát.

Reproduce policy profile từ cache validation baseline: `uv run --project backend --locked python scripts/select_confidence_policy.py --run-dir evaluation/runs/2026-10-24-validation-baseline --output runtime/evaluation/profile-new.json`. Muốn tạo baseline mới, evaluate_model hỗ trợ `--config configs/pipeline-baseline.json`; luôn dùng output directory mới. Không đưa report/prediction artifacts vào inference.

Logic duy nhất trong package backend/evaluation, scripts gốc là entry point mỏng:

```powershell
uv run --project backend --locked python scripts/check_data.py
uv run --project backend --locked python scripts/evaluate_fixtures.py
```

Ghi `reports/fixture-contract.json` + `fixture-contract-run.json`; `--output runtime/ci/fixture-contract.json` để CI không đổi report commit. Report có run ID/type/source/versions/support/counts/null reasons; không latency hay accuracy AI thật. [Protocol](../docs/ml/evaluation-protocol.md). Examples prediction/error có nhãn fixture/illustrative.

**Chưa có lệnh inference/model benchmark thật**, chưa đo; job skipped không đạt AI quality. BL-009 thêm command/manual workflow khi có provider/quyền; tách CI foundation không key/GPU. `evaluate(..., source='model')` có thể chấm predictions offline nhưng phải bổ sung pipeline/metadata đầy đủ trước công bố. Không reviewed values hoặc seed quality gate.
