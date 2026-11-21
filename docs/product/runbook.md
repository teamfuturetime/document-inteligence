# Cài, chạy, demo và phục hồi

## Native

[README gốc](../../README.md) là nguồn duy nhất cho runtime pins, setup, cấu hình, dev servers và checks. Dùng `python scripts/dev.py setup`, `models`, rồi `backend`/`frontend` ở hai terminal. Không copy chuỗi lệnh cũ từ báo cáo foundation. Backend đọc `.env` mẫu tesseract; inference không tải model hoặc fallback fixture. Chi tiết dưới đây tập trung demo/backup/triage, không định nghĩa một cách cài khác.

## Demo có thể lặp lại

Khi nghiệm thu nhiều tính năng hoặc chuẩn bị tích hợp PR, dùng [ma trận nghiệm thu](../testing/integration-acceptance.md) để chọn ca và ghi rõ phần chưa chạy. Demo dưới dùng PNG và lưu nháp thủ công trên nền có notifications từ #18. Dùng mục PDF để kiểm tính năng theo ADR0010 trên nhánh có implementation #27. Ca kết hợp với autosave theo PR #23 được nghiệm thu riêng.

1. Chọn hóa đơn, nguồn synthetic, ảnh `data/product/images/hoa_don_007.png`; xác nhận chính sách data rồi upload.
2. Đợi OCR xong; kiểm số hóa đơn 0041007, ngày 2026-10-08, đơn vị Giả Lập 107, tổng 1000000 và VND theo ảnh. Đây là dữ liệu mẫu, không hóa đơn thật.
3. Chọn trường để thấy evidence; thử xóa tên người bán, lưu nháp và reload: null phải được giữ; confirm bị chặn.
4. Điền lại theo ảnh, lưu, xác nhận và xuất JSON từ server. File có revision khớp màn hình; review thay đổi sau confirm trở lại draft.
5. Mở hai tab cùng một revision, lưu tab đầu rồi lưu tab thứ hai: 409 và UI cho đối chiếu, không tự mất edits.
6. Chạy OCR lại, chọn lịch sử run cũ: review cũ còn nhưng chỉ đọc. Export run cũ bị từ chối.
7. Thử đơn đề nghị `data/fixtures/images/fixture_001.png` trong workspace thật. Cùng ảnh synthetic có thể được OCR thật; không đồng nghĩa dùng predictions fixture.

```powershell
uv run --project backend --locked python scripts/verify_product.py
```

Lệnh này thực sự gọi Tesseract và HTTP workflow, fail nếu không có môi trường; không skip hoặc fallback. Nó dùng DB tạm, scripted review chỉ kiểm workflow, không được báo như accuracy AI.

## PDF một trang

Trong workspace của bản có hỗ trợ PDF, chọn mẫu synthetic `pipeline/tests/fixtures/pdf/hoa_don_007.pdf`, chờ OCR rồi đối chiếu các trường trên preview PNG. Tiếp tục sửa và lưu nháp, xác nhận revision đã lưu và xuất JSON như với PNG. Xem [ADR0010](../decisions/0010-single-page-pdf.md) và [giới hạn, lỗi và ca thử PDF](../operations/single-page-pdf.md).

## Xác nhận và xử lý phản hồi bị mất

Sau bước xác nhận, kiểm trạng thái của bản lưu và revision trước khi tải JSON. Notification chỉ là log local best-effort sau commit; không phải điều kiện để export được phép hoặc bằng chứng đã gửi email. Để quan sát log, dùng [cấu hình INFO và cách chạy backend](../operations/confirmation-notifications.md); giữ một backend/worker trên cùng DB.

| Tình huống | Cách xử lý |
|---|---|
| Confirm trả 200, export tải được nhưng không thấy INFO | Kiểm mode `log`/`disabled` và cấu hình logger theo runbook notifications. Không xác nhận lại hoặc tạo revision mới chỉ để có log. |
| Có cảnh báo `notification_delivery_failed event=document.confirmed` | Kiểm bản đã lưu và export; lỗi sender không rollback confirmation. Log không chứng minh delivery thành công; retry confirm revision đã confirmed không phát lại event. |
| Mất mạng/hủy request trong lúc confirm, chưa rõ máy chủ đã lưu chưa | Mở lại tài liệu, đối chiếu latest run, revision và trạng thái persisted. Nếu vẫn draft, kiểm tra dữ liệu/validation rồi xác nhận bản hiện hành; nếu đã confirmed, tải JSON của revision đó. Không tự tạo draft hoặc chạy OCR lại để gửi notification. |
| Confirm/export trả 409 hoặc đang xem run cũ | Tải bản mới, đối chiếu dữ liệu và revision trước thao tác tiếp. Không ghi đè chỉnh sửa đang giữ ở tab khác hoặc lặp request với revision cũ. |
| Confirm trả 422 | Sửa lỗi validation, lưu nháp rồi xác nhận revision vừa lưu. Không xem lỗi business này là lỗi delivery. |

Khi cần chẩn đoán bằng HTTP, dùng `GET /api/v1/documents/{document_id}` lấy latest run/review. Export dùng `GET /api/v1/documents/{document_id}/export` với `run_id` và `revision` của bản persisted confirmed. Kiểm giá trị và revision trong JSON tải về, không lấy draft trình duyệt thay kết quả máy chủ. Không chép source/OCR/review fields vào logs hoặc issue công khai.

Đây là cách khôi phục trạng thái business sau phản hồi không rõ ràng, không phải cơ chế replay notification. Crash giữa commit và send có thể mất event. Nhu cầu durable delivery cần thiết kế riêng theo [ADR0009](../decisions/0009-confirmation-notifications.md).

## Chuẩn bị demo PDF và autosave sau tích hợp

Trước khi đổi demo trên, kiểm PR #23/#27 đã vào main và ghi SHA ứng viên. PDF theo [ADR0010](../decisions/0010-single-page-pdf.md); dùng sample synthetic hợp lệ, kiểm preview/evidence cùng frame rồi mới sửa trường. Autosave phải có ACK thành công trước confirm/export; đang pending, lỗi mạng hoặc conflict không được coi là đã lưu. Nghiệm thu kết hợp theo ca X1 trong ma trận trên cùng SHA, bao gồm notification lỗi vẫn giữ business result. Hiện chưa có kết quả X1 trên main; các kết quả review nhánh tính năng là riêng biệt.

## Backup và khôi phục

```powershell
uv run --project backend --locked python scripts/backup_runtime.py runtime/app runtime/backups/demo-001
uv run --project backend --locked python scripts/backup_runtime.py runtime/backups/demo-001 runtime/restored-app --restore
```

Destination phải là thư mục mới ngoài source. SQLite backup API tạo snapshot nhất quán; files nguồn/preview bất biến được copy và hash. Restore kiểm source và actual copied bytes trong staging trước publication không ghi đè; xem [restore qua staging](../operations/staged-restore.md). Trỏ DOCINTEL_RUNTIME_DIR vào thư mục vừa restore rồi khởi động app. Không có chính sách tự xóa uploads/review; người dùng bảo quản và dọn runtime sau khi backup. Không chạy cleanup lên thư mục nhóm bằng wildcard.

Source/destination có thể là đường dẫn tương đối như ví dụ trên hoặc tuyệt đối. Helper chuẩn hóa cả hai trước khi tạo paths tương đối trong manifest, gồm các alias như `..` hoặc `/var` → `/private/var` trên macOS. File trong manifest vẫn dùng paths POSIX tương đối; normalize không bỏ kiểm đích mới, containment hoặc hashes. Nếu một lần backup cũ bị lỗi giữa chừng, giữ runtime nguồn và chọn một destination mới cho lần chạy lại, không ghi đè thư mục backup dở.

Đích mới nghĩa là chưa có bất kỳ entry nào tại tên đích được truyền vào: file, thư mục, symlink hoặc Windows junction, kể cả khi target của alias đã mất. Helper kiểm leaf trước khi resolve; dangling alias bị từ chối, không tự tạo lại target. Alias ở thư mục cha vẫn dùng được khi leaf đích là tên mới. Đây là helper local, không có cơ chế khóa chống tiến trình khác sửa alias đồng thời; dừng app và giữ cây thư mục ổn định khi backup/restore.

Backup tạo snapshot trong staging private cùng filesystem, verify SQLite/assets và fsync files trước publication atomic không ghi đè. Xem [staging/cleanup và các nền hỗ trợ](../operations/staged-publication.md). Source/destination cần cây thư mục ổn định; không tự xóa staging hoặc final khi một lệnh báo lỗi, vì lost ACK có thể xảy ra sau publication thành công.

Backup do helper tạo dùng `backup.json` version **1** (số nguyên), với map `sha256` bắt buộc có `documents.sqlite3`. Các paths dùng dấu `/`, tương đối và không có `..`, drive prefix hoặc alias đường dẫn; mỗi hash là 64 ký tự hex thường. Restore từ chối manifest rỗng, thiếu database, version/cấu trúc/hash sai trước khi tạo thư mục đích. Các file được liệt kê phải tồn tại bên trong backup và khớp hash. Không sửa/xóa mục trong manifest để bỏ qua file lỗi.

Nếu gặp `Invalid backup manifest` hoặc lỗi integrity/path, giữ nguyên runtime và backup gốc, chọn lại bản backup hợp lệ. Nếu runtime nguồn vẫn hoạt động, tạo backup mới vào một đường dẫn mới bằng helper; không khởi động app trên thư mục trống và coi đó là restore thành công. Nếu đích đã tồn tại, chọn tên mới, không xóa đích cũ để ép chạy. Sau restore hợp lệ, mở tài liệu đã xác nhận, kiểm run/revision và dữ liệu JSON export; `exported_at` được tạo theo lượt tải, không dùng timestamp đó để kết luận dữ liệu persisted đã đổi.

Format backup v1 không đổi. Verifier dùng chung kiểm cấu trúc/containment/hash, SQLite integrity/foreign keys/schema1-2 và source/preview bắt buộc của từng document trước restore; xem [verify-backup](../operations/backup-verification.md) để chạy chỉ đọc. Đây không phải chữ ký xác thực hoặc chứng nhận mọi quy tắc nghiệp vụ trong JSON. Không đưa backup chứa dữ liệu ngoài sample/synthetic vào Git.

## Docker local

```powershell
docker compose up --build
docker compose down
```

Backend image cài Tesseract từ apt và fetch đúng model lock trong build, chạy user không phải root; named volume giữ SQLite/uploads sau `down`. Không dùng `down -v` nếu cần giữ dữ liệu. Hai cổng chỉ bind loopback. Cấu hình Docker cần được build/run trên máy có Engine; kiểm YAML không chứng minh container đã chạy.

## Phạm vi vận hành

Mặc định local/single-user không đăng nhập. Session opt-in của #11 thêm account/document ownership
theo [hướng dẫn cấu hình và migration](../operations/auth-ownership.md); không có multi-tenant admin,
public deployment hoặc cam kết security audit. Không expose công khai. Không dùng hồ sơ thật;
chỉ synthetic/sample có quyền. Không log source text/native stderr, không gửi dữ liệu sang API AI
ngoài. Lỗi mất provider không tự đổi engine hoặc dùng fixture. Timeouts/limits không phải SLA
đã đo cho mọi máy.

Confirm đã commit có notification best-effort qua log local; không email/webhook, không đổi kết quả business khi lỗi gửi. [Cấu hình INFO, disabled mode, timeout và giới hạn delivery](../operations/confirmation-notifications.md).

Upload mặc định có tổng receive deadline 30 giây và hai slot từ lúc nhận tới khi lưu; Uvicorn trong dev/Docker giới hạn 16 connection/task. Lỗi `UPLOAD_TIMEOUT`/`UPLOAD_BUSY` có thể thử lại với cùng idempotency key. [Budget, header/stream errors và giới hạn buffer trước ASGI](../operations/upload-ingress.md) phân biệt receive timeout với deadline OCR và queue SQLite.
