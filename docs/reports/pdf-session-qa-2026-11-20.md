# Nghiệm thu PDF, autosave và session trên Windows

QA ngày 20/11/2026 cho [Issue #53](https://github.com/teamfuturetime/document-inteligence/issues/53),
thực hiện bằng tài khoản `tuanqtb123-creator` với Codex hỗ trợ. Baseline là main
`875ac432c3fcc0c2d4d4ee48e316b041c81f3bde`, merge commit của [PR #27](https://github.com/teamfuturetime/document-inteligence/pull/27).
Commit kiểm thử trên `test/53-combined-e2e` là `d9e322fe83ed4fe20d14eea11c7dea5181602812`.
Các thay đổi sau commit kiểm thử chỉ thêm tài liệu. Head bàn giao và CI được ghi trên PR.

Windows x64, build 26200.9711. CPython 3.14.5, uv 0.12.22, Node 24.16.0,
npm 11.13.0, Chromium Headless Shell 156.0.8078.4 theo Playwright 1.64.1.
Tesseract 5.5.0.20241111 dùng `vie`/`eng` có SHA-256 khớp lock, revision
`87416418657359cb625c412a48b6e1d6d41c29bd`. PDFium 159.0.8149.0 qua pypdfium2 5.15.2.
Đã đồng bộ dependencies với `uv sync --project backend --locked` và `npm --prefix frontend ci`.

## Coverage và kết quả

PR #27 đã kiểm parser/raster, input lỗi, preview, upload retry, owner/CSRF,
explicit null, CAS, backup và restore. Native helper đã kiểm geometry và persistence.
Browser session đã kiểm A → AB với ACK đến muộn, giữ sửa sau 409, null/reload,
và recovery rồi đổi phiên khi còn ACK. Lượt này chạy lại các suite trên main
đã tích hợp và bổ sung những assertion còn thiếu vào entry points CI đang dùng.

| Nghiệm thu #53 | Bằng chứng |
| --- | --- |
| PDF một trang và evidence | PNG preview 1200 × 1550 trùng kích thước API và frame OCR, span nằm trong raster. Bytes PDF trong runtime trùng mẫu gốc, SHA-256 trùng metadata OCR và document. |
| Autosave và revision | Browser giữ AB khi ACK A tới muộn, null vẫn trống sau reload, 409 cho phép giữ hoặc bỏ chỉnh sửa sau đối chiếu. Kiểm revision trên server sau cả hai lựa chọn. Bản draft chưa được export, null không qua confirm và CAS từ chối ghi đè trạng thái đã confirm. JSON tải về khớp persisted revision. |
| Session và CSRF | Hai cookie session riêng. Account B nhận 404 với detail, PNG preview, history, export, review và confirm của A khi có CSRF của B. Bỏ CSRF nhận 403. Raw PDF nằm nội bộ, API chỉ cấp PNG preview, không có route tải raw PDF. Reload cùng owner giữ draft để đối chiếu. Logout từ tab khác và ACK đến muộn không đưa draft của A sang phiên mới. |
| Notification và history | Sender quan sát revision và values đã confirmed qua kết nối SQLite mới rồi ném lỗi có chủ đích. Retry không gọi sender lần hai và chỉ có một event confirmed. Export vẫn đúng sau lỗi và sau restart. Reprocess bằng OCR thật giữ raw PDF, prediction, review và events của run cũ. Sửa, confirm và export run cũ trả `409 STALE_RUN`. |
| Regression | Browser và OCR CI hiện có tự chạy assertions tăng thêm. Inventory và Product checks giữ nguyên. Gold, model lock, contract và production code giữ nguyên. |

Native helper dùng FastAPI TestClient, SQLite và Tesseract thật. Browser dùng HTTP
loopback, SQLite và Chromium thật. Trong suite session, Playwright chỉ giữ ACK
hoặc làm lỗi vận chuyển ở các bước recovery. Lỗi notification chỉ được cài vào
sender của native helper. Suite autosave riêng và một số pytest dùng inference
double tường minh. Mọi hồ sơ/tài khoản dùng runtime tạm. Báo cáo này chỉ nghiệm thu
workflow trên tài liệu synthetic.

## Lệnh chạy và bằng chứng

| Lệnh | Windows | Evidence local |
| --- | --- | --- |
| `python scripts/dev.py doctor --json` | FAIL chẩn đoán Tesseract, xem bên dưới | `runtime/issue-53/doctor.log` |
| `python scripts/dev.py check` | PASS Ruff, 414 backend/pipeline tests, 29 contracts, data, repository, frontend và evaluator | `runtime/issue-53/check.log` |
| `python scripts/dev.py frontend-check` | PASS 41 tests, contracts, typecheck, lint, format, build | `runtime/issue-53/frontend-check.log` |
| `python scripts/dev.py evaluation-check` | PASS frozen replay 30 documents và 6 fixtures | `runtime/issue-53/evaluation.log` |
| `python scripts/dev.py ocr` | PASS 20 checks native local | `runtime/verification/product-native.json` |
| `uv run --project backend --locked python scripts/verify_product.py --auth-mode session --output runtime/issue-53/native-session.json` | PASS 26 checks native session | `runtime/issue-53/native-session.json` |
| `python scripts/dev.py e2e` | PASS 2 ca PNG/PDF | `runtime/issue-53/e2e.log` |
| `npm --prefix frontend exec -- playwright test --config frontend/playwright.auth.config.ts` | PASS 7 ca session, gồm 2 PDF | `runtime/issue-53/e2e-auth.log` |
| `npm exec -- playwright test --config playwright.autosave.config.ts` từ `frontend/` | PASS 11 ca autosave | `runtime/issue-53/e2e-autosave.log` |
| Lệnh pytest tập trung bên dưới | PASS 60 ca PDF/session | `runtime/issue-53/focused.log` |

```powershell
uv run --project backend --locked pytest backend/tests/test_pdf_upload.py backend/tests/test_pdf_integration.py backend/tests/test_auth_api.py backend/tests/test_auth_backup.py pipeline/tests/test_pdf.py -q --basetemp runtime/issue-53/pytest-focused
```

SHA-256 của hai báo cáo native trên máy đã chạy.

- Local `51107e4a7ec1345dbadc319bb4059690c1a94426026c63efa47bcbb9edb3afd4`
- Session `87b4aabdff989e423f9611dffe4584fa541f517b5d60aac125cee218a4c02880`
- PDF synthetic `36639ed1d790f7b0af76ab846c147289912b60498ef2a1e7e09a89c3abddf43a`

**Giới hạn đã quan sát.** `tesseract --version` in `tesseract v5.5.0.20241111`,
trong khi parser của doctor chỉ nhận ba nhóm số theo ngay bởi khoảng trắng hoặc
kết thúc chuỗi. `python scripts/dev.py doctor --json` vì vậy trả `tool_failed`
và exit 2. Runtime được chọn riêng cho doctor còn trống, nên có `runtime_empty`.
Native OCR và browser dùng chính executable nói trên đã chạy thành công với models
đúng hash. Doctor nằm ngoài phần sửa của #53. Hai lượt pytest đồng thời có cảnh
báo ghi cache `WinError 183`, tất cả assertions vẫn thực thi. Khi phát triển test,
assertion đọc nhầm vị trí mã lỗi `STALE_RUN` đã được sửa để đọc envelope `error.code`.
Lượt chạy lại native session đã pass. Docker và kiểm thử trên dữ liệu thật không
thuộc phạm vi lượt nghiệm thu này.
