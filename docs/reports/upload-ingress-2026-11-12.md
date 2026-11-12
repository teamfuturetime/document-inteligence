# Kiểm chứng upload receive/admission — issue #8

> Cập nhật theo yêu cầu chia 40 commit: nhánh hiện hành là `feat/issue-8-upload-budgets-40`. Kiểm chứng mới trên implementation `fd7413e28b4ead0964d3622716931e71a1d956cc` đạt 131 backend/pipeline tests; xem mục cuối. Bản ghi ban đầu dưới đây và các SHA cũ được giữ để bảo toàn nguồn gốc.

Nhánh `feat/issue-8-upload-budgets`, implementation commit `375e6e4ec2784de55b8890b20f0c7e97e5a41b75`, base `main@fb24bc1`. Phạm vi và cách vận hành: [upload ingress](../operations/upload-ingress.md). Báo cáo này ghi kiểm chứng local, chưa có remote CI/reviewer approval hoặc merge main.

## Thay đổi và acceptance

- Receive: cap byte trước khi nối buffer, kiểm Content-Length nếu có, deadline toàn body không reset theo chunk; malformed/mismatch/disconnect/timeout dùng safe error envelope. Không thêm document/run/event/file nếu bị guard từ chối.
- Admission: mặc định hai slot, lấy ngay không xếp hàng; giữ slot qua thread tiền xử lý/lưu, kể cả HTTP task bị hủy khi thread đang làm. Uvicorn dev/Docker có concurrency limit 16.
- Compatibility: retry cùng key/type/origin/bytes vẫn trả document cũ khi OCR queue đầy; khác nội dung vẫn 409. API version 0.2.1 và generated OpenAPI/types có thêm 400/408; product/export schema không đổi.
- Tests: 18 ca ASGI mới trong `backend/tests/test_upload_ingress.py`, cộng bộ tests hiện có. Các ca cover missing/fake/duplicate Content-Length, chunk vượt cap, đúng cap, không gửi body, trickle, disconnect, cancel lúc nhận/lưu, không chờ slot, reuse và idempotent retry khi queue đầy.

## Kết quả đã chạy

| Kiểm tra | Kết quả |
| --- | --- |
| `ruff check backend scripts pipeline` | PASS |
| `ruff format --check backend scripts pipeline` | PASS, 67 files |
| `pytest backend/tests pipeline/tests -q` | PASS, 121 tests |
| `scripts/generate_contracts.py --check` | PASS, 25 contracts |
| `scripts/check_data.py` | PASS, 6 fixture và 150 independent product parent samples |
| `scripts/check_repository.py` | PASS, 87 Markdown files và config/YAML/Action refs |
| `scripts/check_evaluation_regression.py` | PASS, replay frozen native predictions, không inference mới |
| `scripts/evaluate_fixtures.py --output runtime/checks/fixture.json` | PASS, fixture contract only |
| `python3 scripts/dev.py frontend-check` | PASS contracts/types/lint/format, 12 component tests và production build |
| `scripts/verify_product.py` | PASS, 14 native workflow checks, Tesseract vie+eng thật, cả invoice/application, restart persistence |
| `playwright test --config runtime/verification/playwright.chrome.config.mjs` | PASS, 1 E2E: native invoice upload, null/reload/edit, CAS 409, confirm/download và immutable prediction |
| `scripts/check_upload_ingress.py --output runtime/verification/issue8-http-final.json` | PASS, raw loopback HTTP trên implementation commit ở trên |

Backend commands dùng `backend/.venv/bin/python`/`ruff` trong môi trường `uv sync --project backend --locked`. macOS 13.5 arm64; Python 3.14.5; Tesseract 5.5.2 được cài riêng trong ignored `runtime/tools/tesseract/`, vie/eng được tải và xác minh đúng model lock. Lệnh native dùng `DOCINTEL_TESSERACT_EXECUTABLE` trỏ vào binary đó. Báo cáo native sau commit ở [native evidence](../evidence/upload-ingress-native-2026-11-12.json); working tree vẫn có local artefacts cũ và evidence đang chuẩn bị nên metadata `git_dirty` có thể true, không có sửa pipeline/model/gold.

Node thực tế 24.18.0/npm 11.16.0 khác pin repo 24.16.x/11.13.x; các frontend checks đều đạt nhưng chưa tái lập trên đúng Node/npm pins local. Chromium bundled của Playwright không hỗ trợ macOS 13 này; E2E dùng Chrome đã cài, version 157.0.8103.51, qua config tạm trong runtime, giữ nguyên test và config CI của repo. Docker CMD đã cập nhật nhưng chưa build/run Docker. Remote CI Ubuntu theo pins repo còn chờ push/PR; chưa push hoặc đổi trạng thái issue.

## HTTP, latency, RSS và task count

[Raw JSON](../evidence/upload-ingress-2026-11-12.json) được script sinh lúc 22:43:59 ngày 12/11/2026 (UTC+7), chứa source commit và SHA256 của code/lock/probe. Server subprocess riêng, DB tạm, loopback, cap 5.242.880 bytes, hai slot, Uvicorn limit 16. Receive timeout rút xuống 0,5 giây để thử nhanh, provider unconfigured; đây không phải OCR inference hay đo timeout mặc định 30 giây.

| Ca HTTP thật | Kết quả | Thời gian |
| --- | --- | --- |
| Content-Length > 5 MiB, chưa gửi body | 413 `FILE_TOO_LARGE` | 1,029 ms |
| Chunked body > 5 MiB | 413 `FILE_TOO_LARGE` | 7,920 ms |
| Request thứ ba khi hai upload nhỏ giọt giữ slot | 429 `UPLOAD_BUSY` | 0,672 ms |
| Upload nhỏ giọt thứ nhất | 408 `UPLOAD_TIMEOUT` | 504,424 ms |
| Upload nhỏ giọt thứ hai | 408 `UPLOAD_TIMEOUT` | 504,929 ms |
| Request hoàn chỉnh sau các ca lỗi | 503 `PROVIDER_UNAVAILABLE`, đúng cấu hình probe và chứng minh slot được dùng lại | 3,070 ms |

| Mốc sample server | RSS high-water | Asyncio tasks | Active upload slots |
| --- | --- | --- | --- |
| Idle | 57,56 MiB | 4 | 0 |
| Hai upload nhỏ giọt, sau ca body lớn | 65,41 MiB | 9 | 2 |
| Sau disconnect | 66,16 MiB | 4 | 0 |
| Cuối workload | 66,48 MiB | 4 | 0 |

Ở mọi mốc sample: zero documents và zero source/preview files. Disconnect được tạo bằng cách gửi một phần body rồi đóng socket; kiểm recovery qua metrics thay vì đòi client đã đóng phải nhận JSON. RSS là peak của riêng server process qua `resource.getrusage`, không phải current RSS, không bao gồm bộ nhớ client hoặc native OCR process. Tasks tăng trong khi giữ request và trở về mức idle sau workload. Đây là một lượt đo workload giới hạn; không suy p95/SLA, chống DoS public, trần bộ nhớ tuyệt đối hay chất lượng OCR từ số này. [Giới hạn trước ASGI và cấu hình loopback](../operations/upload-ingress.md#ingress-và-giới-hạn-bộ-nhớ).

## Nhánh 40 commit — kiểm chứng sau phân rã

Người dùng yêu cầu tổng cộng 40 commits cho issue #8. Nhánh `feat/issue-8-upload-budgets-40` được xây từ cùng `main@fb24bc1`, chia theo đặc tả, cấu hình, guards, cancellation/lifecycle, regression scenarios, HTTP probe, CI và tài liệu. Nhánh hai commit `feat/issue-8-upload-budgets` vẫn giữ nguyên ở `9d036d2`; các SHA nguồn trong evidence cũ vẫn tồn tại. Không backdate, không commit rỗng, không push/merge hoặc đổi trạng thái issue.

Mã production trong backend/src, pipeline, scripts, frontend và contracts giống implementation ban đầu. Lockfile được sinh bằng đúng uv 0.12.22, revision format 5 thay cho 3; dependency versions/hashes không đổi. Bổ sung 10 tests có giá trị riêng: 7 ca kiểm bounds cấu hình, một ca error headers/envelope/request ID, một ca preflight không đọc body và một ca shutdown chờ upload đang chạy. Tổng bộ backend/pipeline tăng từ 121 lên 131 tests.

Kiểm chứng thực sự chạy lại trên source `fd7413e28b4ead0964d3622716931e71a1d956cc` (39 commit triển khai trước commit báo cáo cuối):

| Check | Kết quả |
| --- | --- |
| Ruff lint/format | PASS, 70 Python files |
| Backend + pipeline | PASS, 131 tests |
| Generated contracts / data / frozen evaluator | PASS; evaluator là replay, không inference mới |
| Frontend contracts/types/lint/format/tests/build | PASS, 12 tests |
| Native Tesseract 5.5.2 workflow | PASS, 14 checks |
| Chrome 157 E2E invoice workflow | PASS, 1 test; vẫn dùng config runtime do macOS 13 không hỗ trợ Chromium bundled |
| Raw HTTP ingress probe | PASS, 6 response scenarios và disconnect recovery |

[HTTP evidence mới](../evidence/upload-ingress-40-2026-11-12.json) pin source SHA và bảy source hashes, gồm lock revision mới; [native evidence mới](../evidence/upload-ingress-40-native-2026-11-12.json) pin cùng implementation SHA. Chỉ commit cuối bổ sung báo cáo/evidence, không thay code sau các checks này. Giới hạn Node/npm khác pin, macOS/Chrome và Docker chưa chạy vẫn như mô tả ở bản ghi ban đầu; remote CI còn chờ push/PR.

HTTP lần mới: khai báo quá cap 1,260 ms; chunked quá cap 7,763 ms; admission busy 0,678 ms; hai request nhỏ giọt timeout lần lượt 504,553/504,794 ms với deadline thử nghiệm 500 ms. Slot-reuse probe trả đúng provider-unconfigured 503 trong 3,543 ms. Task samples đi từ 4 tới 10 rồi về 4; active slots từ 0 tới 2 rồi về 0, mọi mốc vẫn không có document/source/preview được tạo. Đây là các sample của workload cụ thể, không SLA hoặc metric OCR.

Đếm commits trên nhánh mới bằng `git rev-list --count main..HEAD`: 40 sau commit báo cáo này. Cả 40 commits có tree khác parent. Không đưa node_modules, runtime, model weights hoặc artefacts cá nhân vào lịch sử nhánh.
