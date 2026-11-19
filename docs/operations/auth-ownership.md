# Tài khoản và document ownership — issue #11

Phạm vi đề xuất: session opt-in trong cùng FastAPI/SQLite/React; chỉ dữ liệu synthetic/sample,
không triển khai public. Mặc định `DOCINTEL_AUTH_MODE=local` giữ ứng dụng không đăng nhập và
namespace reserved `local`. Trong mode `session`, mỗi tài khoản chỉ đọc/sửa tài liệu của mình.
Không lấy owner từ header/query/body. [ADR0011](../decisions/0011-authentication-ownership.md)
và [matrix quyền](../architecture/ownership-matrix.md) là contract; acceptance ở
[issue #11](https://github.com/teamfuturetime/document-inteligence/issues/11).

## Bật session trên máy local

1. Dừng backend/worker bằng Ctrl+C. Giữ runtime hiện có, không xóa DB hoặc sửa schema bằng tay.
2. Nếu runtime schema 1 có tài liệu, chạy bước migration bên dưới trước. Runtime mới/rỗng tự
   bootstrap schema 2; runtime schema 1 có dữ liệu bị từ chối startup đến khi migrate có backup.
3. Tạo tài khoản bằng CLI, nhập mật khẩu hai lần tại prompt; không đưa password vào argv/env,
   issue hoặc Git. Không có tài khoản/mật khẩu mặc định hoặc endpoint đăng ký.

```sh
uv run --project backend --locked python scripts/manage_auth.py --runtime runtime/app create-user alice
uv run --project backend --locked python scripts/manage_auth.py --runtime runtime/app list-users
```

4. Đặt trong `.env` ignored, giữ provider/model/runtime đã cấu hình theo README:

```dotenv
DOCINTEL_AUTH_MODE=session
DOCINTEL_CORS_ORIGINS=["http://127.0.0.1:5173"]
# Chỉ cho profile HTTP loopback này. Mặc định Secure=true cho HTTPS.
DOCINTEL_SESSION_COOKIE_SECURE=false
```

Chạy một backend và một frontend theo README; mở đúng `http://127.0.0.1:5173` rồi chọn
**Xử lý tài liệu**. Vite proxy `/api` để cookie cùng origin với frontend; dùng cùng hostname
suốt phiên. Không đặt wildcard CORS. Cấu hình cookie không Secure bị từ chối với origin ngoài
localhost/127.0.0.1/::1. Không mở cổng public hoặc coi HTTP profile này là triển khai an toàn
qua mạng. CORS không thay authentication/CSRF. Cookies HttpOnly, SameSite=Lax, path `/api/v1`;
UI giữ user/CSRF trong memory, không ghi password/token, ảnh nguồn hoặc raw OCR vào storage.
Autosave đã tích hợp từ #23 lưu **changed review fields** trong localStorage để recovery;
session mode dùng namespace user ID + document + run + editor, không nhận draft local cũ
hoặc draft của tài khoản khác. Local mode giữ định dạng key cũ trong namespace reserved local.

## Dùng và xử lý phiên

UI đăng nhập bằng username canonical (3–32 ký tự, chữ thường/số/_/-, bắt đầu bằng chữ), password
12–128 ký tự. Cookie token opaque được giữ bởi browser; SQLite chỉ lưu token digest. Phiên
có absolute TTL (mặc định 8 giờ, cấu hình 60–86400 giây), tối đa 5 phiên gần nhất mỗi user.
Login có budget chung trong SQLite, mặc định 20 attempts/60 giây, không lách bằng đổi username.
429 có Retry-After; chờ trước khi thử lại, không tự replay writes.

| Trạng thái | Cách xử lý |
|---|---|
| 401 / hết hạn / tài khoản bị disable | UI gỡ workspace, yêu cầu đăng nhập lại; tải lại bản persisted sau đăng nhập. Chỉnh sửa chưa lưu của phiên cũ không chuyển sang user mới. |
| 403 / CSRF hoặc origin sai | Kiểm URL và session hiện hành; UI đọc lại session, không tự gửi lại write. Không tắt CSRF để sửa lỗi. |
| 404 khi mở URL tài liệu | Tài liệu không tồn tại hoặc thuộc tài khoản khác; không suy đoán ID hoặc đổi owner ở client. |
| Đổi tài khoản/đăng xuất ở tab khác | BroadcastChannel chỉ gửi tín hiệu đổi phiên, không gửi credentials/data; workspace cũ bị gỡ. Focus/pageshow/visibility cũng đối chiếu server session. |
| Có chỉnh sửa chưa lưu khi đăng xuất | Lưu nháp hoặc bỏ chỉnh sửa trước. Khi session bị thu hồi, dữ liệu chưa lưu không được mang sang account khác. |
| 409 / revision hoặc run cũ | Giữ quy trình CAS hiện có: tải bản mới, so sánh rồi thao tác; không ghi đè silent. |

Logout thành công, 401 hoặc server xác nhận đổi owner sẽ xóa các recovery keys của owner trước
trong localStorage/sessionStorage; signal đổi phiên từ tab khác cũng cleanup owner đã biết.
ACK về trễ không được ghi lại key hoặc thay draft của owner mới. Lỗi mạng khi đọc session là
trạng thái chưa biết: workspace đóng, draft chỉ giữ trong namespace cũ để cùng account có thể
đối chiếu khi kết nối trở lại. Cleanup phụ thuộc browser cho phép truy cập storage; dù storage
bị chặn, không fallback sang owner khác. Browser storage không mã hóa hoặc thay quyền OS.
Recovery 24 giờ vẫn dừng trước server comparison, không tự replay write. Trong lúc login/logout
pending, focus refresh không được hủy mutation thành công; observation cũ về trễ bị bỏ qua.

Đăng xuất thu hồi phiên hiện tại ở server và xóa cookie cùng path; reset password/disable thu hồi
mọi phiên của tài khoản. CLI quản trị chỉ chạy offline; các lệnh đều kiểm app.lock/worker.lock:

```sh
uv run --project backend --locked python scripts/manage_auth.py --runtime runtime/app reset-password alice
uv run --project backend --locked python scripts/manage_auth.py --runtime runtime/app disable-user alice
```

Không có HTTP admin bypass hoặc email password recovery; người vận hành có quyền filesystem
quản trị tài khoản. Lock bảo vệ các app/worker/CLI dùng entry point chuẩn; không thay quyền OS.

## Migration, adoption, backup và rollback

Sau khi dừng app, backup phải ở đường dẫn mới ngoài runtime nguồn:

```sh
uv run --project backend --locked python scripts/manage_auth.py --runtime runtime/app migrate --backup runtime/backups/before-schema2
```

CLI snapshot SQLite và source/preview, kiểm integrity rồi upgrade transaction sang schema 2.
Schema tương lai bị từ chối; lỗi migration rollback DDL/data, giữ backup schema 1. Format
backup.json vẫn version 1, độc lập SQLite schema version. Không lặp migration trên DB2.
Tài liệu legacy tiếp tục thuộc `local`, không tự giao cho người đầu tiên đăng nhập. Muốn chuyển
**toàn bộ** tài liệu local sang một tài khoản active, tạo account rồi chạy offline:

```sh
uv run --project backend --locked python scripts/manage_auth.py --runtime runtime/app adopt-local --owner alice --backup runtime/backups/before-adoption --confirm
```

Adoption yêu cầu backup riêng, không đổi source/predictions/run/revision/history. Không có
endpoint chuyển chủ và không dùng mode local để truy cập tài liệu của user khác.

```sh
uv run --project backend --locked python scripts/backup_runtime.py runtime/app runtime/backups/with-owners
uv run --project backend --locked python scripts/backup_runtime.py runtime/backups/with-owners runtime/restored-owners --restore
```

Chọn đích mới; kiểm confirmed state, source, owner và JSON export sau restore. Backup DB2 chứa
password hashes và session state: giữ private, không commit/upload hoặc đặt trong web root.
Restore có thể phục hồi session chưa hết hạn trong backup; reset password offline nếu cần thu hồi
các phiên đó trước khởi động. Hash manifest kiểm file được liệt kê, không là chữ ký xác thực.
Validation manifest từ [PR #32](https://github.com/teamfuturetime/document-inteligence/pull/32)
đã được merge vào main và đồng bộ vào nhánh auth; giữ cả kiểm manifest trước mkdir và permissions private.

Rollback binary schema 1 phải restore **backup schema 1** vào directory mới rồi trỏ runtime
của binary cũ vào đó. Không chạy binary cũ lên DB2 hoặc sửa số version. Thay đổi sau mốc backup
không tự có trong bản rollback; giữ runtime DB2 để xử lý riêng, không xóa dữ liệu mới.

## Kiểm chứng

```sh
uv run --project backend --locked pytest backend/tests/test_auth_api.py backend/tests/test_auth_backup.py backend/tests/test_auth_migration.py backend/tests/test_auth_cli.py -q
uv run --project backend --locked python scripts/verify_product.py --auth-mode local --output runtime/verification/local-native.json
uv run --project backend --locked python scripts/verify_product.py --auth-mode session --output runtime/verification/session-native.json
npm --prefix frontend exec -- playwright test --config frontend/playwright.auth.config.ts
```

Lệnh browser từ root dùng config path như trên; từ `frontend/` dùng `npx playwright test --config
playwright.auth.config.ts`. Cài browser đúng pin theo README. Runtime browser tạm dùng identities
synthetic riêng, HTTP loopback và Tesseract thật; không seed tài khoản vào app bình thường.
Native workflow dùng review scripted để kiểm contract/persistence, không đo accuracy.
Các ca unit dùng explicit inference/sender doubles không được coi là native benchmark.
