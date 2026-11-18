# PR #33 — review fix và tích hợp autosave theo identity

Đầu ra của issue [#11](https://github.com/teamfuturetime/document-inteligence/issues/11),
review [P2 login/focus](https://github.com/teamfuturetime/document-inteligence/pull/33#pullrequestreview-5950399273)
và [acceptance tích hợp của lead](https://github.com/teamfuturetime/document-inteligence/issues/11#issuecomment-6981760369).
congtri2103 thực hiện với Codex hỗ trợ; reviewer chính canhtungdz. Không tự approve/resolve review,
merge, đóng issue, bật session mặc định hoặc deploy.

## Hành vi đã sửa

Ở 8db03bc, GET session do focus dùng cùng counter với POST login: GET anonymous trong lúc
login pending làm login 200 bị bỏ qua. Hai component regressions và một native browser case
FAIL trước sửa. a6b75e4 tách observation sequence khỏi login/logout mutation; refresh bắt đầu
trước/trong mutation không áp dụng sau mutation. Signal đổi phiên thật từ tab khác/401 vẫn
invalidate mutation/response cũ. Component kiểm cả GET hoàn tất trước/sau login, GET authenticated
về trễ sau logout và login cũ sau cross-tab account change.

28171b4 merge main@bb1489a gồm autosave #23 và data QA #35, giữ source/author gốc. Giữ
expected_status bên trong SQLite transaction, trường hợp omitted/null là draft và confirmed
phải reopen tường minh; App 0.4.0 giữ toàn bộ contract 0.3.1. Generated schema/types được sinh lại,
không sửa bản sinh bằng tay. CI giữ cả autosave suite và auth suite; không bỏ gate/job.

Sau merge, sáu component regressions mới FAIL trước fix identity: recovery nhận draft local cũ,
không namespace user và không cleanup khi logout/401/change. fdffb95 thêm owner namespace cho
changed review fields, giữ key local cũ chỉ trong mode local. Session boundary cấp identity từ
server; không lấy owner từ URL/draft. Same-account reload có recovery nhưng phải đối chiếu server.
Verified logout/401/owner change và cross-tab invalidation cleanup owner đã biết; late ACK/obsolete
editor không ghi lại storage hoặc autosave. Unknown do network đóng workspace nhưng không giả là
logout, chỉ giữ recovery trong namespace cũ. Cleanup là best-effort khi browser từ chối storage;
không có fallback sang owner khác, không claim encryption hay xóa vật lý khi app không chạy.

## Kết quả trên source mới

Source candidate ac30f30; [fingerprints và summary](../evidence/auth-ownership-review-2026-11-18/verification.json).
Backend/pipeline suite chạy sau merge 28171b4, các source đó không đổi sau mốc này. Native reports
bảo toàn SHA/dirty thực tế; commits docs/evidence sau candidate không sửa source đã kiểm.

| Kiểm tra | Kết quả |
|---|---|
| Backend/pipeline pytest | 306 PASS, gồm legacy CAS/confirmed/export và auth/migration/restore |
| Frontend unit/component | 41 PASS; 11 session boundary + 21 ReviewPanel và existing App/Workspace |
| Contracts | 28 backend + frontend check PASS |
| Ruff/format | PASS, 99 Python files |
| Frontend types/lint/format/build | PASS; auth Playwright config được typecheck |
| Data/evaluator/repository/diff | PASS; frozen replay không phải inference mới |
| Native local/session | 14 / 17 PASS với Tesseract thật và models theo lock |
| Auth browser | 5 PASS, 27.5s, native UI/HTTP/SQLite/Tesseract |
| Autosave browser hiện có | 11 PASS, 42.8s, UI/HTTP/SQLite với explicit synthetic OCR double |
| Existing local invoice browser | 1 PASS, 5.7s, native OCR |

Không retry/skip browser. Auth cases gồm: held POST login + focus GET anonymous; same-account
reload recovery và logout từ tab khác; server session revoked trong lúc ACK 200 bị giữ rồi
đổi owner; foreign IDs/confirmed export/cookie isolation; shared-tab account change/401.
Revocation browser dùng logout HTTP ngoài UI rồi refresh server session, không giả là đồng hồ
TTL đã trôi qua. Actual TTL/disable/reset được backend auth tests bao phủ. Browser storage giữ
changed fields đúng owner, không password/session token/ảnh/raw OCR; artifacts trace giữ ngoài Git.

macOS arm64/Python 3.14.5, Node 24.18.0/npm 11.16.0/uv 0.12.0 khác pin CI. Local browser dùng
Chrome đã cài qua runtime override. Autosave suite dùng copy tạm chỉ thay import Playwright
thành absolute path và launch executable cho process restart; giữ mọi assertions, không sửa
source suite chính hoặc mock thêm production flow. CI chạy source suite gốc với Chromium pin.
Native evidence: [local](../evidence/auth-ownership-review-2026-11-18/local-native.json),
[session](../evidence/auth-ownership-review-2026-11-18/session-native.json). Scripted review không
đo accuracy; Windows/Docker chưa chạy local. Không thay data/gold/model/provider.

## Bàn giao

Cập nhật cùng PR #33, phản hồi inline finding và request canhtungdz re-review sau CI đúng head
mới thành công. Review Changes requested chỉ reviewer mới xác nhận xử lý xong; không dùng CI
xanh thay approval. Issue #11 giữ mở đến review/tích hợp/acceptance thực tế. Báo cáo 8db03bc là
lịch sử trước autosave, không áp dụng kết luận browser storage cũ cho source này.
