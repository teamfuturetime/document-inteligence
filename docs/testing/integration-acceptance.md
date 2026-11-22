# Nghiệm thu tích hợp OCR hóa đơn

Checklist kỹ thuật cho [#54](https://github.com/teamfuturetime/document-inteligence/issues/54),
đợt triển khai [#40](https://github.com/teamfuturetime/document-inteligence/issues/40) và
điều phối [#15](https://github.com/teamfuturetime/document-inteligence/issues/15).
Giữ các mã ca U/O/R/C/N/H/B/G/P/A/X để đối chiếu lịch sử; không phải bảng chấm điểm.

Đối chiếu ngày **22/11/2026**, nền `main@d6c579a973e5de730e3fc65d5331a60b51c1cbd3`:
app **0.6.0**, SQLite **schema 2**, product/export **1.0.0**. Autosave #23, auth/ownership #33,
PDF #27, QA kết hợp #66, verifier backup #56 và doctor fix #69 đã tích hợp. Nhánh cá nhân hoặc PR còn mở
không phải nền mặc định. Tài liệu này không tạo một lượt chạy OCR/browser mới.

## Chuẩn bị một lần nghiệm thu

1. Đọc [README](../../README.md), [contracts](../../contracts/README.md) và
   [runbook](../product/runbook.md). Ghi `git rev-parse HEAD`, `git status --short`, môi trường
   và lệnh thực chạy; giữ thay đổi local, không nhận checkout bẩn là sạch.
2. Cài dependencies đúng lock/pins và kiểm models vie/eng theo README. Thiếu engine/model
   phải fail, không bật fixture thay native. Ghi engine, model/config/source hashes từ report.
3. Chỉ synthetic/sample có quyền. Dùng runtime tạm, giữ mọi DB/source/uploads/models/auth
   state/logs cá nhân ngoài Git. Helpers nghiệm thu tạo runtime riêng, không dùng DB đang demo.
4. Tách **coverage có sẵn**, **kết quả đã chạy trên SHA cụ thể** và **Pending/Blocked**.
   HTTP/inference/sender doubles không phải native OCR. Scripted review và frozen replay
   không là accuracy máy trước review; không đọc gold khi inference hoặc đổi thresholds theo test.

## Ma trận trên nền đã tích hợp

Cột coverage chỉ nơi kiểm, không khẳng định mọi ca vừa chạy local. Chọn ca theo phạm vi thay đổi;
đọc kết quả CI đúng SHA ở mục bằng chứng bên dưới. Nếu có thay đổi giao nhau sau đó, kiểm lại
trên bản tích hợp mới trước khi kết luận.

| Ca | Thao tác và kết quả mong đợi | Coverage hiện có |
|---|---|---|
| U1 — giới hạn/body hỏng | Header lặp/sai, mismatch, body vượt cap/disconnect: 400/413 đúng envelope, không document/run/event/files rác, slot được giải phóng | [Ingress](../../backend/tests/test_upload_ingress.py), [receiver](../../backend/tests/test_upload_receiver.py) |
| U2 — timeout/admission | Upload nhỏ giọt có tổng deadline; request dư nhận 429; cancellation không thả slot khi thread persistence còn chạy | Các tests U1; [HTTP loopback probe](../../scripts/check_upload_ingress.py) |
| U3 — retry sau mất response | Cùng key/input/type/origin trả cùng document/run; khác nội dung nhận 409, kể cả queue đầy | [VT-042 retry](../../backend/tests/test_async_retry_vt042.py), [product](../../backend/tests/test_product.py) |
| O1 — OCR native | PNG/JPEG/application/PDF chạy pipeline có provenance/spans; provider lỗi không fallback fixture, không bịa confidence | [Native workflow](../../scripts/verify_product.py), [pipeline](../../pipeline/tests/test_pipeline.py) |
| O2 — liveness/readiness/storage | Health báo tiến trình; readiness 200/503 cùng schema, provider là startup snapshot; lỗi persistence/cleanup không mất trạng thái upload | [Readiness](../../backend/tests/test_readiness.py), [storage failures](../../backend/tests/test_upload_storage_failures.py), [runbook](../operations/readiness.md) |
| O3 — doctor offline | Chỉ đọc DB/model/tool probes, không tạo/migrate runtime; banner Tesseract 3/4 nhóm giữ observed đầy đủ, major khác 5 bị từ chối và output redacted | [Doctor](../../backend/tests/test_doctor.py), [launcher](../../backend/tests/test_dev_launcher.py), [operations](../operations/doctor.md) |
| R1 — sửa/null/reload | Người dùng xóa trường: reviewed null được giữ sau lưu/reload, không fallback prediction; confirm thiếu trường bị chặn | Product, [ReviewPanel](../../frontend/src/features/documents/ReviewPanel.test.tsx), [browser PNG/PDF](../../frontend/e2e/invoice.spec.ts) |
| R2 — revision/status CAS | Hai client cùng revision; write stale nhận 409 và UI giữ edits để đối chiếu. Không tự mở lại confirmed nếu thiếu expected_status phù hợp | Product/ReviewPanel; [autosave browser](../../frontend/autosave-e2e/autosave.spec.ts), session browser |
| C1 — validation/export authority | Confirm invalid/null nhận 422; stale run/revision nhận 409; JSON từ persisted confirmed revision có values/types đúng | Product, native workflow, invoice/session browser |
| N1 — notification sau commit | Sender thấy SQLite đã commit; failure/timeout không rollback confirm/export. Invalid/rollback không send, retry confirmed không gửi lại | [Notification tests](../../backend/tests/test_confirmation_notifications.py) dùng sender doubles; native helper #66 cài failure có chủ đích; [delivery semantics](../operations/confirmation-notifications.md) |
| H1 — history/reprocess/restart | Prediction/review/events/raw PDF cũ còn sau restart/reprocess; run cũ chỉ đọc, write/confirm/export cũ nhận STALE_RUN | Product, native helper, [session browser](../../frontend/e2e/auth.spec.ts) |
| B1 — backup/restore | Snapshot DB/assets/auth state, hashes và private modes giữ nguyên; đích tồn tại/alias lỗi bị từ chối; export/owner sau restore đúng | [Manifest](../../backend/tests/test_backup_manifest.py), [auth backup](../../backend/tests/test_auth_backup.py), [helper](../../scripts/backup_runtime.py) |
| B2 — verifier offline | Schema1/2, required columns, integrity/FK, latest-run/revisions/events và source/preview đầy đủ; invalid snapshot bị chặn trước destination, không sửa nguồn/lộ dữ liệu | [Verifier](../../backend/tests/test_backup_verify.py), [completeness](../../backend/tests/test_backup_completeness.py), [CLI/report](../operations/backup-verification.md) |
| S1 — session/ownership/migration | Hai accounts không vượt owner; thiếu CSRF nhận 403, foreign document nhận 404; late ACK/recovery không sang owner mới; DB1 migration có backup và legacy vẫn local | [Auth API](../../backend/tests/test_auth_api.py), [migration](../../backend/tests/test_auth_migration.py), [auth CLI](../../backend/tests/test_auth_cli.py), native session và auth browser |
| G1 — data/evaluator | Manifest/splits/hashes đúng; không parent overlap; frozen replay đúng công thức và không nhận là inference mới | [Data checker](../../scripts/check_data.py), [frozen regression](../../scripts/check_evaluation_regression.py), [protocol](../ml/evaluation-protocol.md) |
| P1 — PDF hợp lệ/evidence | Một trang synthetic; input hash/raw PDF đúng; preview PNG và OCR spans cùng raster/frame; review/confirm/export đúng revision | [PDF integration](../../backend/tests/test_pdf_integration.py), [PDF pipeline](../../pipeline/tests/test_pdf.py), invoice/auth browser, native helper; [ADR0010](../decisions/0010-single-page-pdf.md) |
| P2 — PDF từ chối | Mã hóa kể cả empty password, nhiều trang/hỏng/encoded/quá budget/timeout: safe errors, không records/files rác, slot/retry hồi phục | [PDF admission](../../backend/tests/test_pdf_upload.py), PDF pipeline/integration; [limits/errors](../operations/single-page-pdf.md) |
| A1 — autosave/late ACK | Sửa A→AB trong lúc ACK A trễ; AB không bị ghi đè, null giữ đúng, trạng thái saving/saved/error phản ánh kết quả | ReviewPanel, autosave browser, auth browser; [contract](../product/autosave.md) |
| A2 — conflict/navigation/recovery | 409 cho phép giữ/bỏ edits sau đối chiếu; retry/network/unmount không replay write hoặc chuyển draft sang document/run/owner khác | ReviewPanel, autosave browser (inference double rõ ràng), auth browser (native backend với giữ ACK/lỗi vận chuyển có chủ đích) |
| X1 — PDF + autosave + confirm/export | Cùng source tích hợp: upload PDF→autosave ACK→confirm→download đúng revision; pending/error không được coi đã lưu; lỗi notification không đổi business result | Native local/session và auth browser assertions từ [#66](https://github.com/teamfuturetime/document-inteligence/pull/66); [QA Windows theo SHA gốc](../reports/pdf-session-qa-2026-11-20.md) |

N1 vẫn best-effort local log theo [ADR0009](../decisions/0009-confirmation-notifications.md),
không durable/exactly-once/email/webhook. Native helper dùng TestClient/SQLite/Tesseract thật,
không phải HTTP TCP/browser. Invoice/auth browser dùng Chromium và HTTP loopback; autosave
suite riêng dùng inference double tường minh. X1 đã có coverage và CI tích hợp; không còn
Pending chỉ vì tài liệu snapshot 17/11 từng ghi autosave/PDF là Draft.

Đối chiếu preview/spans bằng mắt vẫn cần khi nghiệm thu chất lượng UI; spans non-empty không
chứng minh geometry chính xác. Test trên sample không bao phủ mọi layout/ảnh thật hoặc mọi máy.

## Bằng chứng đã xác minh và lịch sử

| Source | Bằng chứng thực | Giới hạn |
|---|---|---|
| main `d6c579a` sau #69 | [Product CI 44975747846](https://github.com/teamfuturetime/document-inteligence/actions/runs/44975747846), completed/success 7/7 trên đúng merge SHA, gồm Windows doctor regression | Parser fix đã tích hợp; không nhận là một lượt chạy local mới của tài liệu |
| main `692a834` sau #56 | [Product CI 44974458695](https://github.com/teamfuturetime/document-inteligence/actions/runs/44974458695), completed/success 7/7, gồm backend/frontend/Windows/evaluation/native/browser và Product checks | Kết quả CI của source này; không tự gọi là lần chạy local của người đọc |
| main `4191dfe` sau #66 | [Product CI 44762412434](https://github.com/teamfuturetime/document-inteligence/actions/runs/44762412434), completed/success 7/7 với assertions X1 tăng thêm | Mốc tích hợp QA kết hợp; main mới kế thừa nhưng cần CI riêng khi thay đổi |
| Test commit `d9e322f` của #66 | [QA Windows 20/11](../reports/pdf-session-qa-2026-11-20.md): native local 20/session 26, Chromium PNG/PDF 2/session 7, autosave 11 và focused PDF/session 60 | Số từ report của tác giả, không phải số vừa chạy lại trên main hiện hành; doctor Windows lúc đó fail, Docker không thuộc lượt này |
| `921541d` và `1b067a7` | [Baseline 14/11](../reports/integration-baseline-2026-11-14.md), tài liệu checklist cũ qua #29 | Giữ nguyên báo cáo lịch sử; không đổi nhãn Pending/Pass của source cũ thành kết quả mới |

## Công việc chưa tích hợp tại mốc trên

| Phần việc | Dependency/PR | Bước tiếp theo |
|---|---|---|
| Docker Compose/persistence | #52 / [#68](https://github.com/teamfuturetime/document-inteligence/pull/68) | Tác giả có evidence Docker riêng; sửa đóng gói/smoke chưa ở main tại mốc này. Review và chạy bản tích hợp trước khi nhận main đã đạt Docker |
| Backup/restore staging | #43/#44, #61 → #62 sau #56 | Retarget/sync/CI/review riêng; verifier #56 đã merge không đồng nghĩa publication hoàn tất |
| Worker crash/restart bằng process | #47 / #59 | Merge main, giữ đủ CI gates và review bản mới. Không gọi test recovery nội bộ hiện có là toàn bộ acceptance process thật |
| Error guidance, keyboard, live readiness UI | #49/#51/#50, #63/#64/#65 | Sửa findings, đồng bộ main và nghiệm thu tích hợp; không suy backend readiness đã có UI polling mới |

Đây là trạng thái gắn SHA, có thể thay đổi sau các PR. Kiểm GitHub/main mới trước một lượt
nghiệm thu khác; không cần sửa báo cáo cũ để tạo lịch sử đẹp hơn.

## Lệnh tái chạy

Từ root, dùng setup/models/pins tại README và output path mới cho mỗi lượt:

```sh
python scripts/dev.py check
python scripts/dev.py ocr
uv run --project backend --locked python scripts/verify_product.py --auth-mode session --output runtime/verification/session-acceptance-new.json
uv run --project backend --locked python scripts/check_upload_ingress.py --output runtime/verification/ingress-acceptance-new.json
npm --prefix frontend exec -- playwright install chromium
python scripts/dev.py e2e
npm --prefix frontend exec -- playwright test --config frontend/playwright.auth.config.ts
npm --prefix frontend exec -- playwright test --config frontend/playwright.autosave.config.ts
```

Chạy các browser profiles tuần tự: auth/autosave dùng chung ports loopback, không chạy hai suite
đồng thời hoặc tái dùng server/runtime thật. Lệnh `check` đã gồm các pytest suites chính;
không bắt chạy focused tests lặp lại nếu cùng source/môi trường đã kiểm đủ. Có thể chọn
notification/verifier/auth tests trong ma trận để tái hiện finding cụ thể. CLI offline/backup/
migration và rollback theo runbook, không thực hiện trên runtime đang chạy chỉ để có test log.

## Quyết định tích hợp

Ghi SHA/dirty state, runtime/engine/model/config, lệnh/exit code, ca đạt và Pending/Blocked.
Chỉ lưu metadata kỹ thuật không nhạy cảm khi cần review. Product checks phải completed/success
đúng head mới nhất, reviewer độc lập xác nhận. Sau mỗi merge, kiểm lại main ancestry, conflicts,
CI và approval của PR tiếp theo; không dùng approval dismissed hoặc CI của base cũ.

#54 cập nhật tài liệu hiện hành, không tự đóng các task còn Pending trong bảng trên hoặc tạo
kết quả benchmark mới. Khi yêu cầu/contract đổi, sửa acceptance và tests có lý do; không làm
yếu expected assertions, đổi gold/model/config hoặc giảm gates để merge nhanh.
