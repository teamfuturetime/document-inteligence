# Đóng góp vào nền OCR hóa đơn

[README gốc](README.md) là điểm chạy duy nhất. Nền được chọn tại [ADR0008](docs/decisions/0008-primary-invoice-platform.md); phạm vi local một người dùng. Đọc [contracts](contracts/README.md) trước khi đổi API và [inventory](docs/branch-inventory.md) trước khi port.

## GitHub Flow

1. Chọn một issue/task có problem, phạm vi, acceptance, dependencies, dữ liệu synthetic và cách kiểm tra (Definition of Ready).
2. Sau khi nền đã vào main: `git switch main`, `git pull --ff-only origin main`, rồi `git switch -c feat/<task>` (hoặc fix/docs/test/chore). Trong thời gian chờ PR nền, branch từ chore/repository-consolidation và ghi dependency/base rõ trong PR; không coi main cũ là runnable.
3. Hoàn tất từng thay đổi nhỏ có thể kiểm tra, commit Conventional Commits. Agent dùng cùng quy ước, không yêu cầu phát triển trên nhánh cá nhân dài hạn. Trước mỗi commit xem status/diff, stage đường dẫn cụ thể, xem staged diff và `git diff --cached --check`; không include file của người khác/output/runtime/secret.
4. Chạy `python scripts/dev.py check`; thay OCR/workflow còn cần `ocr`/`e2e`, thay dataset/config giữ hashes/version/evidence. Đẩy nhánh hoặc tạo PR chỉ khi được ủy quyền. PR đích main, dùng template, ghi lệnh/kết quả/phần chưa chạy. Không coi test với doubles là OCR/provider thật.
5. `Product checks` phải đạt: Backend checks, Frontend checks, Evaluation regression, OCR integration, Browser E2E. Không path filters có thể làm required check mất ở docs-only PR; không continue-on-error. Remote evidence và settings đã xác minh tại [publication record](docs/github-publication.md); luôn kiểm đúng SHA hiện tại.
6. Ít nhất một reviewer khác duyệt nghiệp vụ, contract/null/revision/evidence và diff. Giải quyết hội thoại, cập nhật nhánh bằng merge từ main nếu cần rồi chạy checks lại. Không tự merge; reviewer/team quyết định. Merge nền bằng merge commit để bảo toàn original commits/authorship; không rewrite lịch sử.

Không amend/rebase/reset/force-push hoặc xóa nhánh khi chưa được yêu cầu. Nhánh cá nhân và submission refs giữ làm tham chiếu; chỉ dọn khi có bằng chứng giá trị được bảo toàn và tác giả đồng ý. Không tự gán CODEOWNERS từ kế hoạch phân công cũ.

## Definition of Done

Hành vi đúng acceptance, kiểm tra phù hợp thực sự pass, hướng dẫn chạy tái lập được, generated contracts/types/examples đồng bộ nếu đổi domain, prediction/review tách biệt, dữ liệu/model/config có version/hashes, không secret/PII/runtime artifacts, diff hiểu được và review hoàn tất trước merge. Không dùng commit count, coverage đơn độc hoặc synthetic score để tuyên bố chất lượng sản phẩm.

Issue/milestone/labels dự kiến ở [approval package](docs/governance/github-setup.md); ID CONS-* là mã local được ánh xạ tới Issues #4–#12 tại publication record. [Backlog foundation cũ](docs/planning/backlog.md) là lịch sử. License/security contact/owner volunteers chưa được xác nhận; không tạo LICENSE hoặc CODEOWNERS giả.
