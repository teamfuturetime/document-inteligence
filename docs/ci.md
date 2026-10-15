# P2-04 — GitHub Actions checks

Workflow: `.github/workflows/ci.yml`. Đã push `chore/ci-checks` và xác minh
GitHub run trên commit `7e6c9a1e028e91cc73fcbcd144e7fc04dbb6484d`:
[run 38504082654](https://github.com/teamfuturetime/document-inteligence/actions/runs/38504082654).
`Backend checks` và `Frontend checks` cùng success, gồm install/schema/tests/
typecheck/build. Required checks/branch protection chưa được cấu hình.

## Trigger và các job độc lập

Push mọi branch và Pull Request đều chạy checks, không lọc path để tránh thiếu
required check khi chỉ đổi contract/docs. Commit mới hủy run cũ của cùng branch
hoặc PR. Không có deployment, publish, merge tự động hay thay branch protection.

| Check | Environment | Steps |
| --- | --- | --- |
| `Backend checks` | Ubuntu 24.04, Python 3.13.14, uv 0.11.25 | `uv sync --locked`, schema export check, Pytest |
| `Frontend checks` | Ubuntu 24.04, Node 26.5.0 | `npm ci` trong frontend, Vitest, build gồm TS contract drift/typecheck |
| `OCR integration` | Ubuntu 24.04, Tesseract 5.3.4-1build5, Python 3.13.14 | Model installer kiểm tra SHA-256, Pytest `--run-ocr` trên engine thật |

Các job không cần server backend/Vite đang chạy: API tests dùng TestClient,
UI tests dùng jsdom và fake fetch. `Backend checks` chạy unit tests, skip rõ
10 tests có marker `ocr_integration`; không cần engine/model/secret.
`OCR integration` cài engine với version gói Ubuntu đã pin, tải vie/eng vào
`data/models/tessdata` từ commit chính thức đã pin và xác minh hash. Job này
gọi `pytest pipeline/tests -m ocr_integration --run-ocr` cho OCR/extraction; thiếu prerequisite,
download lỗi hoặc hash sai đều fail, không skip/fallback mock.
Smoke HTTP local của P2-03 là evidence riêng, chưa phải browser E2E trong CI.
Không cần chạy sample generator hoặc tải font để dùng fixtures đã commit.

GitHub Actions được pin SHA từ repo chính thức; khi nâng action, đối chiếu tag
và review SHA thay vì sửa sang `main`. Python/Node/uv pin phiên bản đã kiểm tra
local; dependency ứng dụng vẫn theo `uv.lock`/`frontend/package-lock.json`.
Cache chỉ dùng dependencies, không cache `.venv`/`node_modules` làm source.
Checkout không persist credentials; token chỉ có `contents: read`.
Mỗi job timeout 15 phút. Step trả exit nonzero làm job fail; không có
`continue-on-error` cho test/schema/build.

## Chạy lại các lệnh trước khi push

Từ root:

```bash
uv sync --locked
uv run --locked python -m backend.export_schemas --check
uv run --locked python -m pytest -q
# OCR thật (cần Tesseract 5 trên PATH, installer cần mạng):
uv run --locked python -m document_pipeline.ocr_models --directory data/models/tessdata
uv run --locked python -m pytest pipeline/tests -m ocr_integration --run-ocr --tessdata-dir data/models/tessdata -q
```

Trong `frontend/`:

```bash
npm ci
npm test
npm run build
```

Workflow đã được lint với actionlint 1.7.11, binary/checksum từ release chính
thức. Shellcheck/pyflakes không cài ở máy local; actionlint không chạy hai
integrations đó. Các step workflow hiện chỉ là các lệnh CLI đơn giản.
Kết quả local: backend 85 tests, frontend 30 tests, schema/build/typecheck pass.
Npm cảnh báo optional `fsevents` install script trên macOS chưa được approve;
test/build vẫn pass. Không cấp quyền chạy install scripts toàn cục chỉ để xóa
cảnh báo. Các kết quả macOS là evidence local riêng; run GitHub liên kết ở trên
đã được xác minh bằng GitHub CLI trên đúng SHA.

P3-02 đã bổ sung job `OCR integration`; actionlint pass local. Bộ Python
workspace với real OCR đạt 158 tests trên Tesseract 5.5.2/macOS, schema check
và model installer pass. Linux/Tesseract 5.3.4 job mới chưa được chạy trên
GitHub; link run P2-04 phía trên không chứng minh job này đã xanh.
Model commit/hash giống nhau, engine/build/OS khác nhau có thể cho text khác;
integration tests kiểm tra nội dung/evidence, không snapshot toàn bộ OCR output.

P4-01 đã thêm 4 real-engine extraction tests và mở rộng bước OCR CI theo marker
để thu thập tự động. Tổng 225 Python tests pass local với engine thật, trong đó
10 tests mang marker integration; 9 schema và actionlint pass. GitHub/Linux
run cho các thay đổi này vẫn chưa được xác minh.

## Sau khi được phép publish

```bash
git push -u origin chore/ci-checks
```

Push sẽ publish cả frontend/mock commits kế thừa chưa có trên remote, cùng
workflow CI. Theo quy tắc của nhóm, agent không tự push hoặc merge khi chưa
được cho phép. Mở trang Actions của repository, chọn run có đúng branch và
commit SHA. Cả `Backend checks` và `Frontend checks` phải xanh; lưu link run
và SHA vào PR/evidence, không dùng kết quả run cũ để chứng minh commit mới.

Nếu dùng GitHub CLI đã đăng nhập:

```bash
gh run list --repo teamfuturetime/document-inteligence --branch chore/ci-checks --workflow ci.yml
gh run view RUN_ID --repo teamfuturetime/document-inteligence --log-failed
```

`RUN_ID` là placeholder cần thay bằng ID thật. GitHub CLI đã đăng nhập và đọc
được run trong repository; cũng có thể kiểm tra trực tiếp trên website.

## Required checks và review

Sau run đầu thành công, admin chọn `Backend checks` và `Frontend checks`
làm required status checks cho main; bật yêu cầu PR + tối thiểu một approval
khác tác giả. Đây là bước cấu hình riêng, chưa được thực hiện bởi workflow.
Giữ job names ổn định để không làm lệch tên required checks. Chỉ merge sau khi
cả hai checks và review đạt yêu cầu.

Khi job `OCR integration` có run thành công đã xác minh, đề xuất thêm nó làm
required check; workflow không tự cập nhật branch protection.

CI chưa pass: mở failed step, đọc lỗi và tạo fix nhỏ; không bỏ check hoặc dùng
force push/reset để làm trạng thái xanh. Chưa có run: kiểm tra branch đã push,
workflow được phép chạy trong repository và trạng thái GitHub Actions.

Tham khảo [setup-uv](https://github.com/astral-sh/setup-uv),
[setup-node](https://github.com/actions/setup-node),
[checkout](https://github.com/actions/checkout) và
[actionlint](https://github.com/rhysd/actionlint).
