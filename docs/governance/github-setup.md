# GitHub setup và gói duyệt

Nguồn khảo sát mới: [audit](../repository-audit.md), [snapshot API](../evidence/github-snapshot.json), [inventory](../branch-inventory.md). Đọc được quyền admin; không có thiếu quyền đọc cản trở audit. Main vẫn chỉ README, protection404/rulesets rỗng, 0 Issues; PR #1 mở nhatquang→main và #2 merged autosave→minhthao. Đây là snapshot trước publish. Sau khi chủ dự án duyệt, [publication record](../github-publication.md) ghi PR#3, backlog và main protection đã được API xác minh.

## Nội dung đã duyệt và triển khai

[Gói thao tác đầy đủ](../../.github/consolidation/README.md): một nhánh push, một PR hợp nhất vào main, 8 labels, 3 milestones và 9 Issues có body/acceptance/dependencies. [Protection payload](../../.github/consolidation/main-protection.json) đã áp sau khi Product checks xuất hiện và đạt; không tự áp lại. Không CODEOWNERS: chưa có người phụ trách đồng ý; .github/CODEOWNERS.example vẫn chỉ template. Không mời/sửa quyền, đổi default branch, bật auto-merge hoặc xóa refs.

## Workflow và required context thực tế

`.github/workflows/ci.yml` tên Product CI, jobs Backend checks / Frontend checks / Evaluation regression / OCR integration / Browser E2E; aggregate `Product checks` luôn chạy sau cả năm. [Required check manifest](../../.github/required-checks.json) là nguồn tên cho local validation và protection payload. Không paths/paths-ignore; PR vào main và consolidation, push main/consolidation, workflow_dispatch. Read-only token, pinned Actions, không pull_request_target hoặc API secret.

Gate có tests chạy **chính script workflow** với success/failure/skipped/cancelled/missing, không báo xanh khi dependency bị skip. Branch protection strict required context chỉ `Product checks`; nó đại diện cả năm jobs. Áp sau khi context được run thực tế; không yêu cầu một check chưa từng xuất hiện hoặc có thể mất vô thời hạn do filter.

GitHub Actions/Ubuntu đã được xác minh ở push/PR runs của d597eb5, xem publication record. Docker vẫn chưa build/run; không suy Docker đạt từ CI. Các run URL/head_sha/check names và GET protection được ghi trong snapshot kết quả; checks xanh của a03ea30 không thay evidence mới.

## Đường vào main và PR hiện có

PR consolidation→main chứa original nhatquang history; ghi nguồn PR #1 và giữ attribution. Merge commit sau ít nhất1 reviewer để bảo toàn lịch sử, không rebase/squash baseline. Không merge #1 trước chỉ để tạo check cũ rồi bật gate mới chặn PR. Khi consolidation được chấp nhận/merge, đọc lại trạng thái #1; nếu còn mở, chuẩn bị comment delivered/superseded có URL thật rồi chỉ đóng khi được duyệt. #2 là autosave trên nhánh cá nhân, không cần reopen/merge lại, port có issue CONS-04.

Main ổn định → feat/fix/test/docs/chore ngắn → PR/checks/review, xem [CONTRIBUTING](../../CONTRIBUTING.md). Các kế hoạch phân công cá nhân cũ chỉ là lịch sử. Không nhầm việc có quyền admin với việc đã được chủ dự án cho phép ghi.
