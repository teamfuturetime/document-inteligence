# Auth/ownership acceptance — 18/11/2026

> Báo cáo lịch sử của head 8db03bc trước tích hợp autosave #23. Kết luận browser storage tại
> mốc đó không áp dụng cho bản ghép autosave. Xem [review follow-up](auth-ownership-review-2026-11-18.md)
> để biết fix login/focus, recovery theo identity và kết quả trên source mới.

Issue [#11](https://github.com/teamfuturetime/document-inteligence/issues/11), PR
[#33](https://github.com/teamfuturetime/document-inteligence/pull/33), tài khoản thực hiện
congtri2103 với Codex hỗ trợ. Đây là verification workflow synthetic/sample trên SQLite thật;
không là security audit, accuracy benchmark hoặc quyết định triển khai public.

## Source và phạm vi

Kế thừa commits local 272aff5..4e3ae86, đồng bộ main@259ea63 rồi main@fdf757c tại 2bc092f.
Main mới có #32 (restore manifest) và #30 (ops docs), đã được Trí review độc lập trước khi
người có quyền merge. Nhánh auth giữ kiểm manifest trước mkdir cùng permissions private.
Backend suite và session native dưới đây chạy lại ở 2bc092f; frontend/browser và local native
chạy trước merge backup/docs, không có thay đổi runtime frontend/pipeline/native helper do merge.
[Source fingerprints và kết quả](../evidence/auth-ownership-2026-11-18/verification.json)
giữ hashes theo từng file; native metadata giữ Git SHA/dirty thực tế, không đổi nhãn nguồn.
Commit báo cáo chỉ đổi docs/evidence, không sửa source đã kiểm chứng.

Default local giữ nguyên namespace local. Opt-in session dùng identities thực được cấp qua CLI,
opaque HttpOnly cookie, synchronizer CSRF và owner namespace. App 0.4.0, DB schema 2;
export schema 1.0.0 giữ nguyên. [ADR0011](../decisions/0011-authentication-ownership.md),
[matrix](../architecture/ownership-matrix.md) và [runbook](../operations/auth-ownership.md).

## Acceptance

| Acceptance #11 | Evidence đã kiểm |
|---|---|
| Identity/session/CSRF, migration và matrix quyền | Strict credentials, salted PBKDF2 pinned, token digest, expiry/revocation/throttle/body bounds; anonymous/cross-site API tests; UI login/logout và cross-tab isolation |
| Owner enforcement mọi resource | Hai user trên SQLite thật: list/detail/source/review/confirm/reprocess/history/export/insights, forged run/revision, owner idempotency và internal worker boundary |
| Backup/migration/version conflicts | Schema 1 có dữ liệu không auto-upgrade; backup trước migration, rollback DDL lỗi, future version bị từ chối; explicit adoption và restore giữ owner/prediction/history/confirmed export; PR #32 regressions giữ nguyên |
| Storage portability nguồn | Triage nguồn minhthao@760ccdc; giữ opaque-ID storage của docintel, kiểm Windows/POSIX traversal và symlinks, không nhập backend/PostgreSQL thứ hai |

## Kiểm tra đã chạy

| Kiểm tra | Kết quả |
|---|---|
| backend/.venv/bin/python -m pytest backend/tests pipeline/tests -q | 283 passed, 0 fail/skip; sau main #32/#30 |
| Ruff check + format --check backend scripts pipeline | PASS, 95 files |
| generate_contracts.py --check | 28 PASS |
| check_data.py | 6 fixtures + 150 independent parent samples PASS |
| evaluate_fixtures.py + check_evaluation_regression.py | PASS; frozen replay, không inference mới |
| npm contracts:check/typecheck/lint/format:check/test/build | PASS; 19 frontend tests |
| verify_product.py --auth-mode local | 14 native checks PASS |
| verify_product.py --auth-mode session | 17 native checks PASS, chạy lại sau merge |
| playwright auth config | 2 PASS trong 13.0s, không retry/skip |
| existing invoice browser test | 1 PASS trong 4.7s, không retry/skip |
| check_repository.py + git diff --check | PASS |

[Local native evidence](../evidence/auth-ownership-2026-11-18/local-native.json) và
[session native evidence](../evidence/auth-ownership-2026-11-18/session-native.json) gọi
Tesseract 5.5.2 với vie/eng đúng model lock. Script review đối chiếu giá trị synthetic đã biết,
không dùng gold làm prediction. Browser sử dụng UI, HTTP, SQLite và native pipeline thật;
identities chỉ tồn tại trong runtime tạm do test harness, không seed app bình thường.

Lệnh backend dùng dependencies từ backend/.venv theo lock, Python 3.14.5. Node 24.18.0,
npm 11.16.0 và uv 0.12.0 khác pins CI. Browser local dùng Chrome đã cài qua executable override;
CI dùng Chromium đúng Playwright pin. Local invoice chạy qua config wrapper ngoài repo giữ
webServer/test cũ; auth dùng config riêng. Một lượt auth test đầu timeout vì điền đúng giá trị
OCR không tạo edit nên nút lưu disabled; sửa thao tác đánh dấu fields reviewed trước save.
Không sửa expected/runtime để che lỗi. Windows/Docker chưa chạy local.

## Bàn giao

PR #33 giữ issue mở đến independent review, chốt phạm vi và tích hợp/acceptance thực tế.
Reviewer đề nghị canhtungdz; không coi request là đã nhận/approve. Kế hoạch #15 trước đó ghi
multi-user chờ quyết định, nên PR này đề xuất opt-in và không tự thay scope/default của nhóm.
CI đã bổ sung native session/browser auth trong các jobs hiện có, giữ Product checks đầy đủ;
đọc kết quả ở đúng head mới nhất trên PR. Không dùng kết quả head cũ để đề xuất merge.

Source lineage/source portability giữ refs bài tập gốc. Không thêm provider/model/data, thay gold,
đổi framework/DB hoặc mở quyền/deployment. UI không giữ password/token/documents trong storage;
phiên đổi gỡ workspace và chặn response/download cũ. Các chỉnh sửa chưa lưu có thể mất khi bị
thu hồi phiên, không chuyển sang người dùng khác. TLS/public hardening/account recovery và
nghiệm thu chung PDF/autosave còn ngoài scope của PR này.
