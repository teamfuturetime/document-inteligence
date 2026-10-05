# Evaluation

Logic duy nhất trong package backend/evaluation, scripts gốc là entry point mỏng:

```powershell
uv run --project backend --locked python scripts/check_data.py
uv run --project backend --locked python scripts/evaluate_fixtures.py
```

Ghi `reports/fixture-contract.json` + `fixture-contract-run.json`; `--output runtime/ci/fixture-contract.json` để CI không đổi report commit. Report có run ID/type/source/versions/support/counts/null reasons; không latency hay accuracy AI thật. [Protocol](../docs/ml/evaluation-protocol.md). Examples prediction/error có nhãn fixture/illustrative.

**Chưa có lệnh inference/model benchmark thật**, chưa đo; job skipped không đạt AI quality. BL-009 thêm command/manual workflow khi có provider/quyền; tách CI foundation không key/GPU. `evaluate(..., source='model')` có thể chấm predictions offline nhưng phải bổ sung pipeline/metadata đầy đủ trước công bố. Không reviewed values hoặc seed quality gate.
