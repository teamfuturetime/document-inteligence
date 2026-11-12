# GitHub setup và gói duyệt

Nguồn khảo sát mới: [audit](../repository-audit.md), [snapshot API](../evidence/github-snapshot.json), [inventory](../branch-inventory.md). Đọc được quyền admin; không có thiếu quyền đọc cản trở audit. Main vẫn chỉ README, protection404/rulesets rỗng, 0 Issues; PR #1 mở nhatquang→main và #2 merged autosave→minhthao. Không thay settings trong lượt local này.

## Nội dung đã chuẩn bị để duyệt một lần

[Gói thao tác đầy đủ](../../.github/consolidation/README.md): một nhánh push, một PR hợp nhất vào main, 8 labels, 3 milestones và 9 Issues có body/acceptance/dependencies. [Protection payload](../../.github/consolidation/main-protection.json) không tự áp dụng. Không CODEOWNERS: chưa có người phụ trách đồng ý; .github/CODEOWNERS.example vẫn chỉ template. Không mời/sửa quyền, đổi default branch, bật auto-merge hoặc xóa refs.

## Workflow và required context thực tế

`.github/workflows/ci.yml` tên Product CI, jobs Backend checks / Frontend checks / Evaluation regression / OCR integration / Browser E2E; aggregate `Product checks` luôn chạy sau cả năm. [Required check manifest](../../.github/required-checks.json) là nguồn tên cho local validation và protection payload. Không paths/paths-ignore; PR vào main và consolidation, push main/consolidation, workflow_dispatch. Read-only token, pinned Actions, không pull_request_target hoặc API secret.

Gate có tests chạy **chính script workflow** với success/failure/skipped/cancelled/missing, không báo xanh khi dependency bị skip. Branch protection strict required context chỉ `Product checks`; nó đại diện cả năm jobs. Áp sau khi context được run thực tế; không yêu cầu một check chưa từng xuất hiện hoặc có thể mất vô thời hạn do filter.

GitHub Actions mới/Ubuntu/Docker chưa được chứng minh từ YAML/local macOS. Sau approved push, lưu run URL, head_sha/conclusion/check names; sau apply protection GET xác minh settings. Existing green checks của a03ea30 không thay bằng evidence cho nhánh mới.

## Đường vào main và PR hiện có

PR consolidation→main chứa original nhatquang history; ghi nguồn PR #1 và giữ attribution. Merge commit sau ít nhất1 reviewer để bảo toàn lịch sử, không rebase/squash baseline. Không merge #1 trước chỉ để tạo check cũ rồi bật gate mới chặn PR. Khi consolidation được chấp nhận/merge, đọc lại trạng thái #1; nếu còn mở, chuẩn bị comment delivered/superseded có URL thật rồi chỉ đóng khi được duyệt. #2 là autosave trên nhánh cá nhân, không cần reopen/merge lại, port có issue CONS-04.

Main ổn định → feat/fix/test/docs/chore ngắn → PR/checks/review, xem [CONTRIBUTING](../../CONTRIBUTING.md). Các kế hoạch phân công cá nhân cũ chỉ là lịch sử. Không nhầm việc có quyền admin với việc đã được chủ dự án cho phép ghi.
