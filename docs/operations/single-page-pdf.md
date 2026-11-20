# Tải và kiểm tra PDF một trang

Chọn PDF synthetic/sample có quyền sử dụng, đúng một trang, trong workspace. Server nhận bytes gốc và kiểm nội dung. PDF được render local thành ảnh xám trên nền trắng ở 200 DPI, rồi chạy Tesseract như ảnh PNG/JPEG. Vùng OCR được đặt trên chính frame PNG trả cho trình duyệt. PDF gốc và SHA-256 được giữ nội bộ để chạy lại và truy vết.

`GET /api/v1/capabilities` trả `upload_media_types` gồm `image/png`, `image/jpeg`, `application/pdf`. `POST /api/v1/documents` nhận body raw với query `document_type`, `data_origin`, `filename` và tùy chọn `Idempotency-Key`. Ví dụ PowerShell:

```powershell
$sample = 'pipeline/tests/fixtures/pdf/hoa_don_007.pdf'
$url = 'http://127.0.0.1:8000/api/v1/documents?document_type=hoa_don&data_origin=synthetic&filename=hoa_don_007.pdf'
Invoke-RestMethod $url -Method Post -InFile $sample -ContentType 'application/pdf' -Headers @{'Idempotency-Key'='demo-pdf-007'}
```

Lệnh trên dành cho mode `local`. Khi bật `session`, dùng workspace sau đăng nhập;
client API phải giữ cookie và gửi Origin/CSRF theo [hướng dẫn session](auth-ownership.md).
Không thêm owner vào query/header hoặc dùng tài khoản mặc định. PDF dùng cùng quyền
upload/detail/preview/history/review/confirm/reprocess/export như PNG/JPEG; tài liệu khác
owner trả 404. Readiness 200/503 giữ contract của nền, không dùng liveness để kết luận
engine OCR đã sẵn sàng.

## Review, tự lưu và phục hồi

PDF dùng chung review UI và SQLite revisions với ảnh. Khi sửa, chờ trạng thái đã lưu;
không xác nhận khi còn dirty, đang lưu hoặc có lỗi. Xóa một trường là reviewed null,
không khôi phục prediction máy. Sau conflict, chọn đối chiếu để xem bản trên máy chủ
rồi chủ động giữ/bỏ chỉnh sửa. Chỉ revision đã xác nhận và còn là run hiện hành được export.

Reload có thể khôi phục changed fields theo owner/document/run/editor. Bản khôi phục
phải đối chiếu server trước khi lưu; không tự coi là dữ liệu đã commit. Logout/401/đổi
tài khoản xóa bản nháp của owner trước và bỏ qua ACK cũ, không nhận bản nháp của người
trước vào tài khoản mới. Không tự replay upload/write khi đổi phiên hoặc mất mạng.

Notification lỗi sau commit không hủy confirm/export; confirm retry không gửi thêm lần
nữa theo [ADR0009](../decisions/0009-confirmation-notifications.md). Backup/restore giữ
raw PDF, preview, prediction, owner, history và confirmed revision; theo quy trình
[runbook](../product/runbook.md), dùng đích mới ngoài runtime nguồn và bảo vệ snapshot
có auth state. Không sửa/xóa DB hoặc sidecars thủ công để bỏ qua lỗi.

| Giới hạn | Mặc định |
| --- | --- |
| Body, nhận dữ liệu, upload đồng thời | 5 MiB, 30 giây tổng, 2 upload như [ingress hiện hành](upload-ingress.md) |
| Raster PDF | 8192 pixel mỗi chiều, tối đa 16 triệu pixel qua `DOCINTEL_MAX_IMAGE_PIXELS` |
| Preview và pipeline | Preview tối đa 5 giây hoặc timeout pipeline nếu nhỏ hơn; OCR dùng deadline pipeline mặc định 30 giây |

PDF hỏng/truncated, có mã hóa (kể cả empty password) hoặc nhiều trang trả 415 với `INVALID_PDF`, `PDF_ENCRYPTED` hoặc `PDF_PAGE_COUNT`. Request content encoding khác identity trả 415 `UNSUPPORTED_CONTENT_ENCODING`. PDF vượt cap bytes hoặc kích thước trả 413. Preview vượt deadline trả 408 `PROCESSING_TIMEOUT`. Retry chọn đúng file/loại/nguồn để dùng lại cùng khóa. Khi OCR đã vào queue nhưng lỗi, thông tin nằm trong run.

Dữ liệu nghiệm thu lấy từ [fixtures synthetic](../../pipeline/tests/fixtures/pdf/README.md). Chạy:

```powershell
uv run --project backend --locked pytest pipeline/tests/test_pdf.py backend/tests/test_pdf_upload.py backend/tests/test_pdf_integration.py -q
uv run --project backend --locked python scripts/verify_product.py
uv run --project backend --locked python scripts/verify_product.py --auth-mode session --output runtime/verification/pdf-session.json
npm --prefix frontend run test:e2e
npm --prefix frontend exec -- playwright test --config frontend/playwright.auth.config.ts
```

Chạy từng browser suite tuần tự vì auth và autosave harness dùng cùng cổng loopback;
không bật reuseExistingServer để vô tình kiểm nhầm profile. Các lệnh chỉ tạo runtime,
tài khoản synthetic và artifacts tạm, không tạo người dùng trong runtime sản phẩm.

| Coverage | Điều kiện kiểm chứng |
| --- | --- |
| Pipeline/API PDF | Parser/raster thật, lỗi input/budget/deadline, retry/source/hash/PNG preview; readiness được thay bằng double trong API unit tests. |
| `test_pdf_integration.py` | HTTP/SQLite/session/PDF admission thật; inference double tường minh. Owner/CSRF/idempotency, null/revision/status CAS, sender lỗi sau commit và owned backup/restore. Không dùng để kết luận geometry hoặc accuracy OCR. |
| Native helper local/session | Tesseract/models thật; PNG/PDF/application, PDF preview/evidence frame, null/CAS, confirmed export/restart; session kiểm PDF resource isolation. |
| Native browser local | PNG và PDF upload → review/null/reload → confirm → JSON. |
| Native browser session | PDF autosave A→AB với ACK giữ lại, null/reload, HTTP409/đối chiếu, export revision; recovery/logout/late ACK không lẫn owner. Chỉ transport ACK/fault bị điều khiển, inference vẫn native. |

## Tích hợp và bàn giao

App 0.6.0 kế thừa nền main `a9692a8` (readiness 0.5.0), session, autosave CAS,
storage recovery, backup guards và Windows gates. SQLite schema2 và export1.0.0 giữ nguyên;
không có migration PDF riêng. Contracts được sinh từ backend domain.

Phần này thuộc [#25/PR #27](https://github.com/teamfuturetime/document-inteligence/pull/27),
issue cha [#6](https://github.com/teamfuturetime/document-inteligence/issues/6).
Kết quả trên nhánh PR không đồng nghĩa PDF đã vào main. Kiểm CI đúng head mới và reviewer
khác tác giả trước tích hợp; sau merge đối chiếu acceptance và cập nhật trạng thái.
QA độc lập [#53](https://github.com/teamfuturetime/document-inteligence/issues/53) vẫn do
người được giao thực hiện trên bản chung, không đóng bằng kết quả tự kiểm của tác giả PDF.
Xem [báo cáo QA trên bản tích hợp](../reports/pdf-session-qa-2026-11-20.md) để đối chiếu
các ca bổ sung, lệnh chạy và giới hạn của từng suite.

Native kiểm OCR thật với PNG, PDF và đơn đề nghị, JPEG được kiểm ở pipeline. Browser chạy riêng luồng PNG và PDF đến JSON tải về. Mẫu là scan đóng gói từ ảnh synthetic và không dùng để ước lượng chất lượng OCR tổng quát. PDF nhiều trang, form tương tác, chữ viết tay và triển khai công khai nằm ngoài phạm vi. Parser chạy trong subprocess có deadline và cap bitmap, không có giới hạn RSS cứng. Bộ render pin qua lock và dùng [license notices của wheel PDFium](https://pypdfium2-team.github.io/pypdfium2/readme.html#licensing).
