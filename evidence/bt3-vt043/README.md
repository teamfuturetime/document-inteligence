# VT-043 — hướng dẫn tái hiện

Baseline: `997da9fe1cf617dcf4ec53fe5ed2ce2d5a4469ee`, nhánh làm việc `bt3-vt043-autosave`. Xem [review_diff.md](review_diff.md) cho kết luận, traceability và giới hạn; [ai_usage_log.md](ai_usage_log.md) cho quyết định thiết kế và lỗi trong quá trình thực hiện.

## Môi trường

Chạy các lệnh PowerShell từ thư mục gốc repository. Không dùng database hay thông tin đăng nhập thật. Các integration test và performance harness tự tạo database test rồi dọn dẹp.

Môi trường đã thực chạy là Windows 11, Python 3.14.5, Node 24.20.0; phiên bản package cụ thể trong [python_environment.txt](python_environment.txt) và `performance_results.json`. Các backend package có sẵn khác phiên bản pin trong requirements. Không suy diễn rằng đã kiểm chứng môi trường pin hoặc PostgreSQL.

Để dựng môi trường theo cấu hình dự án, dùng Python tương thích với các phiên bản requirements, tạo virtualenv và cài:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r backend/requirements.txt -r backend/requirements-dev.txt -r ai_service/requirements.txt
$env:PYTHONPATH = 'backend'
.venv\Scripts\python -m pytest tests/unit tests/integration -q -p no:cacheprovider
```

Đợt kiểm chứng này dùng Python đã có sẵn và cài công cụ vào `.test-tools/` (không commit):

```powershell
python -m pip install --target .test-tools coverage==7.17.0 pytest-cov==7.1.0 uvicorn==0.54.0
$env:PYTHONPATH = '.test-tools;backend'
python -m pytest tests/unit tests/integration -q -rs --tb=short -p no:cacheprovider
```

Không cài các pin cũ vào Python 3.14 rồi mặc định chúng tương thích. Dùng `python_environment.txt` để đối chiếu môi trường đã đo.

## Frontend

```powershell
Push-Location frontend
npm.cmd ci
npm.cmd run typecheck
npm.cmd test
npm.cmd run test:coverage
npm.cmd run lint
npm.cmd run build
Pop-Location
```

Vitest dùng fake timers cho debounce và deferred promises cho thứ tự hoàn tất request. Không cần server OCR để chạy frontend tests. ESLint và V8 coverage là dependencies phát triển; không thêm dependency runtime.

## Concurrency và migrations

```powershell
$env:PYTHONPATH = '.test-tools;backend'
python -m pytest tests/integration/test_ocr_autosave.py -v -p no:cacheprovider
1..5 | ForEach-Object {
  python -m pytest tests/integration/test_ocr_autosave.py -q -p no:cacheprovider
  if ($LASTEXITCODE -ne 0) { throw 'Concurrency test failed' }
}
python -m pytest tests/integration/test_ocr_revision_migration.py -v -p no:cacheprovider
```

CT-01/03 dùng Barrier trước atomic update, HTTP client và phiên đăng nhập độc lập; mỗi request có SQLAlchemy Session riêng. Sau khi mọi request hoàn tất, dùng Session mới để xác nhận đúng một winner, revision = 1 và OCR gốc không đổi. CT-02 kiểm tra stale write đến sau và reload API. Database là SQLite dạng file, WAL; chưa kiểm chứng PostgreSQL.

Migration test chạy chuỗi Alembic thật: upgrade 0003 → chèn dữ liệu cũ → upgrade head → kiểm tra backfill/default → downgrade 0003 → kiểm tra OCR vẫn còn → upgrade head. Trước khi sử dụng bản này với database ứng dụng, sao lưu và chạy `alembic upgrade head` trong backend với cấu hình database của bạn. Đợt này không migrate database thật.

## HTTP performance — 80 tác vụ

```powershell
$env:PYTHONPATH = '.test-tools;backend'
python scripts/ocr_autosave_performance.py --concurrency 80 --transport tcp
```

Harness mở uvicorn ở cổng loopback tự chọn, tạo database SQLite WAL dùng một lần và 80 session đăng nhập riêng; auth/CSRF vẫn thực thi. P-01 lưu 80 tài liệu độc lập; P-02 tranh chấp một tài liệu. `--transport asgi` có sẵn cho môi trường không mở được socket, nhưng không đo chi phí TCP.

Kết quả và mọi mẫu latency nằm trong [performance_results.json](performance_results.json); cách tính percentile, cấu hình pool, giới hạn và kết luận ở [performance_summary.md](performance_summary.md). Dùng `--output-dir evidence/bt3-vt043/new-run` để giữ nguyên bằng chứng hiện tại khi chạy lại. Không coi 409 đúng kỳ vọng trong P-02 là lỗi correctness.

## Coverage

```powershell
$env:PYTHONPATH = '.test-tools;backend'
python -m coverage run --branch --source=backend/app -m pytest tests/unit tests/integration -q -p no:cacheprovider
python -m coverage report -m --include='*/api/documents.py,*/services/documents.py,*/repositories/documents.py,*/models/document.py,*/schemas/documents.py,*/services/ocr_text.py'
python -m coverage json --include='*/api/documents.py,*/services/documents.py,*/repositories/documents.py,*/models/document.py,*/schemas/documents.py,*/services/ocr_text.py' -o evidence/bt3-vt043/coverage.json
```

Dùng đường dẫn thư mục ở `--source` để tránh import sớm các module SQLAlchemy trước fixtures. Frontend coverage được tạo bằng `npm.cmd run test:coverage`, xuất vào `frontend_coverage/`. [coverage.txt](coverage.txt) phân biệt line/branch/statements và liệt kê các nhánh còn thiếu; không đặt mục tiêu 100%.

## Mutation bắt buộc

```powershell
python scripts/ocr_validation_mutation.py
```

Không chạy backend test khác song song với experiment này. Script chạy test whitespace PASS, tạm bỏ validation trong schema, chạy lại test phải FAIL, và khôi phục byte gốc trong `finally` rồi test PASS. Xem `mutation.diff`, `mutation_before.log`, `mutation_fail.log`, `mutation_restored.log`, `mutation_results.json`. File diff là bằng chứng cố ý tạo lỗi; source cuối không chứa lỗi này.

## Kiểm tra trình duyệt trước khi nộp

Repository chưa cấu hình browser E2E. Các frontend tests dùng jsdom/mock API; không tuyên bố đã chạy browser E2E. Critical journey thủ công còn PENDING: đăng nhập → mở Document Detail đã có OCR → sửa → chờ trạng thái đã lưu → reload kiểm tra nội dung → xác nhận → kiểm tra chỉ đọc → mở lại rà soát. Kiểm tra thêm bản nháp khi chuyển menu trước debounce và lúc có lỗi mạng. Giữ bản sao nội dung khi xử lý conflict; không tự động ghi đè bản mới của client khác.
