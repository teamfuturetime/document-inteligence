# Thay đổi

## Post-commit confirmation notifications — 12/11/2026

Issue #10: local logging notification sau transaction confirm, receipt tối thiểu và timeout cooperative. Giữ response/schema/export và transaction chính khi sender lỗi, không gửi lại cho confirmed retries. Cấu hình disabled/log, runbook và tests SQLite/cancellation/restart. Thay đổi local theo [ADR0009](docs/decisions/0009-confirmation-notifications.md), chưa là release hoặc tính năng đã merge; chưa email/webhook/durable outbox.

## Upload ingress 0.2.1 — 12/11/2026

Issue #8: giới hạn tổng thời gian nhận body, số upload đồng thời và Uvicorn connection/task; kiểm Content-Length và byte stream trước persistence. Thêm lỗi receive/admission an toàn, giải phóng slot khi timeout/disconnect/cancel và giữ slot nếu thread lưu vẫn chạy; bảo toàn idempotent retry/queue semantics. Sinh lại OpenAPI/frontend types, bổ sung ASGI tests và probe HTTP loopback đo latency/RSS/tasks. Xem [budget và giới hạn](docs/operations/upload-ingress.md). Đây là thay đổi trên nhánh nhiệm vụ, chưa là release/tag đã xuất bản.

## Product local 0.2.0 — 24/10/2026

Theo yêu cầu mới, mở rộng nhatquang thành workflow local: package pipeline với Tesseract thật, pinned models/provenance, hai schemas; upload/storage/SQLite migrations/worker, immutable predictions, review revisions/conflicts, backend confirm/export; UI source evidence/history/dirty-state; 150 synthetic parents và model evaluator. Giữ fixture riêng và source lineage từ nền Quang/model lock Tùng. Sửa hash fixture theo Git LF bytes, không đổi gold/ảnh. Checks và giới hạn ở báo cáo product; chưa là release/tag/PR được xuất bản trên GitHub.

## Foundation 0.1.0 — 05/10/2026

Khởi tạo FastAPI + React/TypeScript trong repository hiện có; thêm domain models, contracts được sinh và kiểm tra drift, chuẩn hóa/validation, fixture adapters bật rõ, 6 ảnh synthetic và manifest, evaluator field-level cùng tests. Thêm UI đối chiếu chỉ xem, CI local configuration, Dockerfiles/Compose, tài liệu yêu cầu/ADR/dữ liệu/cộng tác/backlog và báo cáo verification. Chưa tích hợp OCR/model, persistence hoặc luồng review/export hoàn chỉnh. Đây là phiên bản nền cục bộ, chưa phải release đã xuất bản trên GitHub.
