# Xác minh backup offline — issue #42

Kiểm một snapshot trước phục hồi, không cần destination:

```sh
uv run --project backend --locked python scripts/backup_runtime.py runtime/backups/demo-001 --verify-backup
uv run --project backend --locked python scripts/backup_runtime.py runtime/backups/demo-001 --verify-backup --json
```

Cú pháp giống nhau trên Windows/POSIX. CLI chỉ đọc snapshot, không tạo destination, không
initialize/migrate/checkpoint DB hoặc sửa bytes nguồn. `uv run` là entry point môi trường
đã cài theo README; verifier không tự cài tool/model. Giữ snapshot offline/cây thư mục ổn định,
không chạy đồng thời với tiến trình sửa backup. WAL/journal đi kèm bị từ chối, không tự xóa.

`docintel.storage.backup.verify_backup` dùng chung cho CLI, kiểm snapshot sau khi backup tạo
xong và kiểm đầu vào restore **trước mkdir**. Kết quả nội bộ `VerifiedBackup` chứa schema version
và các entries đã kiểm để helper restore giữ containment đích và chmod/private modes hiện có.
Không đổi manifest v1, schema/application version hoặc caller migration/adoption.

## Nội dung kiểm

- Manifest v1 đúng kiểu, có database hash; paths POSIX tương đối, không escape và hash đúng.
- SQLite mở immutable/read-only/query-only, `PRAGMA integrity_check` và `foreign_key_check`;
  chỉ nhận schema1/2 và các columns cần thiết, không gọi repository initialize hoặc upgrade.
- Mỗi document có ID/hash hợp lệ, latest run thuộc đúng document; source và preview phải
  được liệt kê và có file/hash hợp lệ, source hash khớp input_sha256 trong DB.
- Schema2 có cấu trúc identity/owner/session tương ứng. Không dump account/session/document
  rows, fields, file paths hoặc exception/SQL/stderr ra report.
- Kiểm đầy đủ required columns theo migrations001/002, gồm filename/result_json và metadata
  runtime/auth. Cột bổ sung vẫn được chấp nhận; cột bắt buộc thiếu trả SNAPSHOT_UNREADABLE.
- Mỗi succeeded run phải có review revision; mọi event phải thuộc cùng run/document và
  revision khác null phải tồn tại trong run đó. Vi phạm trả DATABASE_REFERENCES. Queued,
  running, failed hoặc unavailable run hợp lệ có thể chưa có revision.

SQLite có progress deadline10s và connect timeout1s. File hashes đọc từng chunk1MiB; tổng thời
gian phụ thuộc kích thước snapshot. Đây là verifier local/offline, không là chữ ký chống người
có quyền sửa cả DB/manifest, không chứng nhận accuracy/JSON nghiệp vụ hoặc public readiness.
Schema1 giữ nguyên schema1; bản hợp lệ có thể được restore để rollback binary cũ.

## Report và xử lý lỗi

JSON thành công: `{"report_version":1,"status":"verified","schema_version":1}` (hoặc 2),
exit0. Thất bại: `{"report_version":1,"status":"error","code":"..."}`, exit2.
Sai cú pháp argparse cũng exit2; JSON report dành cho lời gọi verify hợp lệ.

| Code | Ý nghĩa/hành động |
| --- | --- |
| `MANIFEST_INVALID` | Cấu trúc/version/path/hash format sai. Giữ nguồn, chọn backup hợp lệ. |
| `FILE_INTEGRITY` | File thiếu/ngoài cây/hash sai; không sửa manifest để bỏ qua. |
| `DATABASE_NOT_OFFLINE` | Có WAL/journal; giữ nguyên snapshot, kiểm quy trình tạo backup. |
| `DATABASE_INTEGRITY` | SQLite không đạt integrity; chọn bản backup khác. |
| `DATABASE_REFERENCES` | Foreign key/latest-run/revision/event tham chiếu không hợp lệ hoặc succeeded run thiếu revision. |
| `SCHEMA_UNSUPPORTED` | Chỉ hỗ trợ schema1/2; không sửa version hoặc tự upgrade. |
| `DOCUMENT_INVALID` | ID/input hash không hợp lệ. |
| `ASSET_MISSING` | Manifest không liệt kê đủ source/preview của document. |
| `SOURCE_HASH_MISMATCH` | Hash source trong manifest khác input_sha256 trong DB. |
| `SNAPSHOT_UNREADABLE` | Không đọc/parse được snapshot/DB/schema (gồm SQL deadline). |
| `RESTORE_PATH_OUTSIDE` | Đường dẫn restore không nằm trong destination. |

Giữ backup/runtime gốc khi lỗi. Backup dùng [publication #43](staged-publication.md), restore dùng
[staging #44](staged-restore.md): chỉ công bố dữ liệu đã xác minh và fsync, không ghi đè đích.
Giữ nguyên final nếu acknowledgement bị mất sau publication; chọn tên mới sau khi kiểm trạng thái.
Không xóa source/final hoặc staging khác để ép chạy lại.

## Kiểm chứng

```sh
uv run --project backend --locked pytest backend/tests/test_backup_verify.py backend/tests/test_backup_manifest.py backend/tests/test_auth_backup.py -q
```

Regressions dùng SQLite/files thật và rehash manifest sau khi phá DB/tham chiếu/assets,
kiểm restore vẫn từ chối trước tạo destination, bytes nguồn không đổi, report không lộ dữ liệu.
Giữ bốn local/owned roundtrips absolute/relative/alias/CLI, schema1 rollback và Windows junction;
suite verifier mới chạy cả Windows job hiện có. Không đổi assertions để bỏ qua lỗi.
