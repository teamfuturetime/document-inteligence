# Bàn giao phiên — 21/10/2026 (Asia/Saigon)

## Task và Git

- S3.2 — OCR thật trên ảnh mẫu tổng hợp đã triển khai và kiểm thử local.
- Branch `tuannguyen`; HEAD nền lúc bắt đầu:
  `39c67892655b0e0113c082aae2fb355d26fcb5b9` — `docs: add session progress handoff`.
  Working tree lúc đó sạch, ahead 1 so với origin/tuannguyen theo refs local.
- Commit S3.2 dự kiến `feat: add local Tesseract OCR adapter`; HEAD sau bàn giao xem
  bằng `git log -1 --oneline`. Không push/fetch/merge trong S3.2; remote refs chưa
  được làm mới. Sau commit này dự kiến ahead 2 so với origin/tuannguyen đã biết.

## Đã hoàn thành

- OCRProvider/OCRResult riêng, adapter Tesseract và CLI local nhận PNG/JPEG bytes.
  Giữ text/TSV, word/bbox/native score, hash input/ảnh xử lý/model/config và version.
- Giải mã bằng Pillow 13.0.0, áp dụng EXIF, alpha trên nền trắng; guard ảnh
  10 MiB/20 triệu pixel, từ chối nhiều frame. Timeout từng subprocess, dọn file tạm.
- Chọn Tesseract 5.5.0.20241111, vie tessdata_fast, OEM 1/PSM 6/DPI 300.
  Hash vie đã so với file chính thức; engine/model Apache-2.0, không phân phối model.
- Ba ảnh smoke hoàn toàn tổng hợp, generator/manifest; đã xem PNG trực quan.
  37 unit test OCR và 7 test tích hợp/mẫu, trong đó 5 ca chạy OCR thật.
- S3.1, schema sales_invoice 1.0.0, normalization/validation, health và frontend giữ nguyên.
  Không có VLM, field extraction mới, API upload/review/export hoặc metrics.

## Kiểm tra thực tế

- `.\.venv\Scripts\python.exe -m pytest -c backend/pytest.ini -q`:
  baseline 419 passed in 0.95s; sau S3.2 **463 passed in 2.74s**, không warning/skip.
- `.\.venv\Scripts\python.exe -m pytest -c backend/pytest.ini backend/tests -q --require-real-ocr`:
  **463 passed in 2.81s**, không warning/skip.
- `.\.venv\Scripts\python.exe -m pytest -c backend/pytest.ini -q -m "not ocr_real"`:
  **456 passed, 7 deselected in 1.12s**; không cần Tesseract.
- `.\.venv\Scripts\python.exe -m pip check`: No broken requirements found.
- `git diff --check`, `git diff --cached --check`: kiểm tra trong quy trình review/commit.
- Backend chưa cấu hình type checker/linter; không chạy frontend tests ở S3.2.

## Lỗi đã xử lý và giới hạn

- Cài Pillow/đọc hash model chính thức trong sandbox bị chặn mạng; chạy lại với
  quyền mạng đã cấp thành công. Chỉ cài trong .venv, không sửa Tesseract/model hệ thống.
- Cờ pytest --require-real-ocr cần truyền rõ backend/tests để nạp conftest trước parse;
  lệnh đầu thiếu đường dẫn bị từ chối option, lệnh đúng phía trên đã đạt.
- OCR vie còn đọc nhầm TỔNG thành TỎNG, GIẢ LẬP thành GIÁ LẬP trên mẫu. Giữ nguyên
  raw output, không sửa dấu để làm kết quả có vẻ tốt hơn. Chưa có metric/benchmark.
- Timeout là giới hạn riêng từng tiến trình version/OCR, không bao gồm decode/hash.
- Chưa nối OCR vào extraction S3.1; native score không phải confidence cấp trường.
- Frontend vẫn chưa được kiểm tra trực quan; S3.3 chưa bắt đầu. Không có code dở đã biết.

## Phiên sau

1. Đọc bản bàn giao, kiểm tra branch/HEAD/status/diff và commit mới; giữ mọi thay đổi
   phát sinh sau bàn giao. Không giả định refs remote còn mới hoặc tự push.
2. Task tiếp theo duy nhất theo roadmap: **S3.3 — VLM thật và confidence**. Trước khi
   triển khai, kiểm tra tài nguyên/model/license và phạm vi được giao; không làm lại S3.2.
3. Đọc [README](../README.md), [requirements](requirements.md),
   [architecture](architecture.md), [roadmap](roadmap.md), [testing](testing.md),
   [OCR local](ocr.md), [ADR 0001](adr/0001-local-tesseract-ocr.md) và
   `..\MASTER_PROMPT_AI02_Solo_Development.md` ngoài repo.
4. Code liên quan: schemas/{invoice,extraction,ocr}.py, providers/{contracts,ocr,tesseract,fake}.py,
   services/pipeline.py, app/ocr_cli.py trong backend/app; tests/test_ocr*.py,
   tests/test_pipeline.py, tests/conftest.py trong backend; data/ocr-smoke/.