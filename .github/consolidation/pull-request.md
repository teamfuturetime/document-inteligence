Main hiện chỉ có README nên người mới không có một ứng dụng chung để chạy. PR này đưa một nền OCR hóa đơn local có persistence lên đường tích hợp: giữ nguyên ancestry nhatquang@a03ea30, thêm audit/ADR, một hướng dẫn chạy, test retry có nguồn gốc và CI/browser checks.

Phạm vi chủ dự án đã chọn: OCR hóa đơn local một người dùng. React frontend/, FastAPI docintel backend/, pipeline/, contracts từ backend domain, SQLite và một worker; không thêm framework/database/microservices mới. Đơn đề nghị sẵn có tiếp tục hoạt động. Auth, PDF, autosave, notification và các loại giấy tờ khác được giữ bằng refs/SHA và backlog port, không giả định đã tích hợp.

PR #1 (nhatquang→main) là nguồn nền. PR này giữ toàn bộ original commits; đề xuất review một PR hợp nhất và merge commit để không thay tác giả. Không đóng #1 trước khi nhóm chấp nhận đường thay thế; sau merge kiểm lại trạng thái và chỉ đóng/comment khi được duyệt. PR #2 autosave đã merge vào minhthao, chưa nằm trong nền này.

## Thay đổi

- docs/repository-audit.md, branch-inventory.md, ADR0008, consolidation-plan.md: source/ancestry/CI tại đúng SHA cho 16 nhánh; compatibility và phần chờ.
- README root + scripts/dev.py: setup/models/backend/frontend/check/ocr/e2e; guides cũ có nhãn lịch sử, không duy trì hai chuỗi lệnh cạnh tranh.
- Port nguyên test_async_retry_vt042.py từ 9a76a6e, source lineage và Co-authored-by; không nhập report cá nhân/UI cũ.
- Browser E2E native upload→OCR→null/reload/edit→CAS409→confirm→server JSON; kiểm immutable prediction.
- CI Product checks phụ thuộc backend/frontend/evaluator/native/browser, không path filters hoặc secret cho PR. Gate có test failure/skipped/cancelled/missing.
- Gói GitHub labels/milestones/issues/protection local; không tự thay quyền, merge, default branch hoặc xóa submission refs.

## Kiểm chứng local và giới hạn

Nguồn kết quả chính xác: docs/consolidation-verification.md. `python scripts/dev.py check`, `ocr`, `e2e`; clean checkout/locked install được ghi ở đó. OCR Tesseract5.5.2/macOS + pinned vie/eng, native HTTP checks và Chromium có chạy thật. Evaluator regression là replay frozen native predictions Windows5.4, không gọi đó là inference mới.

Khảo sát phát hiện minhthao có 1 storage path test fail trên macOS, không âm thầm sửa nhánh nguồn. npm audit advisories được ghi riêng trong backlog, không dùng audit fix --force. Docker và Ubuntu/Actions workflow mới chưa được gọi là pass nếu chưa quan sát run trên đúng push/PR SHA.

## Reviewer cần kiểm tra

- ADR/scope local, field semantics/null/revision/export authority; xem original attribution và các nhánh bài tập được giữ.
- Tái lập README từ clone đúng branch, Product checks đúng head/merge SHA; không dùng check xanh từ nhánh cũ.
- Không có thay đổi inference/domain/dataset/gold/threshold; runtime/models/DB/secrets và output cá nhân không nằm trong diff.
- Chỉ áp protection sau khi Product checks đã xuất hiện. Một reviewer khác trước merge; không auto-merge.
