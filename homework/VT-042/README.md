# BT3 - VT-042: async upload và retry

Phạm Nhật Quang - 23001920 - SE2026-T11. Baseline `db727496312087af6495aa12e7c9a52df3dfa230`.

Nhánh: https://github.com/teamfuturetime/document-inteligence/tree/codex/bt3-vt042-async-retry

## Chạy

```powershell
uv sync --project backend --locked
uv run --project backend --locked pytest backend/tests/test_async_retry_vt042.py -q
uv run --project backend --locked pytest backend/tests pipeline/tests -q
```

Test workflow dùng provider/decode double công khai; SQLite, transaction và file I/O thật. Không có gold trong inference; bộ test này không đo chất lượng OCR. Native OCR được kiểm riêng bởi `scripts/verify_product.py`.

Specification, kế hoạch và các điểm review ở [spec-and-plan.md](spec-and-plan.md). Test-first và kết quả từng lệnh lưu trong `evidence/`. Nhánh không được merge vào main trong bài làm này.
