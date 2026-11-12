# ADR0010 — Opt-in session identity và document ownership

Status: triển khai local theo yêu cầu người dùng ngày 13/11/2026, issue #11 / CONS-08. Base main@921541d; không đổi SQLite/FastAPI hoặc nhập app PostgreSQL/Alembic cạnh tranh. Chưa là quyết định public deployment hay cho phép truy cập dữ liệu thật.

## Identity và scope

Mặc định `local` vẫn là ứng dụng một người dùng, không được gọi đó là authenticated. Mode `session` bật tài khoản thực tạo bằng CLI quản trị, không signup/default password hoặc identity từ header client. Password dùng PBKDF2-HMAC-SHA256 600.000 iterations, salt ngẫu nhiên và constant-time compare; opaque session token 256-bit chỉ lưu digest trong SQLite. Cookie HttpOnly/SameSite=Lax, Secure mặc định; HTTP cookie chỉ được cấu hình rõ trong profile loopback. Tắt tài khoản/reset password thu hồi sessions; phiên có absolute expiry, login được giới hạn budget DB để tránh KDF không giới hạn.

Unsafe requests trong session mode kiểm synchronizer CSRF token gắn với server session và Origin/Fetch Metadata. Login dùng JSON, custom header và Origin allowlist chống login CSRF. CORS không phải authentication. Trả 401 khi thiếu/expired/revoked session; 403 khi CSRF/origin sai; 404 cho tài liệu không thuộc owner để không tiết lộ tồn tại. Không log password/cookie/CSRF hoặc source.

## Ownership và persistence

Owner được lấy từ session DB, bất biến theo request và được bind vào service riêng; không sửa shared singleton khi đổi user. Mọi đường document/list/source/review/confirm/reprocess/history/export/insights và idempotency lookup đều scope owner. Queue/worker là quyền hệ thống nội bộ, không endpoint bypass; quota upload/OCR chung vẫn là budget tài nguyên, không trả dữ liệu của người khác.

Giữ SQLite thật. Schema v2 bổ sung users/sessions và owner cho documents, unique idempotency theo (owner,key). Dữ liệu v1 thuộc owner reserved `local`, không giao cho người đăng nhập đầu tiên. DB v1 có dữ liệu phải backup + migrate bằng CLI khi server đã dừng; DB mới/rỗng có thể bootstrap v2. Từ chối schema mới hơn, migration thất bại rollback, kiểm FK trước commit. Chuyển tài liệu local sang tài khoản cần lệnh adoption riêng, backup và xác nhận owner; không endpoint đổi chủ hay admin bypass tài liệu.

Rollback về binary/schema1 phải restore backup; không reset lịch sử hoặc ép chạy bản cũ trên DB2. Backup chứa auth state và phải giữ private; restore dùng directory mới và kiểm hashes theo helper hiện có.

## Portability và lineage

Nguồn Minh Thảo `minhthao@760ccdc`: tham khảo opaque sessions/CSRF/owner enforcement, không copy PostgreSQL/Alembic model hoặc gọi VT-044 harness là auth production. Phải triage lỗi Windows-style path trên POSIX trước khi reuse storage; giữ opaque-ID storage của docintel và tests đường dẫn độc lập. Không đổi submission refs/authors.

## Kiểm chứng và giới hạn

Matrix hai tài khoản trên SQLite thật: mỗi user chỉ thấy dữ liệu của mình; direct URL/source, forged run/revision, idempotency replay và aggregate không vượt owner. Kiểm session expiry/disable/logout/rotation, CSRF/login CSRF, migration/backup/version conflict/restore, legacy adoption và local compatibility. Có UI login/logout, native/browser checks cho cả local lẫn session mode.

Đây là cơ sở cho sử dụng nhiều tài khoản trong môi trường local được kiểm chứng, không cam kết public-hardening, SSO/MFA/password reset email, distributed workers hoặc audit compliance. TLS/reverse proxy/account recovery ngoài scope cần thiết kế và kiểm chứng riêng.

Tham khảo primary sources: [OWASP Password Storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html), [Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html), [CSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html). Các lựa chọn được pin cho implementation này, không coi việc đọc guideline là security audit.
