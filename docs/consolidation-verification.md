# Consolidation verification

## Baseline trước sửa production

Ngày 2026-11-12; nguồn Git nhatquang `a03ea309ada1480e537cb7de8936ad0d52d53698`, main `94c5101b94a43f1b0e2814d1cdfeee4139289673`. Worktree riêng, không copy `.env`/uploads/DB từ workspace cũ. Native data đều synthetic. Python3.14.5, Tesseract5.5.2, Pillow12.3.0, Pydantic2.13.5 trên macOS ARM64.

| Lệnh / kiểm tra | Kết quả |
|---|---|
| uv sync --project backend --locked | Cài sạch đúng backend/uv.lock; không đổi lock |
| pytest backend/tests pipeline/tests -q | 74 passed, 7.00s trên source snapshot chính xác SHA |
| ruff check / format --check | Pass, 59 files formatted |
| scripts/generate_contracts.py --check | 25 artifacts đạt |
| scripts/check_data.py | 6 fixture samples + 150 independent product parents đạt |
| scripts/fetch_ocr_models.py | vie/eng tải từ revision pin, SHA256 verified; runtime ignored |
| scripts/verify_product.py | 14 native HTTP checks đạt: upload/idempotency/OCR/evidence/draft/null/CAS409/confirm validation/export/reprocess/history/restart, cả invoice và đơn đề nghị |
| scripts/evaluate_model.py --split test --output runtime/audit/baseline-test | 30 mẫu; 176/176 present fields đúng; không đọc gold trong inference; score synthetic không đại diện ảnh thật |

[Baseline JSON](evidence/consolidation-baseline.json) lưu engine/model/config/source fingerprints và lệnh. Báo cáo gốc Windows Tesseract5.4 nằm tại evaluation/runs/2026-10-24-test-frozen; không overwrite và không coi hai engine là cùng một run.

## Checks sau consolidation

Được bổ sung sau từng phần hoàn tất; trạng thái chưa có kết quả được coi là chưa xác minh. Không mặc định remote Actions hoặc Docker đã đạt vì có YAML. Gói thao tác ghi GitHub chỉ thực hiện sau người dùng duyệt.
