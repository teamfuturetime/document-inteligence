# Bàn giao phiên — 22/10/2026 (Asia/Saigon)

## Task và Git đã xác minh

- Task: finalize, kiểm tra/commit/push tiến trình; không phát triển inference hoặc cài thêm.
- Branch `tuannguyen`; origin fetch/push:
  `https://github.com/teamfuturetime/document-inteligence.git`.
- Đầu phiên: HEAD `7a28be309eb3da380795a46d7c738105351dafbf`, 3 file tracked sửa,
  15 file untracked, index rỗng. Bảo toàn và lưu toàn bộ nguồn/tài liệu hợp lệ.
- Fetch origin thành công; trước commit local hơn 2 commit, remote riêng 0.
- HEAD tiến trình chính đã push và kiểm tra trực tiếp bằng ls-remote:
  **`8d94093ee0d856dcc9d3fface55d1f956aa547de`**.
- `git push origin tuannguyen` trả exit 0:
  `d620342..8d94093 tuannguyen -> tuannguyen`. Local HEAD, origin/tuannguyen và
  remote HEAD khớp; ahead/behind 0/0, working tree sạch trước sửa bản bàn giao này.
- Lần push chính đưa lên ba commit:
  `39c6789 docs: add session progress handoff`,
  `7a28be3 feat: add local Tesseract OCR adapter`,
  `8d94093 feat: add offline invoice benchmark and VLM preflight`.
  Commit mới lưu 18 file, 1886 dòng thêm/7 dòng bỏ.
- Bản bàn giao được ghi sau test và push chính thành công, rồi tạo commit riêng
  `docs: update session handoff after progress push`.
  HEAD cuối phiên gồm thêm commit bàn giao này; tra hash bằng
  `git log -1 --format=%H -- docs/session-handoff.md` (không ghi hash tự tham chiếu).
  Trạng thái push ở trên là lần push chính đã xác minh trước khi ghi file;
  kết quả push commit bàn giao được xác minh và báo trong phản hồi kết thúc phiên.

## Tiến trình đã bảo toàn

- S3.1: extraction contract/pipeline/fake có từ d620342, giữ nguyên.
- S3.2: Tesseract adapter/CLI, text/TSV/bbox/native score/provenance, ảnh tổng hợp và
  guards ở 7a28be3; không sửa hành vi. Lỗi dấu OCR còn được ghi trong docs/ocr.md.
- S3.3.1: khảo sát VLM, nguồn chính thức, giới hạn phần cứng, confidence/provenance.
- S3.3.2a: runner ba mode, strict JSON/fence parser, evidence adapter, metric theo
  field và fixture offline; 68 test mới. Report fixture_simulation,
  inference_performed=false; không phải chất lượng/tốc độ VLM.
- S3.3.2b: **chỉ có preflight Giai đoạn 0–1; chưa được xác nhận cho phép tải**,
  chưa tải weights/runtime, chưa có provider/inference hoặc benchmark VLM thật.
- Canonical sales_invoice 1.0.0, normalization/validation S2, health và frontend
  giữ nguyên. README/roadmap/testing cập nhật trạng thái finalize.

## Kiểm tra và an toàn

```powershell
.\.venv\Scripts\python.exe -m pytest -c backend/pytest.ini -q -p no:cacheprovider
git diff --check
git diff --cached --check
```

- **531 passed in 4.09s**, không warning/skip; không sửa test để làm suite pass.
  Diff checks đạt, đã review staged diff/stat và đối chiếu với file làm việc,
  kiểm UTF-8/Python syntax/JSON/liên kết nội bộ. Không cài dependency.
- Không chạy lại frontend; backend chưa cấu hình type checker/linter riêng.
- Rà soát 68 file trong cây dự án và 92 blob lịch sử nhánh trước commit: không phát
  hiện secret thực tế hoặc file lịch sử vượt 5 MiB. Hai pattern secret=DO_NOT_EXPOSE
  trong test sanitization là tổng hợp, đã đọc và xác minh.
- File lớn nhất khoảng 124 KB là JPEG tổng hợp S3.2; manifest ghi nguồn CC0, font
  không phân phối. Fixture mới tổng hợp, không dùng hóa đơn/dữ liệu cá nhân thật.
- Không đưa .env, .venv, node_modules, cache/build, weights hoặc executable tải về
  vào Git. Đã kiểm .gitignore và staged files; không bỏ sót nguồn/tài liệu untracked.
- Sandbox chặn .git/FETCH_HEAD và index.lock ban đầu; chạy lại Git với quyền được
  cấp thành công. Không có lỗi test/bảo mật/xung đột lịch sử đang chặn.
  Không reset, amend, merge, force-push, xóa file hoặc sửa lịch sử.

## Phiên sau

Task tiếp theo duy nhất: **tiếp tục S3.3.2b sau khi người dùng xác nhận cho phép
tải model/runtime**. Quyền commit/push cuối phiên không phải quyền tải model.

1. Kiểm tra lại branch/HEAD/status/diff/remote, giữ mọi thay đổi mới. Đọc preflight
   và xác nhận quyền tải nếu chưa có; không coi snapshot này là Git hiện tại.
2. Phương án chờ: Qwen3-VL-4B Q4_K_M + mmproj F16 + llama.cpp b11669 CPU,
   khoảng 3.35 GB tải/6 GiB đĩa dự trù; revision/hash/license/lệnh ở preflight.
   Kiểm tra lại nguồn/tài nguyên; chưa có RAM peak/latency/GPU acceleration đã đo.
3. Sau cho phép mới tải/kiểm hash/runtime, tạo OCR snapshot thật, provider real có
   guard/provenance, smoke rồi ba mode; không fallback fixture thành inference.
   Dataset chỉ một invoice PNG/JPEG và một blank, chưa đủ xếp hạng model.
4. Frontend vẫn chưa kiểm tra trực quan; chưa tích hợp OCR/VLM vào API/UI/export,
   chưa calibration hoặc confidence extraction có cơ sở; confidence giữ null.

Đọc [README](../README.md), [roadmap](roadmap.md), [preflight](vlm-preflight.md),
[khảo sát VLM](vlm-survey.md), [benchmark offline](benchmark-offline.md),
[requirements](requirements.md), [architecture](architecture.md),
[testing](testing.md), [OCR](ocr.md), [ADR 0001](adr/0001-local-tesseract-ocr.md)
và Master Prompt ngoài repo. Code: backend/app/benchmark/, providers/tesseract.py,
schemas/{invoice,extraction,ocr}.py; tests/test_benchmark.py, test_ocr*.py,
test_pipeline.py; data/ocr-smoke/ và data/benchmark-fixture/.
