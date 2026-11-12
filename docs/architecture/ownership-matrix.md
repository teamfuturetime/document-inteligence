# Matrix quyền và actor — issue #11

Theo [ADR0010](../decisions/0010-authentication-ownership.md), principal được server lấy từ session DB. Owner ID không phải query/header/body option do client chọn. `local` là actor reserved của mode không auth, không phải tài khoản có thể đăng nhập. Local mode chỉ truy cập tài liệu local, không được coi là đường tắt vào tài liệu của tài khoản khác khi đổi cấu hình.

| Resource / operation | Anonymous session mode | Chủ tài liệu | User khác | Local mode |
| --- | --- | --- | --- | --- |
| Health, capabilities, auth/session status | Public metadata | Public metadata | Public metadata | Public metadata |
| Foundation schema definitions / synthetic fixture catalog | Không có dữ liệu cá nhân; fixture vẫn explicit | Như anonymous | Như anonymous | Như cũ |
| Product document-schemas metadata | 401, cùng gate product router | Read | Read | Read |
| Upload / documents list | 401 | Tự tạo, chỉ list của mình | Tạo/list trong namespace riêng | Namespace local |
| Document detail / selected run | 401 | Read | 404 | Chỉ owner local |
| Source preview / image | 401 | Read sau owner check | 404 | Chỉ owner local |
| Save review / confirm | 401 | Write + valid CSRF, run/revision CAS | 404 kể cả biết run/revision | Chỉ owner local, semantics cũ |
| Reprocess | 401 | Write + CSRF, expected run | 404 | Chỉ owner local |
| History / persisted export | 401 | Read, export vẫn latest/confirmed/validated | 404 | Chỉ owner local |
| Insights / aggregates | 401 | Chỉ số trên tài liệu của mình | Không aggregate dữ liệu người khác | Chỉ owner local |
| Logout | CSRF/session policy rõ ràng | Thu hồi session hiện tại | Không thu hồi session người khác | Không giả tạo session |
| Tạo/disable/reset user, migrate/adopt legacy | Không HTTP endpoint | Không HTTP endpoint | Không HTTP endpoint | CLI quản trị filesystem, server dừng |

Unsafe requests của user đăng nhập vẫn 403 nếu CSRF/Origin sai. Ownership lookup và transaction revision phải được kiểm trong cùng SQL transaction; không kiểm owner bằng UI hay CORS. Không lấy run ID hợp lệ của user khác làm nguồn đọc dù document ID thuộc mình. Idempotency key chỉ unique trong owner namespace.

Worker xử lý queue và crash recovery có quyền hệ thống nội bộ qua service không scope user; HTTP không expose các phương thức đó. Giới hạn admission/queue là tài nguyên chung, không là API đếm tài liệu hay suy ra nội dung của người khác. Owner tài liệu không đổi qua HTTP. CLI adoption yêu cầu offline/backup và target user hợp lệ; tài liệu legacy không tự động thuộc người đầu tiên login.

Kiểm chứng bắt buộc trên SQLite thật bằng hai tài khoản độc lập, cả API không cookie/cookie sai/CSRF sai, direct URL và forged run/revision. 404 unauthorized phải cùng envelope với missing document; không trả raw SQL/path/password/token trong lỗi. Backup/restore phải giữ owner, run, revision, immutable prediction và source hashes.
