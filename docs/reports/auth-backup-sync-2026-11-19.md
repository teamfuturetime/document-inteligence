# PR #33 — tích hợp backup #38, 19/11/2026

Theo [bàn giao mới trên #11](https://github.com/teamfuturetime/document-inteligence/issues/11#issuecomment-7003478677),
congtri2103 tích hợp main@9fec214 vào cùng PR #33, có Codex hỗ trợ. Merge **10c9ab9**
không conflict, giữ commits/tác giả gốc của #38. Commit **65be5e0** bổ sung kiểm chứng
phần giao nhau backup/auth và Windows; không phải lỗi auth mới được lead tìm thấy.

## Hành vi sau tích hợp

Backup/restore chuẩn hóa source/destination và kiểm `lstat` requested leaf trước resolve:
không ghi đè entry có sẵn, kể cả dangling symlink/junction; alias ở thư mục cha vẫn dùng
được nếu leaf mới. Giữ manifest version 1, SHA256, containment và validation trước mkdir.
So với helper main, chỉ còn quyền riêng tư của auth: root mới mode 0700, database backup
và các files restore chmod 0600. Không coi helper là cơ chế khóa chống đổi alias đồng thời.

Test schema 1 → migrate schema 2 → tạo hai user → adoption tường minh → backup/restore
SQLite thật chạy qua bốn kiểu paths: absolute, relative, lexical alias `..`, relative CLI.
Mỗi ca kiểm schema 2 và owner alpha, manifest v1, quyền POSIX, prediction/review/history,
confirmed export và source giữ nguyên; beta không đọc/export được hoặc thấy document.
Schema 1 backup vẫn dùng được cho rollback. Test dùng inference double tường minh,
không phải kiểm OCR native hoặc benchmark accuracy. Các regressions alias/manifest và
bốn local-mode confirmed/export roundtrips của #38 được giữ nguyên.

Windows job hiện có thêm bước chạy test_backup_manifest.py và test_auth_backup.py:
**26 cases**, gồm junction thật qua `mklink /J`, đích dangling/parent và owned restore.
Giữ launcher setup/frontend-check, inventory sáu jobs và aggregate Product checks:
tổng **7 checks**. Quyền POSIX được kiểm trên macOS/Ubuntu, không gán nghĩa POSIX cho Windows.

Auth/session/frontend/pipeline runtime, generated contracts/types, versions và lockfiles
không đổi so với 8cee486; giữ login/focus fix, owner-scoped recovery/cleanup/late ACK,
expected_status/CAS/confirmed/export. #39 vẫn độc lập.

## Kiểm chứng local

- Sau merge: 56 backup/auth/CLI/migration/product tests PASS.
- Sau mở rộng: 26 backup manifest/owned restore cases PASS; toàn bộ **331 backend/pipeline
  tests PASS**, Ruff check/format **100 Python files PASS**.
- **scripts/dev.py frontend-check PASS**: contracts/typecheck/lint/format, **41 tests**, build.
- Generated contracts **28 PASS**, data **6 fixtures/150 parents PASS**; fixture evaluator
  contract PASS (output timestamp local không đưa vào commit); repository/diff checks PASS.
- Sau thêm Windows step: 10 tests thực thi aggregate gate PASS; repository checker PASS.

Môi trường macOS arm64, Python3.14.5, Node24.18.0/npm11.16.0; dùng backend venv và node_modules
sẵn có, khác pin CI. Không lặp native/browser local vì delta chỉ là backup helper/tests/CI;
CI đúng head mới phải chạy lại native local/session, cả invoice/auth/autosave browser suites,
Windows và Product checks. Không lấy CI 8cee486 hoặc approval 2d350af thay bản ghép này.
[Source/check fingerprints](../evidence/auth-backup-sync-2026-11-19.json) pin source tại 65be5e0;
commit report kế tiếp không đổi source đã kiểm. CI/review thực tế được bàn giao trên PR/#11.

## Bàn giao

Push cùng PR #33, xác minh đủ 7 checks success trên head mới rồi request canhtungdz re-review
normalize/leaf guards + private permissions và owner/schema/confirmed restore. Giữ #11 mở
đến review/tích hợp/acceptance; không tự approve/dismiss, merge main, đổi default auth hoặc deploy.
Báo cáo đồng bộ #37 và các reviews trước giữ làm lịch sử, không phải approval bản ghép #38.
