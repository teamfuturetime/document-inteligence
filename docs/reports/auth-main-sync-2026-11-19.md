# PR #33 — đồng bộ main sau approval, 19/11/2026

Theo [bàn giao của lead trên #11](https://github.com/teamfuturetime/document-inteligence/issues/11#issuecomment-6984575243),
congtri2103 đồng bộ main cho [PR #33](https://github.com/teamfuturetime/document-inteligence/pull/33),
có Codex hỗ trợ. Approval trước đó tại 2d350af xác nhận P2 đã resolved và owner recovery đã kiểm;
không tự coi đó là nghiệm thu phần tích hợp main mới.

## Thay đổi và nguồn

Merge main@dfbc88f (#37) vào feat/11-auth-ownership tại f5b8350, không conflict/rewrite lịch sử.
Giữ Windows launcher thực trong scripts/dev.py: shutil.which, absolute path trước đổi cwd,
list args/shell=False và subprocess exit code. Giữ test relative PATH/space và exit23 của tác giả.
Workflow/inventory có sáu product jobs gồm Windows launcher checks, gate Product checks always
đòi đủ sáu success (bảy checks kể cả gate); không skip/mask hoặc giảm gate. Giữ các steps native
local/session, browser invoice, auth và autosave.

Diff so với head đã approve chỉ gồm .github/required-checks.json, workflow, scripts/dev.py,
test_ci_gate.py, test_dev_launcher.py, README/CONTRIBUTING. Auth/backend/frontend runtime,
generated contracts và dependency lockfiles **không đổi**. Trong 161 fingerprints của báo cáo
review trước, chỉ workflow, test_ci_gate.py và scripts/dev.py đổi; các files runtime đã approve
khớp. [Source fingerprints bản ghép](../evidence/auth-main-sync-2026-11-19.json).

#38 còn mở ở lúc đồng bộ: không chép code từ PR đó vào auth, chưa claim normalization/leaf
junction acceptance. Khi #38 thực sự vào main trước auth, giữ fix đó cùng permissions private
của auth và kiểm lại phần giao nhau. #39 là dependency follow-up riêng; không đổi lockfile,
chạy audit fix hoặc coi audit snapshot của lượt review là trạng thái hiện tại.

## Kiểm chứng local

- backend/.venv/bin/python -m pytest backend/tests pipeline/tests -q: **321 PASS**.
- Ruff check/format backend scripts pipeline: PASS, **100 Python files**.
- generate_contracts.py --check: **28 PASS**; data checker **6 fixtures/150 parents PASS**.
- **scripts/dev.py frontend-check** gọi launcher thật trên macOS: contracts, types, lint,
  format, **41 frontend tests**, production build PASS. Không chỉ chạy npm scripts riêng.
- check_repository.py và git diff --check: PASS.
- Không sửa expected tests, backend/auth behavior hoặc phụ thuộc. Local Python3.14.5,
  Node24.18.0/npm11.16.0 khác pins CI. Không claim Windows thật đã chạy trên máy macOS.

Runtime/native/browser source không đổi so với 2d350af, nên không lặp bộ native/browser local
cho diff launcher/gate này. CI đúng head mới phải cung cấp Windows thật + native và các suite
browser gốc, đủ **7 checks**; không dùng 6/6 của head cũ thay kết quả mới. Kết quả remote và
review trên bản ghép được bàn giao ở PR/#11, giữ report này như source/check evidence local.

## Bàn giao

Push cùng PR #33, xác minh Product checks trên head mới và đề nghị canhtungdz kiểm phần ghép
main/gate. Không tự approve/dismiss, merge/đóng #11, đổi default session, deploy hoặc quyền/refs.
Báo cáo 18/11 và approval 2d350af giữ làm lịch sử; chưa phải approval của commit sau đồng bộ.
