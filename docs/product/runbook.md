# Cài, chạy, demo và phục hồi

## Native

[README gốc](../../README.md) là nguồn duy nhất cho runtime pins, setup, cấu hình, dev servers và checks. Dùng `python scripts/dev.py setup`, `models`, rồi `backend`/`frontend` ở hai terminal. Không copy chuỗi lệnh cũ từ báo cáo foundation. Backend đọc `.env` mẫu tesseract; inference không tải model hoặc fallback fixture. Chi tiết dưới đây tập trung demo/backup/triage, không định nghĩa một cách cài khác.

## Demo có thể lặp lại

Khi nghiệm thu nhiều tính năng hoặc chuẩn bị tích hợp PR, dùng [ma trận nghiệm thu](../testing/integration-acceptance.md) để chọn ca và ghi rõ phần chưa chạy. Hướng dẫn này đối chiếu `main@d6c579a` ngày 22/11/2026: app 0.6.0, SQLite schema 2, export 1.0.0. Main đã có autosave #23, session #33, PDF #27, QA kết hợp #66, verifier backup #56 và doctor fix #69. Các báo cáo cũ giữ nguyên SHA/môi trường; xem ma trận để phân biệt coverage, kết quả CI và phần còn chờ tích hợp.

1. Chọn hóa đơn, nguồn synthetic, ảnh `data/product/images/hoa_don_007.png`; xác nhận chính sách data rồi upload.
2. Đợi OCR xong; kiểm số hóa đơn 0041007, ngày 2026-10-08, đơn vị Giả Lập 107, tổng 1000000 và VND theo ảnh. Đây là dữ liệu mẫu, không hóa đơn thật.
3. Chọn trường để thấy evidence; thử xóa tên người bán, đợi trạng thái autosave đã lưu rồi reload: null phải được giữ; confirm bị chặn. Khi lỗi/conflict, đối chiếu bản máy chủ trước retry; không coi thay đổi đang pending là đã lưu.
4. Điền lại theo ảnh, đợi ACK autosave, xác nhận bản lưu và xuất JSON từ server. File có revision khớp bản persisted; chỉnh sửa bản confirmed cần CAS trạng thái/revision rõ ràng để trở lại draft.
5. Mở hai tab cùng một revision, để tab đầu lưu rồi sửa tab thứ hai: khi nhận 409, chọn đối chiếu, giữ hoặc bỏ chỉnh sửa theo nhu cầu; không tự replay write hoặc silent overwrite. Recovery nháp dừng trước đối chiếu máy chủ.
6. Chạy OCR lại, chọn lịch sử run cũ: review cũ còn nhưng chỉ đọc. Export run cũ bị từ chối.
7. Thử đơn đề nghị `data/fixtures/images/fixture_001.png` trong workspace thật. Cùng ảnh synthetic có thể được OCR thật; không đồng nghĩa dùng predictions fixture.

```powershell
uv run --project backend --locked python scripts/verify_product.py
```

Lệnh này thực sự gọi Tesseract và HTTP workflow, fail nếu không có môi trường; không skip hoặc fallback. Nó dùng DB tạm, scripted review chỉ kiểm workflow, không được báo như accuracy AI.

## PDF một trang

Trong workspace hiện hành, chọn mẫu synthetic `pipeline/tests/fixtures/pdf/hoa_don_007.pdf`, chờ OCR rồi đối chiếu các trường trên preview PNG. Tiếp tục sửa, đợi ACK autosave, xác nhận revision đã lưu và xuất JSON như với PNG. Raw PDF được giữ trong runtime; API cấp preview PNG, không phải route tải raw PDF. Xem [ADR0010](../decisions/0010-single-page-pdf.md) và [giới hạn, lỗi và ca thử PDF](../operations/single-page-pdf.md).

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

## Nghiệm thu kết hợp hiện hành

PDF + autosave + session/confirm/export và lỗi notification đã được bổ sung assertions qua
[PR #66](https://github.com/teamfuturetime/document-inteligence/pull/66), merge vào `4191dfe`.
[Báo cáo QA Windows](../reports/pdf-session-qa-2026-11-20.md) ghi môi trường và source gốc;
[CI main sau merge](https://github.com/teamfuturetime/document-inteligence/actions/runs/44762412434)
đạt trên chính merge SHA. Không gán số liệu report đó cho một lần chạy local mới.
Native helper dùng Tesseract/SQLite thật và review scripted; suite autosave riêng dùng inference
double tường minh. Các checks này kiểm workflow, không đo accuracy máy trên ảnh thật.

## Chọn runtime và profile trước vận hành

| Trạng thái | Bước tiếp theo |
|---|---|
| Runtime mới/rỗng | Chạy setup/models theo README; backend bootstrap schema 2 khi khởi động. Doctor trước đó có thể báo thiếu runtime/DB; không tạo DB bằng doctor. |
| Runtime schema 1 có dữ liệu | Dừng app/worker; chạy migration có backup vào đích mới bên dưới. Không đổi số schema bằng tay hoặc chạy bản mới để ép upgrade. |
| Runtime schema 2 | Dùng binary hiện hành; một app/worker cho mỗi DB. Backup trước thao tác quản trị offline. |
| Rollback về binary schema 1 | Restore backup schema 1 vào đích mới và dùng đúng binary cũ. Không chạy binary cũ trên DB2; giữ runtime DB2 vì thay đổi sau backup không tự đi theo rollback. |

```sh
uv run --project backend --locked python scripts/manage_auth.py --runtime runtime/app migrate --backup runtime/backups/before-schema2
```

Chỉ chạy migration trên runtime schema 1 có dữ liệu sau khi dừng app. Đích backup phải mới,
ngoài runtime nguồn. Runtime mới/rỗng không cần bước này. Mặc định `local` không đăng nhập;
để bật `session`, tạo user offline bằng prompt và cấu hình cookie/origin theo
[runbook auth](../operations/auth-ownership.md). Không có mật khẩu mặc định. Legacy documents
vẫn thuộc reserved owner `local`, không tự chuyển cho tài khoản vừa tạo. Backup DB2 chứa
password hashes/session state: giữ private, ngoài Git/web root; restore có thể phục hồi các
session chưa hết hạn, nên cân nhắc thu hồi bằng CLI offline trước khởi động.

## Kiểm tra trước và sau khởi động

`python scripts/dev.py doctor --json --runtime runtime/app` chỉ đọc runtime offline. Dừng app
trước probe; không xóa WAL/journal để ép kết quả ready. Xem [doctor](../operations/doctor.md)
cho exit codes. Parser đã nhận banner Tesseract ba/bốn nhóm số qua
[PR #69](https://github.com/teamfuturetime/document-inteligence/pull/69), giữ observed đầy đủ và
major 5. Report Windows cũ vẫn ghi lỗi parser tại source cũ; native OCR thành công không thay
kết quả doctor/runtime probes. Không bật fixture để né chẩn đoán lỗi.

Khi app đang chạy, `GET /api/v1/health` kiểm liveness; `GET /api/v1/readiness` phân biệt
HTTP 200/ready và 503/not_ready. Provider readiness là startup snapshot, không phải mỗi poll
chạy OCR; xem [readiness](../operations/readiness.md). Sau restore, chạy native workflow phù hợp
trên runtime nghiệm thu riêng rồi mở tài liệu, kiểm owner/run/revision/preview và export persisted.

## Backup và khôi phục

```powershell
uv run --project backend --locked python scripts/backup_runtime.py runtime/app runtime/backups/demo-001
uv run --project backend --locked python scripts/backup_runtime.py runtime/backups/demo-001 --verify-backup --json
uv run --project backend --locked python scripts/backup_runtime.py runtime/backups/demo-001 runtime/restored-app --restore
```

Destination phải là thư mục mới ngoài source. SQLite backup API tạo snapshot nhất quán; files nguồn/preview bất biến được copy và hash. Restore kiểm tất cả hashes trước khi copy, không đè runtime đang chạy. Trỏ DOCINTEL_RUNTIME_DIR vào thư mục vừa restore rồi khởi động app. Không có chính sách tự xóa uploads/review; người dùng bảo quản và dọn runtime sau khi backup. Không chạy cleanup lên thư mục nhóm bằng wildcard.

Source/destination có thể là đường dẫn tương đối như ví dụ trên hoặc tuyệt đối. Helper chuẩn hóa cả hai trước khi tạo paths tương đối trong manifest, gồm các alias như `..` hoặc `/var` → `/private/var` trên macOS. File trong manifest vẫn dùng paths POSIX tương đối; normalize không bỏ kiểm đích mới, containment hoặc hashes. Nếu một lần backup cũ bị lỗi giữa chừng, giữ runtime nguồn và chọn một destination mới cho lần chạy lại, không ghi đè thư mục backup dở.

Đích mới nghĩa là chưa có bất kỳ entry nào tại tên đích được truyền vào: file, thư mục, symlink hoặc Windows junction, kể cả khi target của alias đã mất. Helper kiểm leaf trước khi resolve; dangling alias bị từ chối, không tự tạo lại target. Alias ở thư mục cha vẫn dùng được khi leaf đích là tên mới. Đây là helper local, không có cơ chế khóa chống tiến trình khác sửa alias đồng thời; dừng app và giữ cây thư mục ổn định khi backup/restore.

Backup tạo snapshot trong staging private cùng filesystem, verify SQLite/assets và fsync files trước publication atomic không ghi đè. Xem [staging/cleanup và các nền hỗ trợ](../operations/staged-publication.md). Source/destination cần cây thư mục ổn định; không tự xóa staging hoặc final khi một lệnh báo lỗi, vì lost ACK có thể xảy ra sau publication thành công.

Backup do helper tạo dùng `backup.json` version **1** (số nguyên), với map `sha256` bắt buộc có `documents.sqlite3`. Các paths dùng dấu `/`, tương đối và không có `..`, drive prefix hoặc alias đường dẫn; mỗi hash là 64 ký tự hex thường. Restore từ chối manifest rỗng, thiếu database, version/cấu trúc/hash sai trước khi tạo thư mục đích. Các file được liệt kê phải tồn tại bên trong backup và khớp hash. Không sửa/xóa mục trong manifest để bỏ qua file lỗi.

Nếu gặp `Invalid backup manifest` hoặc lỗi integrity/path, giữ nguyên runtime và backup gốc, chọn lại bản backup hợp lệ. Nếu runtime nguồn vẫn hoạt động, tạo backup mới vào một đường dẫn mới bằng helper; không khởi động app trên thư mục trống và coi đó là restore thành công. Nếu đích đã tồn tại, chọn tên mới, không xóa đích cũ để ép chạy. Sau restore hợp lệ, mở tài liệu đã xác nhận, kiểm run/revision và dữ liệu JSON export; `exported_at` được tạo theo lượt tải, không dùng timestamp đó để kết luận dữ liệu persisted đã đổi.

Format backup v1 không đổi. Verifier dùng chung kiểm cấu trúc/containment/hash, SQLite integrity/foreign keys/schema1-2 và source/preview bắt buộc của từng document trước restore; xem [verify-backup](../operations/backup-verification.md) để chạy chỉ đọc. Đây không phải chữ ký xác thực hoặc chứng nhận mọi quy tắc nghiệp vụ trong JSON. Giữ mọi backup/database/auth state ngoài Git, kể cả runtime synthetic. Publication qua staging #43/#44 còn chờ PR #61/#62; lỗi ghi backup giữa chừng có thể để lại đích dở, chọn tên mới thay vì ghi đè hoặc xóa nguồn.

## Docker local

```powershell
docker compose up --build
docker compose down
```

Backend image cài Tesseract từ apt và fetch đúng model lock trong build, chạy user không phải root; named volume giữ SQLite/uploads sau `down`. Không dùng `down -v` nếu cần giữ dữ liệu. Hai cổng chỉ bind loopback. Cấu hình Docker cần được build/run trên máy có Engine; kiểm YAML không chứng minh container đã chạy. Nghiệm thu/sửa đóng gói của [#52 / PR #68](https://github.com/teamfuturetime/document-inteligence/pull/68) còn chờ tích hợp ở SHA nêu trên; chưa coi main hiện hành đã nhận các fixes của PR đó.

Nghiệm thu bằng project và volumes tạm riêng, từ root với Docker Engine đang chạy:

```powershell
uv run --project backend --locked python scripts/check_docker_smoke.py --output runtime/docker-qa/my-new-run.json
```

Chọn file output mới. Helper build hai image, dùng cổng frontend loopback được Docker cấp,
gọi API qua Nginx, kiểm PNG/JPEG native, restart cùng volume, migration DB1 và restore.
Helper đọc lại cổng sau restart, vì cổng động có thể thay đổi. Script probe được mount
read-only; user root chỉ khởi tạo quyền cho volume QA rỗng, app vẫn chạy user `docintel`.
Mỗi lượt tạo tên `docintel52-<uuid>` và tự `down --volumes --rmi local` đúng project đó,
kiểm containers/volumes đã được dọn. Backup và runtime tạm bị xóa sau kiểm thử.
Report lưu IDs, revisions, hashes và metadata OCR, còn logs có thể giữ riêng trong runtime.

Nếu host/process bị dừng cưỡng bức trước cleanup, đọc tên project từ log/report rồi kiểm
`docker ps -a --filter label=com.docker.compose.project=<project>` và
`docker volume ls --filter label=com.docker.compose.project=<project>`.
Chỉ dọn project đã xác định với đúng override configuration của lượt chạy;
giữ cấu hình tạm nếu cần điều tra, không dùng prune hoặc wildcard trên resources chung.
Xem [báo cáo Docker trên Windows](../reports/docker-smoke-2026-11-21.md) và
[evidence JSON](../evidence/docker-smoke-2026-11-21.json).

PR #68 đã bổ sung [nghiệm thu tích hợp ngày 22/11](../reports/docker-smoke-2026-11-22.md)
và [evidence mới](../evidence/docker-smoke-2026-11-22.json) trên main đã có verifier #56,
doctor #69 và frontend #63; không thay kết quả lịch sử ngày 21/11. Helper còn kiểm
snapshot lỗi đã rehash (required columns/revisions/events), current reviewed-null draft,
old runs, và restored session profile qua HTTP: owner/foreign-owner, login/CSRF và
session persistence sau restart. Passwords synthetic chỉ ở private QA volume/memory;
cookie Secure=false chỉ trong override loopback tạm, không đổi `.env` hay default auth.
Inventory trước/sau gồm containers, volumes, networks và image tags đúng project;
shared build cache được giữ. File output phải mới; không dùng CI xanh để thay lượt Compose.
Report ghi Git head tại lúc chạy và source hashes, không gán SHA commit tài liệu tạo sau đó
cho source đã thực thi. Browser trong container không nằm trong HTTP smoke này.

## Phạm vi vận hành

Mặc định local/single-user không đăng nhập. Session opt-in của #11 thêm account/document ownership
theo [hướng dẫn cấu hình và migration](../operations/auth-ownership.md); không có multi-tenant admin,
public deployment hoặc cam kết security audit. Không expose công khai. Không dùng hồ sơ thật;
chỉ synthetic/sample có quyền. Không log source text/native stderr, không gửi dữ liệu sang API AI
ngoài. Lỗi mất provider không tự đổi engine hoặc dùng fixture. Timeouts/limits không phải SLA
đã đo cho mọi máy.

Confirm đã commit có notification best-effort qua log local; không email/webhook, không đổi kết quả business khi lỗi gửi. [Cấu hình INFO, disabled mode, timeout và giới hạn delivery](../operations/confirmation-notifications.md).

Upload mặc định có tổng receive deadline 30 giây và hai slot từ lúc nhận tới khi lưu; Uvicorn trong dev/Docker giới hạn 16 connection/task. Lỗi `UPLOAD_TIMEOUT`/`UPLOAD_BUSY` có thể thử lại với cùng idempotency key. [Budget, header/stream errors và giới hạn buffer trước ASGI](../operations/upload-ingress.md) phân biệt receive timeout với deadline OCR và queue SQLite.
