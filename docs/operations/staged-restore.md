# Restore qua staging — issue #44

CLI backup/restore giữ nguyên cú pháp trong runbook. `restore` kiểm source bằng verifier #42
trước khi tạo staging, giữ bản bytes manifest đã dùng khi verify. Dữ liệu được copy vào payload
private cùng filesystem với đích cuối, chmod0600, kiểm lại actual copied SQLite/assets theo
manifest đã chốt. Sau đó bỏ manifest kiểm nội bộ, fsync files và dùng publication no-overwrite
của #43. Đích runtime chỉ xuất hiện hoàn chỉnh; output vẫn gồm DB/assets như trước, không thêm
backup.json, không initialize/migrate DB hoặc tự tạo tài khoản.

Schema1 giữ schema1 cho rollback binary cũ; schema2 giữ identity/owner, prediction/review/history,
source/preview và confirmed export. Không đổi manifest1/schema DB/app/export versions hoặc
dependency locks. Captured manifest là field nội bộ VerifiedBackup, không thêm dữ liệu vào API
hay CLI verification report. Capture metadata không thay điều kiện source/parent tree ổn định;
không coi đây là cơ chế chống mọi thay đổi filesystem đồng thời hoặc chữ ký xác thực.

## Lỗi và cleanup

Copy lỗi/thiếu file hoặc copy trả thành công nhưng bytes hỏng đều bị chặn trước publish. Lỗi
manifest write/verify/remove, fsync hoặc publish không được in Restore verified. Giữ guard
requested-leaf lstat trước resolve, destination ngoài source, containment, parent aliases,
relative paths và dangling symlink/junction. Một đích rỗng xuất hiện lúc publication vẫn được
giữ nguyên; hai restore helpers tranh một đích chỉ một người thắng.

Chỉ cleanup token staging do chính task tạo. Cleanup failure giữ root error, warning cố định,
không xóa source/final/staging khác hoặc wildcard. Nếu rename hoàn tất rồi mất acknowledgement,
giữ runtime hoàn chỉnh ở final và báo lỗi; không xóa để rollback. Khi lỗi, giữ dữ liệu và đối chiếu
nguồn/đích trước chọn tên mới. Backup chưa dùng vẫn chạy verify-backup; runtime đã restore không
có backup.json nên kiểm schema/source/owner/confirmed export theo runbook, không coi runtime
là một backup snapshot mới.

Native primitives/platform/filesystem limits và quyền xem [publication #43](staged-publication.md).
Files được fsync trước rename, không cam kết power-loss/directory-durability hoặc network FS.
Không có file đang copy tại final mà app có thể nhầm là runtime sẵn sàng.

## Kiểm chứng

```sh
uv run --project backend --locked pytest backend/tests/test_restore_publication.py backend/tests/test_auth_backup.py backend/tests/test_backup_verify.py -q
```

23 cases mới dùng SQLite/files thật và explicit fault injection: database/source/preview copy,
staged manifest write/verify/remove, fsync/publish, corrupt copied bytes, late file/empty dir/
dangling junction, barrier race, schema1/2/no initialize/private modes, cleanup/ACK, containment
và CLI success reporting. Metadata-change regression bảo đảm staged verification dùng bản
manifest đã validate trước đó. Không ghi lỗi do test double là lỗi mất dữ liệu đã xảy ra thực tế.
Giữ bốn path/CLI local/owned roundtrips, beta isolation và confirmed export trong các suites có sẵn.
Windows job chạy cả suite mới; backend/native/browser/gate vẫn giữ đủ checks.

#44 tạm dựa trên publication PR #61 (`feat/43-backup-publish`), kế thừa verifier PR #56.
PR chỉ delta restore, giữ Draft chờ nền review/tích hợp. Sau dependency vào main phải đồng bộ,
đổi base và chạy CI trên head mới trước đề xuất merge. Không nhận CI từng nhánh là nghiệm thu
của một main đã tích hợp.
