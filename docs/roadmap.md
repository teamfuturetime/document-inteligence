# Roadmap và phối hợp nhóm 5 người

## Ownership

| Thành viên | Vai trò / phạm vi chính | Review chéo |
| --- | --- | --- |
| 1 | Technical Lead: kiến trúc, tích hợp, docs, CI, release/demo | Contract, evaluation, PR tích hợp |
| 2 | Frontend: `frontend/` | Contract backend, trải nghiệm demo |
| 3 | Backend: `backend/`, nguồn schema và API | Frontend API client, validation extraction |
| 4 | OCR: `pipeline/` preprocessing/OCR, mẫu synthetic | Evidence extraction, ảnh preview |
| 5 | Extraction/evaluation: module extraction, `evaluation/`, ground truth | OCR output, metrics |

Ownership là phân công công việc, không phải quyền ghi độc quyền. File contract
chung do Backend chỉnh trong một PR; các vai trò khác review trước khi dùng.
Lead điều phối README root/CI để giảm conflict. Không tạo CODEOWNERS với tên
GitHub giả; thêm sau khi có tài khoản thật của 5 thành viên.

## Phase 0 — Repository initialization

- Mục tiêu: cấu trúc và cách cộng tác thống nhất, không triển khai app.
- Tasks: overview/ignore (P0-01), kiến trúc/cấu trúc (P0-02), roadmap/backlog
  (P0-03), hướng dẫn Git và templates (P0-04).
- Owner: Lead; cả nhóm review. Dependency: kiểm tra repo và quyền Git.
- Acceptance: file có chủ đích, không secret/artifact, tài liệu liên kết được,
  commit atomic trên branch; không push/merge tự động.
- Verification: diff check, ignore rules, local links và staged diff.
- Checkpoints: `chore: initialize project overview and ignore rules`;
  `docs(architecture): define MVP and monorepo module boundaries`;
  `docs(planning): add phased roadmap and issue backlog`;
  `chore(github): add collaboration guide and issue PR templates`.

## Phase 1 — Architecture & contract

- Mục tiêu: chốt một loại hóa đơn và interface trước khi các module làm riêng.
- Tasks: scope (P1-01), schema/API/error fixtures (P1-02), sample nhỏ (P1-03).
- Owner: Lead + Backend chốt contract; OCR/Extraction tạo mẫu; Frontend review.
- Dependency: Phase 0. Sample có thể làm song song sau khi scope được chốt.
- Acceptance: trường bắt buộc/null, schema version, giới hạn file, endpoint,
  mock response và OCR output đều rõ; có mẫu synthetic đã review.
- Tests: validate fixture hợp lệ/không hợp lệ; kiểm tra ground truth bằng tay.
- Checkpoints: `docs: agree invoice MVP scope`; `feat(schema): define invoice contract`;
  `test(data): add synthetic invoice contract fixtures`.

## Phase 2 — Backend & frontend skeleton

- Mục tiêu: chạy demo xuyên frontend/API bằng mock có ghi nhãn rõ.
- Tasks: FastAPI/package (P2-01), Vite (P2-02), mock extraction (P2-03), CI (P2-04).
- Owner: Backend, Frontend làm song song; Lead đóng gói/CI/tích hợp.
- Dependency: P1-02 cho skeleton; P1-03 cho demo; CI sau khi có test thật.
- Acceptance: cài được từ checkout sạch, upload trả fixture đúng contract,
  UI hiển thị kết quả mock, lỗi mạng được báo; không tuyên bố đã có OCR.
- Tests: health/API contract pytest; UI upload states Vitest; smoke demo.
- Checkpoints: `chore(backend): configure FastAPI project`;
  `chore(frontend): initialize Vite React app`; `feat(api): add mock extraction endpoint`;
  `ci: run backend and frontend checks` (các commit/PR riêng).

## Phase 3 — OCR pipeline

- Mục tiêu: ảnh/PDF thành OCR output tiếng Việt có evidence.
- Tasks: decode/preprocessing (P3-01), adapter Tesseract (P3-02).
- Owner: OCR; Backend hỗ trợ upload validation/timeout và gọi adapter.
- Dependency: P1-02/03, Python package Phase 2. Không cần chờ UI review.
- Acceptance: PNG/JPG/PDF một trang chạy thật, tọa độ nhất quán, model/engine
  version ghi được, lỗi corrupt/đa trang/engine missing rõ ràng, file tạm cleanup.
- Tests: decode/transform unit; OCR integration trên mẫu tiếng Việt pin model;
  phân biệt test adapter fake và test engine thật trong CI.
- Checkpoints: `feat(preprocessing): normalize document pages`;
  `feat(ocr): add Vietnamese Tesseract adapter`; `test(ocr): cover real engine fixtures`.

## Phase 4 — Structured extraction

- Mục tiêu: OCR thành năm field hợp lệ, confidence/provenance minh bạch.
- Tasks: rule mapping (P4-01), validation (P4-02), real integration (P4-03).
- Owner: Extraction cho rules; Backend cho validation; Lead tích hợp.
- Dependency: rules/validation làm từ OCR fixture P1-02; integration cần P3-02.
- Acceptance: null khi missing, ngày/tiền đúng định dạng, warnings, version
  schema/rules/config; mock được chọn rõ, mode thật không fallback mock âm thầm.
- Tests: mapping nhãn tiếng Việt, missing/ambiguous fields; ngày sai, tiền âm,
  dữ liệu nhập sai kiểu; API integration thật trên mẫu.
- Checkpoints: `feat(extraction): map invoice fields from OCR`;
  `feat(validation): validate reviewed invoice values`;
  `feat(api): integrate real document pipeline`.

## Phase 5 — Review UI & export

- Mục tiêu: người dùng kiểm tra tài liệu và sửa trước khi xuất JSON.
- Tasks: preview/edit (P5-01), validation/export (P5-02).
- Owner: Frontend; Backend hỗ trợ validate. Có thể làm song song Phase 3/4
  từ fixture; tích hợp validate/export cần P4-02.
- Acceptance: preview ảnh/PDF, render Unicode, edit/reset đúng, field errors,
  trạng thái loading/error; chỉ export dữ liệu đã validate; đổi value sau validate
  phải vô hiệu hóa kết quả validate cũ. Giữ provenance AI và thay đổi review riêng.
- Tests: component interaction, stale validation response, export JSON; smoke
  ảnh/PDF và tải xuống; quản lý object URL khi đổi tài liệu.
- Checkpoints: `feat(frontend): add document preview and field review`;
  `feat(frontend): validate and export reviewed invoice JSON`.

## Phase 6 — Evaluation & testing

- Mục tiêu: đánh giá tái lập, không chỉ demo các mẫu đẹp.
- Tasks: golden dataset (P6-01), metrics/CLI (P6-02), regression (P6-03).
- Owner: Extraction; OCR tạo mẫu, Lead review phép đo và dependency locks.
- Dependency: dataset/metrics bắt đầu từ Phase 1; full run cần P4-03.
- Acceptance: fixed split, hash/ground truth/version đầy đủ; report từng field,
  macro/micro, null policy, error taxonomy; lệnh chạy tái lập trên checkout sạch.
- Tests: metric có kết quả tính tay, all-null/empty/sai value, dataset integrity,
  regression rules, hai lần chạy cùng input/config cho cùng metrics.
- Checkpoints: `test(data): add versioned golden invoice dataset`;
  `feat(evaluation): add field metrics and reproducible CLI`;
  `test(pipeline): add golden regression checks`.

## Phase 7 — Final integration

- Mục tiêu: ứng dụng/demo và tài liệu có thể bàn giao.
- Tasks: E2E/bugfix (P7-01), hướng dẫn chạy/evaluation/demo (P7-02).
- Owner: Lead điều phối; cả nhóm xử lý lỗi module của mình.
- Dependency: Phase 3–6 tích hợp, CI pass.
- Acceptance: flow upload → edit → validate → JSON cho 3 định dạng; lỗi rõ,
  không còn mock trong demo thật; report chất lượng có hạn chế; người khác làm
  theo README từ checkout sạch; một reviewer khác tác giả, CI pass trước merge.
- Tests: smoke E2E, file lỗi/oversize/missing field, rerun evaluation; fix nào
  cũng có test phù hợp với lỗi. Không đánh dấu pass nếu chưa chạy.
- Checkpoints: `test(e2e): cover document review export flow`; mỗi lỗi là một
  `fix(<module>): ...`; `docs: add reproducible development and demo guide`.

## Thứ tự triển khai song song

1. Lead bootstrap → cả nhóm review/chốt scope → Backend mở PR contract.
2. Contract được merge: Frontend skeleton/UI mock; Backend API mock; OCR
   preprocessing/engine; Extraction rule từ OCR fixture; Lead CI.
3. OCR và rules ổn định: Backend tích hợp pipeline thật; Frontend nối validation;
   Extraction hoàn thiện metrics; OCR mở rộng synthetic dataset.
4. Contract ổn định: Frontend export; Extraction chạy golden; Lead E2E/docs.
5. Cả nhóm review báo cáo lỗi, sửa bằng PR nhỏ, chuẩn bị demo cuối.

Trong một phase mỗi task có thể là một PR; một PR có nhiều atomic commit cùng
phạm vi. Không gom toàn bộ phase vào một commit. Backlog tại [issues.md](issues.md).
