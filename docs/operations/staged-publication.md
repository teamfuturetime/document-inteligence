# Công bố backup qua staging — issue #43

`backup_runtime.backup` ghi toàn bộ snapshot trong payload của một thư mục token private
`.docintel-staging-*` cạnh đích cuối để cùng filesystem. SQLite backup API tạo snapshot, copy
source/preview và manifest v1; verifier #42 phải đạt rồi fsync từng file trước khi publish.
Root0700 và files0600 trên POSIX; Windows dùng semantics quyền OS hiện có, không claim POSIX ACL.
Chỉ sau publication, helper mới trả thành công/CLI in Backup verified; không có final directory
chứa snapshot đang copy dở. Caller migration/adoption tiếp tục dùng cùng helper.

## Publication không ghi đè

| Nền | Primitive |
| --- | --- |
| Linux | libc renameat2 với RENAME_NOREPLACE (1), AT_FDCWD (-100) |
| macOS | libc renamex_np với RENAME_EXCL (4) |
| Windows | os.rename (từ chối đích có sẵn) |

Nguồn chuẩn: [Linux kernel flags](https://github.com/torvalds/linux/blob/master/include/uapi/linux/fs.h),
[Linux man-pages](https://man7.org/linux/man-pages/man2/renameat2.2.html),
[Apple header](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/sys/stdio.h),
[Apple exclusive rename](https://developer.apple.com/documentation/foundation/urlresourcekey/volumesupportsexclusiverenamingkey),
[Python Windows rename](https://docs.python.org/3.14/library/os.html#os.rename).
Không fallback sang rename có thể thay empty directory trên POSIX; thiếu primitive/filesystem
không hỗ trợ phải báo lỗi. Hai helpers tranh cùng đích chỉ một người publish; đích xuất hiện
trong lúc tạo/verify staging vẫn không bị ghi đè, gồm file/empty dir/dangling symlink/junction.

Guard requested leaf bằng lstat trước resolve vẫn giữ; source/destination normalized một lần,
alias ở parent dùng được với leaf mới. Helper kiểm destination ngoài source cả khi gọi trực tiếp.
Đây là helper filesystem local với cây parent/source ổn định: không chống tiến trình khác thay
alias/parent đồng thời. Không dùng chiến lược này như distributed lock hoặc bảo đảm NFS/power-loss
durability. Fsync files + atomic namespace publication không chứng nhận máy mất điện không mất dữ liệu.

## SQLite và cleanup

Với nguồn offline không có WAL, read-only immutable tránh tạo sidecars; khi có WAL, dùng SQLite
read-only backup API để giữ các commits trong WAL. Không dùng immutable để bỏ qua WAL tồn tại.
Với file DB qua symlink, kiểm sidecars cạnh cả tên được yêu cầu và file đích đã resolve;
SQLite được mở bằng đường dẫn file đích để đọc đúng WAL của file đó trên Windows/POSIX.
Nếu WAL nằm cạnh riêng tên symlink, helper từ chối và yêu cầu recovery ở đường dẫn được
yêu cầu trước backup; không đoán WAL nào là nguồn chuẩn hoặc xóa sidecars. Doctor/verifier
cũng không báo DB offline hợp lệ khi một trong hai vị trí còn WAL/journal.
Có rollback journal phải hoàn tất recovery theo quy trình vận hành trước backup; helper không
tự repair/init/migrate. Không tạo source assets directory khi DB rỗng; thiếu assets ở DB có docs
thì từ chối. Giữ schema1/2, owner/prediction/review/history/source/confirmed export.

Cleanup chỉ exact token directory task vừa tạo, không xóa source/final hoặc các staging khác.
Nếu cleanup thất bại, warning cố định và giữ nguyên lỗi gốc; giữ staging để kiểm offline, không
wildcard-delete. Sau crash có thể còn staging/empty token dir; chọn đích mới, xác minh trước thao tác.
Nếu publication thành công nhưng acknowledgement lỗi, giữ final đã verify, không rollback bằng xóa;
chạy verify-backup để xác định trạng thái. Không coi mọi lỗi publication là bằng chứng final chưa tồn tại.

## Kiểm chứng và dependency

Tests SQLite/files thật inject database/source/preview/manifest/fsync/verify/publish faults,
cleanup failure, lost ACK, late targets và hai helpers race bằng barrier có deadline. Giữ tests
absolute/relative/alias/CLI local+owned roundtrip và Windows junction; thêm publication suite vào
Windows job hiện có. Không đổi manifest1, API/contracts/versions/dependencies hoặc default auth.

#43 tạm dựa trên verifier PR #56 (`feat/42-backup-verify`), chỉ delta publication backup;
giữ Draft chờ nền review/tích hợp, rồi đổi base/sync main và chạy CI lại. Workflow thêm đúng
target branch để CI đủ sáu jobs + Product checks trên PR phụ thuộc. [Restore staging #44](staged-restore.md) tái dùng helper publication tuần tự trong nhánh phụ thuộc;
bản #43 riêng chỉ cung cấp backup publication.
