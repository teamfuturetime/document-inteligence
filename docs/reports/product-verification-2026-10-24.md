# Kiểm chứng triển khai sản phẩm trên nhatquang — 24/10/2026

## Phạm vi và trạng thái

Người dùng đã yêu cầu triển khai cả sản phẩm trên nhatquang, mở rộng khỏi phạm vi AI riêng/foundation trước đó. App local 0.2.0 có luồng upload → OCR/extraction thật → SQLite prediction/review → confirm → backend export; hóa đơn 5 trường và đơn đề nghị 7 trường. Có UI source evidence, conflicts/dirty-state, pagination, run history, operational stats và backup/restore.

Không commit/push/merge, reset hoặc đổi remote/quyền repo; không gửi tin nhắn/issue/assignment. Chỉ fetch refs để đối chiếu. Các thay đổi tài liệu nhóm đã có trước lượt này và file chưa theo dõi `'` được giữ. [Source lineage](../ml/source-lineage.md) ghi foundation Quang và pin models kế thừa từ Tùng; không bịa đóng góp hay reviewer approval.

## Kiểm tra đã chạy

| Kiểm tra | Lệnh hoặc cách chạy | Kết quả |
| --- | --- | --- |
| Python unit/integration logic | uv run --project backend --locked pytest backend/tests pipeline/tests -q | 72 passed; unit doubles không là model benchmark |
| Python lint/format | ruff check và ruff format --check trên backend/scripts/pipeline | Pass |
| Native workflow | uv run --project backend --locked python scripts/verify_product.py | 14 checks passed, actual Tesseract/HTTP, không skip |
| Frontend component tests | npm --prefix frontend test | 7 passed, gồm null/409/archived read-only |
| Frontend static/build | typecheck, lint, format:check, build | Pass trên Node 24.16.0; build tạo bundle thực |
| Contracts | generate_contracts.py --check và frontend contracts:check | Pass: 25 artifacts từ models/OpenAPI và TypeScript không drift |
| Python packaging | uv build backend/pipeline --wheel, kiểm nội dung wheel | Pass: docintel 0.2.0 và document-pipeline 0.1.0; migration SQL và model-lock resources có trong package |
| Dataset | check_data.py | Pass: 6 fixtures và 150 product parents/hashes/splits |
| Browser thật | In-app browser, HTTP backend cổng 8810 + Vite 5178 | Upload/OCR, xóa/lưu null, phục hồi, confirm revision 3 và download JSON thực từ server |
| SQLite lifecycle | Product tests/native workflow | Reload/restart, CAS hai clients, immutable reruns, stale export, backup/restore và worker process lock |

File export tải qua trình duyệt có document_type hoa_don, revision 3, số hóa đơn 0041007, ngày 2026-10-08, đơn vị Giả Lập 107, total_amount integer 1000000 và VND. Đây là sample tự thiết kế và scripted/manual UI review, không dùng làm accuracy AI.

Sau restart backend với policy 1.1.0, browser chạy OCR lại thành run mới, xác nhận revision 1 và download server export lần nữa. History còn run cũ/revision 3 cùng các events. [Ảnh kiểm chứng](product-review-ui-2026-10-24.png), [JSON thực đã tải](../../contracts/examples/product-export-synthetic.json).

## Evidence model và dữ liệu

150 ảnh synthetic tự thiết kế, 75 mỗi schema; 90 development / 30 validation / 30 test, parent và byte hashes độc lập; layouts vẫn có thể lặp giữa splits. Dataset card mô tả việc tạo nhãn và review chéo còn cần nhóm thực hiện, không giả danh reviewer.

- Baseline development: 90 documents, 530 present fields, 525 exact correct; còn lỗi dấu/OCR và một trường thiếu. Đây là development, không phép đo độc lập cuối.
- Confidence policy chọn trên validation baseline 30 documents: 174/176 present đúng; ngưỡng 0.5 giữ counts này và từ chối 2/2 vùng unreadable, support rất nhỏ. Profile/model config có versions/hashes; không calibrated probability.
- Sau freeze policy 1.1.0, validation 30 documents đạt 174/176 present đúng, unreadable abstain 2/2; test 30 parent documents khác đạt 176/176 present đúng, unreadable abstain 2/2. Document exact-match chỉ chấm 26 documents đủ required readable fields; bốn documents absent/unreadable bị loại có lý do. Đây là số liệu synthetic theo template biết trước, không cam kết accuracy ảnh thật.

Artifacts thực: [development baseline](../../evaluation/runs/2026-10-24-development-baseline/report.json), [validation baseline](../../evaluation/runs/2026-10-24-validation-baseline/report.json), [validation policy đã chọn](../../evaluation/runs/2026-10-24-validation-selected/report.json), [frozen test](../../evaluation/runs/2026-10-24-test-frozen/report.json), [native checks](../../evaluation/reports/product-native-2026-10-24.json). Mỗi thư mục run giữ predictions.json để đối chiếu, không chỉ một số tổng.

[Protocol](../ml/evaluation-protocol.md), [confidence selection](../../evaluation/reports/confidence-selection-2026-10-24.json), [dataset card](../../data/product/README.md). Model metadata có package/weights revision+SHA, rules/config/source hashes, Git commit/dirty, runtime và CPU. Fingerprints của mọi prediction validation-selected/test khớp source AI đã đóng băng. Git SHA là HEAD nền với dirty=true cho thay đổi chưa commit; snapshot working tree ghi ở [candidate manifest](../../evaluation/reports/product-candidate-2026-10-24.json), không bịa commit đã chứa code mới.

[Error triage](../../evaluation/reports/error-triage-2026-10-24.json) đối chiếu trực quan ảnh nguồn và OCR cho 5 lỗi trường trên 4 documents development: lỗi dấu và một label OCR sai dẫn đến abstention. Đây là phân tích của agent, chưa phải review chéo bởi thành viên nhóm; các lỗi vẫn mở và không sửa AI theo test holdout.

## Sửa lỗi nền có bằng chứng

Sáu annotation fixture đã nằm trong Git với LF, nhưng manifest trước đó lưu SHA của bytes CRLF khi generator chạy Windows. Đã xác minh lại cả sáu trường hợp; sửa hashes theo bytes Git, bump synthetic-seed-1.0.1 và bắt generator ghi newline LF. Không sửa nội dung gold, predictions hoặc PNG để làm tests xanh. Fixture evaluator tiếp tục chỉ là evaluator contract check.

## Phần chưa kiểm chứng và giới hạn

Docker CLI/Engine không có trong môi trường hiện tại: chưa build/run containers, chỉ kiểm cấu hình và nguồn. Remote GitHub Actions/PR/ruleset chưa được chạy hoặc xác nhận; không có push trong lượt này. Cần nhóm review/clean install trên máy khác, đối chiếu nhãn toàn dataset và thống nhất nền trước merge main.

Chỉ local/single-user, một worker cho mỗi DB; chưa auth, cloud, multi-tenant, PDF/multi-page/handwriting/line items hoặc VLM. Mẫu synthetic/layouts biết trước không chứng minh độ đúng ảnh thật hoặc bố cục chưa thấy. Confidence buckets/threshold có support hạn chế. Không công bố mục tiêu accuracy/SLA hoặc lợi ích thời gian người dùng chưa đo.

## Bàn giao

[Runbook](../product/runbook.md) có setup/demo, provider missing/timeout, backup/restore. [Handoff](../product/integration-handoff.md) nêu thứ tự review và port sang nền khác nếu nhóm chọn. Người dùng tự xem git diff, chọn file, commit/push nhatquang; runtime/models/DB/uploads và file `'` không thuộc commit sản phẩm.
