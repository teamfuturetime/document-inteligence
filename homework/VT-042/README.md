# BT3 - VT-042: async upload và retry

Phạm Nhật Quang - 23001920 - SE2026-T11. Baseline `db727496312087af6495aa12e7c9a52df3dfa230`.

Nhánh: https://github.com/teamfuturetime/document-inteligence/tree/codex/bt3-vt042-async-retry

Bài nộp: [BT3_23001920_VT-042.pdf](../../output/pdf/BT3_23001920_VT-042.pdf). Commit test/spec: `9a76a6ed5d064336df5ba3eb275f7ee9996e5615`; commit patch: `6289d84e3da04690472506f07c3107549db92181`.

## Chạy

```powershell
uv sync --project backend --locked
uv run --project backend --locked pytest backend/tests/test_async_retry_vt042.py -q
uv run --project backend --locked pytest backend/tests pipeline/tests -q
```

Test workflow dùng provider/decode double công khai; SQLite, transaction và file I/O thật. Không có gold trong inference; bộ test này không đo chất lượng OCR. Native OCR được kiểm riêng bởi `scripts/verify_product.py`.

Specification, kế hoạch và các điểm review ở [spec-and-plan.md](spec-and-plan.md). Test-first và kết quả từng lệnh lưu trong `evidence/`. Nhánh không được merge vào main trong bài làm này.

## Thí nghiệm

Chạy từ repository root; output tái lập mặc định nằm ngoài Git trong `runtime/vt042/`.

```powershell
uv run --project backend --locked python homework/VT-042/experiments.py mutation
uv run --project backend --locked --with coverage==7.17.0 python homework/VT-042/experiments.py coverage
uv run --project backend --locked python homework/VT-042/experiments.py repeat
uv run --project backend --locked python homework/VT-042/performance.py
```

Mutation tạm đổi `>` thành `>=` tại upload byte bound, khôi phục bytes trong `finally` và kiểm lại suite. Chạy mutation riêng, không chạy song song với các tests khác.

Tải: 150 client tasks đồng thời qua TCP loopback, SQLite/file thật; readiness/decode là doubles, worker tắt. Các scenario là key mới, retry cùng key và GET trạng thái. `performance.json` giữ toàn bộ request, kể cả 429/error; p95 dùng nearest-rank. Capacity 5 làm 145/150 upload mới bị từ chối; kết quả này không là phép đo hoàn tất 150 tác vụ OCR.

## Kết quả ngày 03/11/2026

- Baseline: 2 failed, 22 passed; hai forced races trả 429 sai contract.
- Sau patch: 24 passed; bộ hồi quy backend/AI: 96 passed.
- Mutation: 1 failed, 2 passed tại boundary; sau khôi phục: 24 passed.
- Lặp suite 3 lần và đảo thứ tự: cả 4 lượt pass, 24 tests/lượt.
- Native OCR/HTTP: 14 checks passed; frontend: 7 tests, contracts/typecheck/lint/format/build pass.
- Full command/results: `evidence/checks-backend.json`, `checks-frontend.json`, `native-workflow.json` và các logs.

`npm audit` ghi 15 advisories (13 moderate, 2 high) trong dependency tree hiện hữu; lockfile không thay đổi trong slice này. Workflow hiện chạy trên PR hoặc push main, không chạy trên push nhánh bài tập; không ghi nhận remote CI pass.

## Phạm vi diff

Implementation chỉ thêm 19 dòng ở `backend/src/docintel/services/documents.py`: re-read key dưới write transaction trước capacity, đối chiếu fingerprint và xóa file của request thua. Không đổi API/schema, pipeline AI, model/data/config. Hai bài VT-043 autosave và VT-045 config-contract chỉ được đối chiếu source để tránh trùng phạm vi; không sử dụng test/data/reflection của các bài đó.

## Sinh PDF

```powershell
uv run --with-requirements homework/VT-042/report-requirements.txt python homework/VT-042/build_report.py
```

Renderer dùng Times New Roman từ `C:/Windows/Fonts`; có thể truyền `--font-dir` trỏ tới thư mục có `times.ttf` và `timesbd.ttf`. Nguồn nội dung đọc các số liệu đã lưu trong evidence, không tự sinh test results khi dựng PDF.
