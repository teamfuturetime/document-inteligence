# Baseline workflow tích hợp — 14/11/2026

Đầu ra task [#21](https://github.com/teamfuturetime/document-inteligence/issues/21), đối chiếu [ma trận nghiệm thu](../testing/integration-acceptance.md). Đây là baseline kỹ thuật cho main trước PDF/autosave/notification; không là nghiệm thu toàn bộ kế hoạch và không đo chất lượng OCR trên dữ liệu thực.

## Source và môi trường

- Main tham chiếu: `921541da51560d5d51ea68d91520bfdea18ec794` (upload budgets qua PR #16).
- Checkout chạy: `2dfe825d04e92b0984f660b8e2759a4d2d674e0c`, chỉ thêm ma trận và liên kết tài liệu. Không đổi source backend/pipeline/contracts/data so main; `git_dirty=false` trong native metadata, `git status --short` rỗng sau chạy trước khi lưu báo cáo này.
- macOS 15.8.3 ARM64, Python3.14.5, Pillow12.3.0, Pydantic2.13.5; dùng Python/dependencies environment đã cài ở workspace, `PYTHONPATH=backend/src:pipeline/src` trỏ source của worktree sạch. Không gọi đây là một lần cài dependencies sạch mới hoặc kiểm Docker/Windows.
- Tesseract5.5.2, CPU, weights vie/eng dùng từ thư mục model đã pin của workspace qua `DOCINTEL_TESSDATA_DIR`. Model revision `87416418657359cb625c412a48b6e1d6d41c29bd`; hai SHA256 được native runner kiểm và ghi trong [report](../evidence/integration-baseline-2026-11-14/native-workflow.json).
- Native workflow và ingress probe mỗi helper dùng runtime/SQLite tạm riêng; report ban đầu xuất ngoài worktree. Không dùng hoặc sao lưu DB người dùng; không commit ảnh upload, models hay exports.

## Kiểm tra đã thực sự chạy

| Lệnh (Python chạy source worktree như trên) | Kết quả | Ý nghĩa và giới hạn |
|---|---|---|
| `python -m pytest backend/tests pipeline/tests -q` | 131 passed, 7.42s | Test sản phẩm, upload lifecycle/retry, contracts/pipeline có mocks/doubles; không gọi toàn bộ suite là native OCR |
| `python scripts/check_data.py` | 6 fixture samples + 150 independent product parents pass | Kiểm tính toàn vẹn manifests; không thay cho review nhãn độc lập #5 |
| `python scripts/check_evaluation_regression.py` | Pass trên 30 frozen predictions | Replay evaluator; `new_inference=false`, không là benchmark Tesseract5.5.2 mới |
| `python scripts/verify_product.py --output <đường-dẫn-mới>` | 14 native workflow checks pass | OCR thật, async run, idempotency, evidence có spans, null/CAS/validation/export, reprocess/history/restart và hai schemas |
| `python scripts/check_upload_ingress.py --output <đường-dẫn-mới>` | 6 HTTP response checks pass; disconnect recovery pass | Provider unconfigured, 5MiB cap, 2 slots, deadline thử nghiệm0.5s, Uvicorn limit16; không là OCR hoặc SLA/load benchmark |

`source_evidence` của native helper chỉ xác nhận spans tồn tại; `two_client_conflict_409` là thao tác HTTP scripted, không chứng minh đã chạy hai tab UI. Không lấy các tên check để mở rộng kết luận ngoài những asserts thực sự có trong helper.

Native report ghi pipeline source SHA256 `8576b1df9b1d327f5119f6d8ae686920a2a7f4469363b1a73b828f5bbae33fcf`, config SHA256 `3615bd047d1f1e3897482040368f991002d12cfc9bc2e8a9591e871308d1b5ff`, rules SHA256 `10e7c040a535cbdbeac240f68a24d0f7149041619d131ec190e6a2d5937eebcd`. Scripted review trong mẫu phát triển không dùng như dự đoán máy hoặc điểm accuracy.

[Ingress report](../evidence/integration-baseline-2026-11-14/upload-ingress.json): 413 declared/stream oversize, 429 khi admission đầy, hai 408 dù có trickle chunks, rồi request hoàn chỉnh tới provider-unconfigured503. Sau disconnect và cuối lượt, active slots=0, tasks trở về4; mọi mốc đo documents/source-preview-files=0. RSS high-water là một lần đo cụ thể, không là trần bộ nhớ hay cam kết concurrency.

## Các phần còn Pending

- Browser UI/visual evidence, hai tab UI, network recovery ngoài component mocks chưa chạy lại trong baseline này. Không thay kết quả CI/browser nhánh cũ thành bằng chứng mới.
- Notification N1 chờ PR #18 review/merge; PDF P1/P2 và autosave A1/A2 chờ #6/#7. Ca X1 liên tính năng chưa chạy, không suy pass từ 14 native checks.
- Review labels/splits của người khác ở #5 vẫn pending; không tự ghi đã có người review hoặc thay gold.
- Docker, Windows, public/multi-user và model accuracy/unseen layouts ngoài phạm vi lần đo này.

Khi tính năng được tích hợp, chạy lại các ca bị ảnh hưởng trên cùng source SHA; lưu report đường dẫn mới, kiểm latest confirmed revision/export và nguồn evidence. Không sửa baseline cũ để làm như feature đã tồn tại từ trước.
