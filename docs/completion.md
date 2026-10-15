# Trạng thái triển khai và bàn giao — 2026-10-15

Code Phase 0–7 đã triển khai trên nhánh tích hợp cá nhân. Đây là trạng thái
implementation/verification local; Done theo quy trình nhóm còn cần reviewer
khác tác giả, review ground truth độc lập và CI GitHub trên commit mới trước
merge main. Không coi automated tests là review con người. Chưa push các nhánh
mới hoặc thay main chung.

| Phase | Đã triển khai |
| --- | --- |
| 0 | Monorepo, Git guide, roadmap, ownership, issue/PR templates |
| 1 | Invoice MVP, 9 schemas/generated TS và synthetic fixtures |
| 2 | FastAPI/React workspace, upload/mock rõ nhãn và CI |
| 3 | Bounded preprocessing, Tesseract vie+eng, pin model/provenance |
| 4 | Rules/evidence/confidence, review validation, real API/process deadline |
| 5 | Preview ảnh/PDF, edit/reset, stale validation protection, JSON download |
| 6 | 30-document frozen dataset, 18/12 split, metrics/CLI/taxonomy/regression |
| 7 | Browser E2E, integration fixes, runbook/demo và verification local |

## Kết quả đo

Golden v1 trên macOS ARM64/Tesseract 5.5.2: macro exact match dev/test/all đều
0,9667, mục tiêu ≥0,85. Test có 12 tài liệu: seller_name đúng 10/12, bốn field
còn lại đúng 12/12 (currency có ba null-null, báo riêng). Năm sai lệch trên cả
30 tài liệu là tên bên bán mất dấu ở blur/rotation. Không chỉnh rules/dataset
theo holdout để xóa lỗi; report giữ mismatch/cause chưa xác minh.

Hai lượt evaluation đủ 30 tài liệu cho JSON byte-identical, không execution
errors. Dataset nhỏ/ba template, layout tương quan format; không chứng minh
khả năng tổng quát trên hóa đơn thực.

Verification local cuối: 267 Python tests pass với real OCR, 36 Vitest tests
pass, 7 Chromium E2E tests pass; 9 schema/generated TS, typecheck/build và
actionlint pass. Browser tải JSON thật cho PNG/JPG/PDF và kiểm tra Pydantic
ReviewedExport; ca missing/invalid/oversize/mobile cũng đạt. Đã xem ảnh QA
desktop review và mobile preview, không có overflow mobile ở width 390.

Hướng dẫn [demo](final-demo.md), [phương pháp đo](evaluation.md),
[API và giới hạn](real-pipeline.md).

## Bước cần nhóm thực hiện sau local handoff

- Review độc lập ground truth, contract và PR.
- Publish khi được cho phép, kiểm tra CI đúng SHA và khác biệt Linux.
- Admin cấu hình branch protection/required checks theo quyết định nhóm.
- Hosting/deployment và mở rộng layout/chất lượng là phạm vi tiếp theo.
