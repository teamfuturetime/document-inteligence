# Phạm vi harness và hướng dẫn giải thích khi vấn đáp

## Vì sao dùng harness

Tại baseline `66074f4ecc384b6006ac8b574001a0b4aced86ef`, `Document` không có
owner, `require_api_key` chỉ kiểm tra key dùng chung, còn `docs/security.md`
giao phân quyền người dùng cho gateway. Không có identity đáng tin để gắn
quyền tài liệu trong ứng dụng hiện tại. Đề bài cho phép executable harness khi
repository chưa đủ điều kiện. Thêm auth/gateway, migrations, backfill owner
và sửa mọi route/UI sẽ vượt quá vertical slice nhỏ được chọn.

## Phần thật, phần mới và dữ liệu giả lập

| Thành phần | Cách dùng trong bài | Giới hạn |
|---|---|---|
| `Document`, `Extraction` | ORM model thật của dự án, có foreign key và confirmation | Không thêm owner vào bảng production |
| `DocumentRepository` | Dùng create/get thật; test truy vấn và transaction với SQLAlchemy | Search production vẫn không được đổi để scope owner |
| `LocalStorage` | Ghi/đọc tệp thật, kiểm tra bytes và SHA-256 | Bytes fixture giả không đại diện ảnh PNG hợp lệ hoặc OCR |
| Database | SQLite file thật; session/transaction độc lập và contention thật | Không chứng minh PostgreSQL hoặc lịch xen kẽ retention/processing |
| `vt044_lifecycle` | Bảng phụ mới chứa owner và tombstone, tham chiếu Document thật | Chỉ được tạo cho harness; chưa có migration/backfill production |
| Identity | Token demo ánh xạ user ở server | Không phải JWT/gateway hay cơ chế quản lý tài khoản production |
| API | FastAPI app riêng có list/read/content/extraction/delete/restore | Chưa mount vào `app.main`; API production còn ngoài phạm vi |
| Thời gian/dữ liệu | Clock cố định cho boundary tests; 200 owner/doc synthetic cho load | Không dùng dữ liệu cá nhân thực, không đo OCR hay tài liệu lớn |
| ASGI load | 200 tác vụ phát cùng lúc, 1.200 assertions qua app/DB/storage | Không có socket/mạng; HTTP runs có lỗi vẫn được giữ riêng |

## Các điểm cần tự giải thích được

1. Vì sao có shared API key vẫn không phân biệt được chủ sở hữu.
2. Vì sao vòng đời active/deleted tách khỏi `Document.status`: restore phải giữ
   được trạng thái confirmed/review và dữ liệu xác nhận cũ.
3. Vì sao UPDATE khóa owner trước và Document sau, rồi mới kiểm tra điều kiện;
   vì sao no-op UPDATE có thể lấy khóa mà không đổi status nghiệp vụ.
4. Vì sao rollback test flush SQL rồi ném lỗi, sau đó đọc bằng session mới.
5. Vì sao không chỉ kiểm tra response `deleted=true`: mutant vẫn echo target
   nhưng không lưu tombstone, nên GET sau delete phải được kiểm tra.
6. Vì sao tỷ lệ 100% line/branch của 93 statements không đóng mọi risk hệ thống.
7. Vì sao p95 nhỏ hơn 5 giây nhưng có task lỗi vẫn không được nghiệm thu HTTP.
8. Vì sao job retention hard-delete dữ liệu hết hạn khiến restore phải kiểm tra
   expiry và vẫn còn race cần tích hợp/kiểm chứng trước release.

Sinh viên đã tự xác nhận rà soát và cam kết trong cuộc hội thoại; phản hồi thực
tế được lưu ở `evidence/student-review.md`. Việc đó không thay thế team review.
